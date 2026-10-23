# Local detector preview checkpoint — 2026-10-20

Opening a standard YouTube watch video with **Preview detected promotions** enabled now requests
the backend's typed detection endpoint. The popup shows intervals or a distinct no-promotions,
unsupported-video, loading, backend-unavailable, or acquisition-error state. It always says
**Preview only — automatic skipping off**. Neither the popup nor preview response feeds the
playback controller or changes `currentTime`. Manual fixtures and the browser caption probe are
mutually exclusive with preview. The saved source is the default preview choice.

## Run locally

From `/Users/anuvikdas/Downloads/YTSponsorSkip/YTSponsorSkip`:

```bash
YTSS_REQUEST_TIMEOUT_SECONDS=30 .venv/bin/uvicorn ytsponsorskip.main:app \
  --app-dir backend/src --host 127.0.0.1 --port 8000
```

The repository-root `.env` remains ignored. Keep `SUPADATA_API_KEY` there only if you explicitly
select Supadata; do not put it in the extension. The ordinary transcript endpoint still defaults
to `youtube-transcript-api`. The detection endpoint requires an explicit `source=saved` or
`source=supadata`; saved mode is local-only and reads only the fixed 14-ID reviewed-tune allowlist.
No saved-to-live fallback exists. Supadata mode is also local-only, uses native captions, a
Free-credit preflight and the existing persistent trial ledger. A live cache miss may consume a
credit even when the detector returns no intervals. Use saved mode for repeatable Chrome checks.

At `chrome://extensions`, enable Developer mode and load/reload the unpacked extension from
`/Users/anuvikdas/Downloads/YTSponsorSkip/YTSponsorSkip/extension`. Open its Settings page and:

1. Check **Preview detected promotions**.
2. Choose **Saved reviewed-tune transcript** and **Conservative**.
3. Ensure manual playback fixtures and the browser acquisition probe are unchecked.
4. Use `http://127.0.0.1:8000` as Backend URL and save.

Chrome demonstration checklist (the positive, negative, unsupported-page and no-skip checks below
were also verified in the user's Chrome during this milestone):

- Open [reviewed positive — ice cream](https://www.youtube.com/watch?v=O7sQBfpQCvU). Playback
  should start normally. Open the extension popup: expect one Conservative saved-source prediction
  around **565–611 s**, a preview-only banner, and no seek when playback enters that interval.
- Navigate within the same tab to [reviewed negative — C in 100 Seconds](https://www.youtube.com/watch?v=U3aXWizDbQ4).
  Open the popup: expect **No promotions detected**; the previous video's interval should be gone.
- Navigate rapidly between those links, or change Conservative to Aggressive while a request is
  loading. The popup should only show the active video/mode. Reopening the popup should not
  trigger another request. Turning preview off should clear its predictions.
- On a non-watch page, expect **Unsupported page or video**. Stop the backend and reload a saved
  video to check **BACKEND_UNREACHABLE**; playback should still run. Restart the backend afterward.

## Request flow and safeguards

`content.js` observes YouTube SPA navigation and settings changes. It creates a new request ID,
clears the old view immediately, and sends one `video-changed` message per video/configuration.
`service-worker.js` cancels the previous fetch, checks the local backend origin and current
settings, then calls `GET /api/v1/detections/{video_id}?mode=...&source=...`. The popup reads
`chrome.storage.session` only; it does not fetch. Both the worker and response validator compare
video/request/mode/source identities before storing predictions. Old writes are serialized and
generation-checked. The content script rejects any playback intervals while preview is active.

FastAPI validates the 11-character video ID, required `X-Request-ID`, mode and source, then uses
the selected `TranscriptService` for bounded concurrency, cache and duplicate-request
coalescing. `DetectionService` hashes exact transcript content/metadata and caches predictions by
**transcript hash + detector source version + mode**. The same unchanged `PromotionDetector` runs
for both sources; no annotation file or manual timestamp enters detection. The response retains
source, timing provenance, detector version, cache/coalescing flags and separate provider,
detection and total latency. An empty `intervals` list with `status=ready` means successful
zero-prediction detection; acquisition or detection errors use the stable unavailable contract.
Heuristic scores are never displayed as probabilities. Intervals of three seconds or less remain
predictions but are marked ineligible for automatic skipping. Detector-driven skipping remains off.

## Measured checks

Saved-input HTTP checks on the actual local server: `O7sQBfpQCvU` returned HTTP 200 with one
prediction; `U3aXWizDbQ4` returned HTTP 200 with zero predictions. Offline mocked Supadata,
malformed data, invalid identity, budget exhaustion, coalescing, cache and stale-navigation cases
are covered by automated tests. These checks did not consume a Supadata acquisition attempt.

The two **and only two** new live Supadata transcript attempts through local FastAPI were:

| Reviewed tune video | HTTP / detector result | Provider latency | Detection latency | Total API latency | Client time |
| --- | --- | ---: | ---: | ---: | ---: |
| `O7sQBfpQCvU` (positive) | 200; one interval 565.36–611.06 s | 1848.99 ms | 15.02 ms | 1864.58 ms | 1.867 s |
| `U3aXWizDbQ4` (negative) | 200; zero intervals | 2087.91 ms | 6.41 ms | 2097.03 ms | 2.111 s |

Repeating the identical positive video/mode/source query returned HTTP 200 with both transcript
and detection cache hits, `provider_latency_ms=null`, 1.84 ms reported API work and 0.008 s
client time. The attempt ledger moved **3/50 → 4/50 → 5/50**, with no change on the repeat and
zero job polls. A read-only authenticated account check afterward showed **Free (100/mo), 4/100
credits used**, up from the previously observed 2/100. That is consistent with two credits for
these two new attempts, but provider billing can reconcile later. No purchase or recharge was
made; cash spend observed for this milestone is $0.

Actual Chrome verification: the existing unpacked extension was reloaded in Chrome, and Settings
visibly showed preview enabled, saved source selected, and both conflicting development switches
off. The positive popup displayed **9:25.0–10:11.0** with the saved-source label and preview-only
banner. Navigation in the same tab to the negative showed **No promotions detected** and no stale
positive interval. Reopening that popup produced no new backend request in the local server log.
Starting the positive video at 9:26 advanced to 9:28 rather than jumping to 10:11. The YouTube
home page displayed **Unsupported page or video**. The first Chrome pass revealed a missing
`defaults.js` include in `popup.html`; it was fixed, the extension reloaded, and these checks
then passed. Rapid navigation while a deliberately delayed request is pending and an actual
backend-down popup were covered by automated checks or remain manual checklist items, not claimed
as observed Chrome behavior. Before opt-in automatic skipping, we still need broader
cross-session/source reliability and a safety decision informed by held-out evaluation after the
detector is frozen. This milestone does **not** run held-out evaluation or enable predicted skips.
