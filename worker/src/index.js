export default {
  async fetch(request, env) {
    // Simple API key auth (you set ACTIONS_API_KEY as a secret)
    const apiKey = request.headers.get("x-api-key");
    if (!apiKey || apiKey !== env.ACTIONS_API_KEY) {
      return json({ error: "unauthorized" }, 401);
    }

    const url = new URL(request.url);

    if (request.method === "POST" && url.pathname === "/run/ehp") {
      const body = await safeJson(request);
      const ref = body?.ref ?? "main";
      const allow_out_of_scope = String(body?.allow_out_of_scope ?? true);

      await gh(env, "POST",
        `/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${env.WORKFLOW_FILE}/dispatches`,
        { ref, inputs: { ref, allow_out_of_scope } }
      );

      // After dispatch, discover the run_id by looking for the newest queued/in_progress run on that workflow+branch.
      const run = await findNewestRun(env, ref);
      if (!run) return json({ error: "could_not_find_run" }, 502);

      return json({
        run_id: String(run.id),
        status: run.status,
        html_url: run.html_url
      }, 200);
    }

    // GET /run/ehp/{run_id}
    const m = url.pathname.match(/^\/run\/ehp\/(\d+)$/);
    if (request.method === "GET" && m) {
      const runId = m[1];

      const run = await gh(env, "GET",
        `/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/runs/${runId}`,
        null
      );

      // If not finished, return status
      if (run.status !== "completed") {
        return json({ run_id: runId, status: run.status, conclusion: run.conclusion ?? null }, 200);
      }

      if (run.conclusion !== "success") {
        return json({
          run_id: runId,
          status: run.status,
          conclusion: run.conclusion,
          html_url: run.html_url
        }, 200);
      }

      // Fetch latest.json from bot-outputs. If repo is public, raw.githubusercontent.com works without auth.
      const rawUrl =
        `https://raw.githubusercontent.com/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/${env.OUTPUT_BRANCH}/${env.OUTPUT_PATH}`;

      const outResp = await fetch(rawUrl, { headers: { "accept": "application/json" } });
      if (!outResp.ok) {
        return json({ error: "output_fetch_failed", status: outResp.status, raw_url: rawUrl }, 502);
      }
      const outJson = await outResp.json();

      return json({
        run_id: runId,
        status: run.status,
        conclusion: run.conclusion,
        html_url: run.html_url,
        result: outJson
      }, 200);
    }

    return json({ error: "not_found" }, 404);
  }
};

async function gh(env, method, path, body) {
  const resp = await fetch(`https://api.github.com${path}`, {
    method,
    headers: {
      "authorization": `Bearer ${env.GITHUB_TOKEN}`,
      "accept": "application/vnd.github+json",
      "content-type": "application/json",
      "user-agent": "tower-runner-worker"
    },
    body: body ? JSON.stringify(body) : undefined
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
    const runs = await gh(env, "GET",
      `/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${env.WORKFLOW_FILE}/runs?per_page=10&branch=${encodeURIComponent(ref)}`,
      null
    );

    const items = runs?.workflow_runs ?? [];
    // choose newest run that is queued or in_progress or completed very recently
    const candidate = items.find(r => ["queued", "in_progress"].includes(r.status)) ?? items[0];
    if (candidate) return candidate;

    await sleep(750);
  }
  return null;
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function safeJson(request) {
  try { return await request.json(); }
  catch { return null; }
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj, null, 2), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" }
  });
}
