# ADK + GitLab MCP — WSL Deploy & Live-Verify Runbook

**Branch:** `feat/adk-gitlab-mcp` · **Plan:** `docs/superpowers/plans/2026-06-08-adk-gitlab-mcp.md`

**Why this is Steve-run:** the deploy needs `gcloud` + Docker, which Norton blocks on Git Bash — run everything below from **WSL**. The Python code + 63 unit tests are already green; what remains is live validation that the real agent invokes Gemini + the GitLab MCP server at runtime, and that the hero demo is unbroken.

**What changed (so you know what to watch):** the webhook's MR *evaluation* now runs through a Google ADK agent (`LlmAgent`, Gemini 2.5 Flash) that calls a **community GitLab MCP server** (`@zereight/mcp-gitlab`, stdio) for its read tools (`get_merge_request`, `get_merge_request_diffs`, `list_merge_request_pipelines`). Write-backs (comment/labels/issue) still go over REST — unchanged. The image now installs Node + the MCP server.

> ⚠️ This is the FIRST deploy where the evaluation path is model-driven (non-deterministic) instead of a single structured Gemini call. The hero MR `!10` verdict could drift. **Do the hero-MR regression check (§6) BEFORE re-recording anything.**

---

## 0. Pre-flight (WSL)

```bash
cd ~/CascadeProjects/mr-sentinel          # or wherever your WSL checkout lives
git fetch && git checkout feat/adk-gitlab-mcp && git pull
gcloud auth list                          # expect active: sgharlow@gmail.com
gcloud config get-value project           # expect: aicin-477004
```

If your WSL checkout doesn't have this branch yet, pull it from GitHub after it's pushed (it is currently local-only on the Windows checkout — push it first, or copy it over).

## 1. Confirm the PAT is available to the MCP server

The MCP server reuses the SAME GitLab PAT the REST client already uses. The Cloud Run service already mounts `GITLAB_TOKEN` from Secret Manager (`mr-sentinel-gitlab-token`). `build_gitlab_mcp_toolset()` translates it to `GITLAB_PERSONAL_ACCESS_TOKEN` for the stdio child. **No new secret is needed.** Just confirm it's still bound:

```bash
gcloud run services describe mr-sentinel-webhook --region us-central1 \
  --format='value(spec.template.spec.containers[0].env)' | tr ',' '\n' | grep -i gitlab
```

## 2. Build + deploy

```bash
bash scripts/cloud-run-deploy.sh
```

**Watch the Cloud Build log for the Node/MCP install step** (`npm install -g @zereight/mcp-gitlab`). The Dockerfile uses `RUN set -eux` so a failed npm install will FAIL the build (good — no silently-broken image). If the build fails on npm, check network/registry access in Cloud Build.

After deploy, find the new revision + confirm the MCP binary resolved in the image:

```bash
gcloud run services describe mr-sentinel-webhook --region us-central1 --format='value(status.latestReadyRevisionName)'
# Optional: shell the image locally to confirm the bin name:
#   docker build -t mrs-check . && docker run --rm --entrypoint sh mrs-check -c 'which mcp-gitlab && mcp-gitlab --version || echo NO-BIN'
```

If the binary is NOT named `mcp-gitlab`, redeploy adding the override:

```bash
gcloud run services update mr-sentinel-webhook --region us-central1 \
  --set-env-vars GITLAB_MCP_COMMAND=<actual-bin-name>
```

## 3. Health check

```bash
SERVICE=$(gcloud run services describe mr-sentinel-webhook --region us-central1 --format='value(status.url)')
curl -s "$SERVICE/health"     # expect {"status":"ok"}
```

## 4. ⭐ MCP tool-trace proof (closes the eligibility question)

This is the evidence that all three required technologies run at runtime. Trigger a NON-hero MR evaluation (protects hero `!10`):

```bash
bash scripts/verify-tool-logging.sh        # or: bash scripts/demo-capture.sh fire 9
```

Then read the logs for the new evaluation and confirm you see BOTH the GitLab **MCP** read-tool calls AND the Gemini evaluation:

```bash
gcloud logging read \
  'resource.type=cloud_run_revision AND resource.labels.service_name=mr-sentinel-webhook' \
  --limit 100 --freshness=10m --format='value(textPayload)' \
  | grep -Ei 'get_merge_request|get_merge_request_diffs|list_merge_request_pipelines|evaluation: score|record_verdict|mcp'
```

**PASS criteria:** you see the agent invoking the 3 GitLab MCP read tools, then an `evaluation: score=... verdict=... mr_iid=...` line. If you see the eval line but NOT the MCP read-tool calls, the model skipped the tools — see §4a.

### 4a. If the MCP reads don't appear
The agent is *instructed* to call the MCP reads (`EVAL_USER_PROMPT`) but not hard-gated. If a run skips them:
- Re-run once (non-determinism); usually they fire.
- Check the stdio child actually launched: `grep -i 'mcp-gitlab\|stdio\|MCPToolset\|error closing ADK runner' ` in the same log window.
- If the child failed to start (PATH / bin name), fix per §2.
- If you want a hard guarantee for the judges, capture a clean run's log where all 3 appear and save it as evidence (e.g. `docs/closeout-2026-06-XX/mcp-tool-trace.txt`).

## 5. Confirm no contradictory-prompt failure
If evaluations raise `did not record a verdict` in the logs, the model returned prose instead of calling `record_verdict`. The system prompt was fixed for this (`build_system_prompt(..., for_tool_use=True)`), so it should not happen — but if it does, grep the agent's raw output and tighten `EVAL_USER_PROMPT` / the tool-use hint.

## 6. ⭐ Hero MR `!10` regression check (DO BEFORE RE-RECORDING)

The demo is pinned to hero `!10` = verdict **block**, score **0.0/10**, sha8 `1fb25ad2`, failing rule `no-secrets-in-diff` mapped to SOC2-CC6.1 / ISO-27001-A.9.4.3 / OWASP-ASVS-V2.

```bash
curl -s "$SERVICE/audit/sgharlow/governance-demo-app/10" | grep -Eo 'block|0\.0|no-secrets-in-diff|SOC 2|ISO 27001|OWASP'
```

- **If unchanged:** demo storyboard + screenshots + video still valid. 
- **If the verdict/score/citations DRIFTED:** the model-driven path scored differently. STOP. Decide: (a) re-tune the rubric/prompt to restore the demoed output, or (b) re-record the demo against the new output. Do NOT publish a video that contradicts the live audit page.

## 7. Subprocess hygiene sanity (optional)
The runner is now closed after each eval (`runner.close()` → terminates the `mcp-gitlab` child). After firing several evals, confirm no runaway Node processes accumulate (Cloud Run will recycle instances, but good to spot-check if you exec in):
```bash
# inside an instance, if you can exec: ps aux | grep -c '[m]cp-gitlab'  -> should stay low
```

## 8. Latency re-capture (expect higher than REST)
The agentic multi-turn loop is slower than the old single-call path. Re-capture per `docs/latency-capture.md` and update README "Status" if p50/p95 changed materially. Note the new numbers will be higher — that's expected and worth a one-line note in the Devpost writeup ("agentic tool-calling loop").

## 9. Re-seed + re-record (only if needed)
If §6 drifted or the dashboard needs fattening:
```bash
SEED=1 bash scripts/closeout-all.sh
# then re-record per docs/recording-teleprompter.md
```

## 10. Merge decision
Only after §4 (MCP trace PASS) + §6 (hero-MR PASS):
```bash
git push -u origin feat/adk-gitlab-mcp
# open a PR feat/adk-gitlab-mcp -> main, or fast-forward merge once satisfied
```
Note `main`'s current HEAD as the rollback point before merging.

## 11. Rollback (if anything goes wrong)
- **Code:** `git checkout main` restores the REST-only evaluation loop (the legacy `AgentRunner` was kept intact).
- **Deployed service:** redeploy the prior image, or `gcloud run services update-traffic mr-sentinel-webhook --region us-central1 --to-revisions <PRIOR_REVISION>=100`.
- Rollback is <10 min either way.

---

## Devpost submission updates (after a green deploy)
- Update the "tech used" / writeup to state all three: **Gemini 2.5 Flash** (model), **Google ADK / Agent Builder** (LlmAgent + Runner), **GitLab MCP server** (`@zereight/mcp-gitlab` via ADK MCPToolset, used at runtime for evaluation reads). Be honest about the hybrid (MCP reads + REST write-backs) and why (official Duo MCP server is Premium/Ultimate-only, OAuth-only, lacks MR-note/label tools — `docs/mcp-endpoint-audit.md` addendum).
- Attach/keep the §4 MCP tool-trace log as evidence the partner MCP server runs at runtime.
- Deadline: **June 11, 2:00 PM PT.** Edits stay open until then.
