export default {
  async fetch(request, env) {
    console.log("HIT", request.method, new URL(request.url).pathname);
    console.log("host:", request.headers.get("host"));
    console.log("has_x_api_key:", request.headers.has("x-api-key"));
    console.log("x_api_key_prefix:", (request.headers.get("x-api-key") || "").slice(0, 8));

    // --- Auth ---
    const apiKey = request.headers.get("x-api-key");
    if (!apiKey || apiKey !== env.ACTIONS_API_KEY) {
      return json({ error: "unauthorized" }, 401);
    }

    const url = new URL(request.url);

    // --- SnapshotReader: GET /snapshot/{name} ---
    const snapMatch = url.pathname.match(/^\/snapshot\/([a-z0-9_-]+)\/?$/i);
    if (request.method === "GET" && snapMatch) {
      const name = snapMatch[1].toLowerCase();
      console.log("SNAPSHOT_MATCH", name);
      return await handleSnapshotGet(name, env);
    }

    return json({ error: "not_found" }, 404);
  },
};

const SNAPSHOT_FILES = {
  ids_dump: "ids_dump_latest.json",
  base_stats: "base_stats_latest.json",
  inventory: "inventory_latest.json",
  loadout: "loadout_latest.json",
};

async function handleSnapshotGet(name, env) {
  const path = SNAPSHOT_FILES[name];
  if (!path) {
    return json({ error: "invalid_snapshot_name", allowed: Object.keys(SNAPSHOT_FILES) }, 400);
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
      { error: "github_fetch_failed", ref, path, status: out.status, detail: out.detail },
      502,
    );
  }

  return json({
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
  });
}

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
      } catch {}
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

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj, null, 2), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}
