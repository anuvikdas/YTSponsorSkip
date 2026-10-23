# Render Free deployment checklist

The repository is ready for one Docker-based Render Free web service. No database, cache service, custom domain, secret, or paid plan is required.

## Deploy through the dashboard

1. Sign in at <https://dashboard.render.com/> with the GitHub account that can access `anuvikdas/YTSponsorSkip`.
2. Choose **New +** and **Blueprint**.
3. Connect GitHub if prompted, then select `anuvikdas/YTSponsorSkip`.
4. Select branch `codex/transcript-provider`. Do not select or merge into `main`.
5. Confirm Render detects the root `render.yaml` and proposes exactly one service named `ytsponsorskip-api`.
6. Confirm **Instance Type: Free** and that the estimated recurring charge is **$0**. Do not add a database, disk, custom domain, proxy, or paid instance.
7. Apply the blueprint and wait for the deploy log to show that Uvicorn is listening.
8. Copy the assigned `https://...onrender.com` URL.

If Render cannot see the repository, open the GitHub installation settings offered by Render and grant access to this repository only (or to the minimum repository set you prefer), then return to step 2.

## Verify without spoiling the cold-start measurement

The deploy health check can warm the initial instance. After deployment is healthy, leave the service untouched for at least 16 minutes so Render can spin it down. Do not open `/health` immediately before the corpus run.

Then run:

```bash
.venv/bin/python scripts/run_acquisition_experiment.py \
  --base-url https://YOUR-SERVICE.onrender.com \
  --environment render-free \
  --attempts 2 \
  --delay-seconds 1.1 \
  --output results/render-free.json
```

The first-request end-to-end latency is the cold-start observation. Provider latency is populated only for successful uncached acquisitions. Warm uncached end-to-end latency excludes request 1. Cache-hit latency is reported separately on the second pass. `IP_BLOCKED` and `REQUEST_BLOCKED` are acquisition failures, while `ENDPOINT_UNREACHABLE` and `ENDPOINT_INVALID_RESPONSE` indicate hosting/startup or routing problems.

Send the assigned Render URL back to continue the comparison if browser control is not connected.
