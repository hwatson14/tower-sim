export default {
  async fetch(request, env) {
    console.log("host:", request.headers.get("host"));
    console.log("has_x_api_key:", request.headers.has("x-api-key"));
    console.log("x_api_key_prefix:", (request.headers.get("x-api-key") || "").slice(0, 8));

    // Simple API key auth (you set ACTIONS_API_KEY as a secret)
    const apiKey = request.headers.get("x-api-key");
    if (!apiKey || apiKey !== env.ACTIONS_API_KEY) {
      return json({ error: "unauthorized" }, 401);
    }

    const url = new URL(request.url);

    // -----------------------------
    // SnapshotReader: GET /snapshot/{name}
    // -----------------------------
    // Supported:
    //  - ids_dump
    //  - base_stats
    //  - inventory
    //  - loadout
    const snapMatch = url.pathname.match(/^\/snapshot\/([a-z_]+)$/);
    if (request.method === "GET" && snapMatch) {
      const name = snapMatch[1];
      return await handleSnapshotGet(name, env);
    }

    // -----------------------------
    // Legacy runner: POST /run/ehp (kept for now)
    // -----------------------------
    if (request.method === "POST" && url.pathname === "/run/ehp") {
      const body = await safeJson(request);
      const ref = body?.ref ?? "main";
      const allow_out_of_scope = String(body?.allow_out_of_scope ?? true);

      await gh(
        env,
        "POST",
        `/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${env.WORKFLOW_FILE}/dispatches`,
        { ref, inputs: { ref, allow_out_of_scope } },
      );

      // After dispatch, discover the run_id by looking for the newest queued/in_progress run on that workflow+branch.
      const run = await findNewestRun(env, ref);
      if (!run) return json({ error: "could_not_find_run" }, 502);

      return json(
        {
          run_id: String(run.id),
          status: run.status,
          html_url: run.html_url,
        },
        200,
      );
    }

    // Legacy: GET /run/ehp/{run_id}
    const m = url.pathname.match(/^\/run\/ehp\/(\d+)$/);
    if (request.method === "GET" && m) {
      const runId = m[1];

      const run = await gh(env, "GET", `/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/runs/${runId}`, null);

      // If not finished, return status
      if (run.status !== "completed") {
        return json({ run_id: runId, status: run.status, conclusion: run.conclusion ?? null }, 200);
      }

      if (run.conclusion !== "success") {
        return json(
          {
            run_id: runId,
            status: run.status,
            conclusion: run.conclusion,
            html_url: run.html_url,
          },
          200,
        );
      }

      // Fetch latest.json from OUTPUT_BRANCH/OUTPUT_PATH using GitHub Contents API (auth-safe; works for private repos).
      const out = await fetchGithubContentsJson({
        owner: env.GITHUB_OWNER,
        repo: env.GITHUB_REPO,
        ref: env.OUTPUT_BRANCH,
        path: env.OUTPUT_PATH,
        token: env.GITHUB_TOKEN,
      });

      if (!out.ok) {
        return json(
          {
            error: "output_fetch_failed",
            status: out.status,
            detail: out.detail,
            ref: env.OUTPUT_BRANCH,
            path: env.OUTPUT_PATH,
          },
          502,
        );
      }

      return json(
        {
          run_id: runId,
          status: run.status,
          conclusion: run.conclusion,
          html_url: run.html_url,
          result: out.data,
          meta: {
            source: "github_contents_api",
            ref: env.OUTPUT_BRANCH,
            path: env.OUTPUT_PATH,
            content_sha: out.contentSha,
            fetched_at_utc: new Date().toISOString(),
          },
        },
        200,
      );
    }

    return json({ error: "not_found" }, 404);
  },
};

// -----------------------------
// Snapshot routing
// -----------------------------

const SNAPSHOT_FILES = {
  ids_dump: "audit/ids_dump_latest.json",
  base_stats: "audit/base_stats_latest.json",
  inventory: "audit/inventory_latest.json",
  loadout: "audit/loadout_latest.json",
};

async function handleSnapshotGet(name, env) {
  const path = SNAPSHOT_FILES[name];
  if (!path) {
    return json(
      {
        error: "invalid_snapshot_name",
        allowed: Object.keys(SNAPSHOT_FILES),
      },
      400,
    );
  }

  const owner = env.GITHUB_OWNER;
  const repo = env.GITHUB_REPO;
  const ref = env.SNAPSHOT_REF || "ids-dump-latest";

  const out = await fetchGithubContentsJson({
    owner,
    repo,
    ref,
    path,
    token: env.GITHUB_TOKEN,
  });

  if (!out.ok) {
    return json(
      {
        error: "github_fetch_failed",
        name,
        ref,
        path,
        status: out.status,
        detail: out.detail,
      },
      502,
    );
  }

  return json(
    {
      meta: {
        source: "github_contents_api",
        owner,
        repo,
        ref,
        path,
        content_sha: out.contentSha,
        fetched_at_utc: new Date().toISOString(),
      },
      data: out.data,
    },
    200,
  );
}

// -----------------------------
// GitHub helpers
// -----------------------------

async function gh(env, method, path, body) {
  const resp = await fetch(`https://api.github.com${path}`, {
    method,
    headers: {
      authorization: `Bearer ${env.GITHUB_TOKEN}`,
      accept: "application/vnd.github+json",
      "content-type": "application/json",
      "user-agent": "tower-runner-worker",
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`GitHub API ${method} ${path} failed: ${resp.status} ${text}`);
  }

  // dispatch returns 204 No Content
  if (resp.status === 204) return null;
  return await resp.json();
}

async function findNewestRun(env, ref) {
  // Poll a few times because dispatch is async and the run may not appear immediately.
  for (let i = 0; i < 8; i++) {
    const runs = await gh(
      env,
      "GET",
      `/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${env.WORKFLOW_FILE}/runs?per_page=10&branch=${encodeURIComponent(ref)}`,
      null,
    );

    const items = runs?.workflow_runs ?? [];
    // choose newest run that is queued or in_progress; otherwise fall back to newest item
    const candidate = items.find((r) => ["queued", "in_progress"].includes(r.status)) ?? items[0];
    if (candidate) return candidate;

    await sleep(750);
  }
  return null;
}

// Fetch + decode JSON via GitHub Contents API (works for public/private; avoids raw endpoint issues)
async function fetchGithubContentsJson({ owner, repo, path, ref, token }) {
  const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(path)}?ref=${encodeURIComponent(ref)}`;

  const headers = {
    accept: "application/vnd.github+json",
    "user-agent": "tower-runner-worker",
  };
  if (token) headers.authorization = `Bearer ${token}`;

  let resp;
  try {
    resp = await fetch(apiUrl, { headers });
  } catch (e) {
    return { ok: false, status: 502, detail: `fetch_failed: ${String(e)}` };
  }

  if (!resp.ok) {
    let detail = "";
    try {
      const j = await resp.json();
      detail = j?.message || JSON.stringify(j);
    } catch {
      try {
        detail = await resp.text();
      } catch {
        detail = "";
      }
    }
    return { ok: false, status: resp.status, detail };
  }

  let j;
  try {
    j = await resp.json();
  } catch (e) {
    return { ok: false, status: 502, detail: `contents_json_parse_failed: ${String(e)}` };
  }

  if (!j || j.type !== "file" || typeof j.content !== "string") {
    return { ok: false, status: 502, detail: "unexpected_contents_api_shape" };
  }

  const contentSha = j.sha || null;
  const b64 = j.content.replace(/\n/g, "");

  let text;
  try {
    text = atob(b64);
  } catch (e) {
    return { ok: false, status: 502, detail: `base64_decode_failed: ${String(e)}` };
  }

  let data;
  try {
    data = JSON.parse(text);
  } catch (e) {
    return { ok: false, status: 502, detail: `json_parse_failed: ${String(e)}` };
  }

  return { ok: true, status: 200, data, contentSha };
}

// -----------------------------
// Small utilities
// -----------------------------

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function safeJson(request) {
  try {
    return await request.json();
  } catch {
    return null;
  }
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj, null, 2), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}
