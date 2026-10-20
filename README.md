# YTSponsorSkip

YTSponsorSkip is an experimental Chrome extension for detecting and skipping creator-integrated promotional interruptions in YouTube videos. The current milestone includes transcript acquisition, a detector-independent playback controller, an improved offline deterministic detector, and a disabled development-only browser acquisition probe. Detector predictions are not connected to playback yet.

## Current components

- `backend/`: Python 3.12 FastAPI service with a replaceable `TranscriptProvider`
- `extension/`: unpacked Manifest V3 Chrome extension with packaged settings and acquisition status
- `extension/playback-controller.js`: interval playback, seeking policy, and Undo
- `scripts/run_acquisition_experiment.py`: repeatable local/cloud acquisition measurement
- `scripts/import_validation_workbook.py`: repeatable manual-label normalization and validation
- `scripts/import_manual_transcripts.py`: deterministic DOCX transcript import with source/derived
  timing separated
- `scripts/evaluate_detector.py`: saved-transcript inventory and tune-only detector evaluation
- `scripts/build_error_review.py`: standalone HTML/Markdown error review from saved tune results
- `scripts/compare_detectors.py`: reproducible local rules and recorded-output comparisons (no model calls)
- `tools/transcript-acquisition-node/`: isolated, pinned Node acquisition probes (not backend code)
- `data/acquisition_corpus.csv`: initial acquisition corpus (not a detection evaluation set)
- `data/validation/`: normalized user-supplied manual annotations

The bounded alternative caption acquisition probe is documented in
[Supadata native-caption probe](docs/supadata-probe.md). It uses the project-root ignored `.env`,
free credits, native captions only, and two prespecified videos. Supadata is not yet selected as
the default FastAPI provider; local live preview can select it explicitly, with Free-credit
preflight and a persistent attempt budget.

The opt-in contextual detector development checkpoint is documented in
[the contextual comparison](docs/contextual-development-2026-10-20.md). The frozen rules remain
the default, predictions remain preview-only, and the saved development transcript is Git-ignored.

## Offline detector review

Open [the local review page](data/reviews/tune-2026-10-11/index.html) directly in Chrome; no backend
is needed. It compares both modes on all 14 reviewed tune videos, with timestamped excerpts and
annotation questions. See [findings and reproduction commands](docs/offline-error-review.md) and
the [proposed $0 semantic experiment](docs/next-detection-experiment.md). Detector predictions remain
disconnected from playback; the browser acquisition experiment is unchanged.

## Local backend

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/uvicorn ytsponsorskip.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for FastAPI's generated OpenAPI UI or check:

```bash
curl http://127.0.0.1:8000/health
curl 'http://127.0.0.1:8000/api/v1/transcripts/dQw4w9WgXcQ?languages=en'
```

Run tests:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
node --test extension/tests/*.test.js
```

## Acquisition experiment

Start the API with its default in-memory cache enabled:

```bash
.venv/bin/uvicorn ytsponsorskip.main:app --host 127.0.0.1 --port 8000
```

Then run:

```bash
.venv/bin/python scripts/run_acquisition_experiment.py \
  --environment local \
  --attempts 2 \
  --output results/local.json
```

The first pass measures uncached acquisition. The second pass measures successful cache hits; failures are intentionally not cached. The report separates eligibility, caption type, expected negatives, end-to-end latency, upstream provider latency, cache behavior, snippet timing granularity, overlap count, and normalized failure reasons.

The acquisition corpus records confirmed caption availability at the time it was curated. That denominator is distinct from the negative cases and from the future manually labeled detection set.

## Load the Chrome extension

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Choose **Load unpacked** and select the `extension/` directory.
4. Start the local backend and open a standard YouTube watch page.
5. Open **Settings**, leave the backend URL as `http://127.0.0.1:8000`, and save.
6. For playback testing, expand **Development**, enable **Use manual playback fixtures**, and save.
7. Follow `docs/chrome-test-checklist.md`.

The development fixtures are user-supplied `tune` labels, disabled by default, and visibly identified as manual fixtures. They exercise skipping and Undo without claiming detector output. If acquisition fails, YouTube playback continues; fixture playback remains independently testable.

## Configuration

Backend settings use the `YTSS_` prefix:

| Variable | Default | Purpose |
| --- | --- | --- |
| `YTSS_ENVIRONMENT` | `local` | Environment label in health output |
| `YTSS_ALLOWED_ORIGINS_CSV` | `http://localhost` | Comma-separated CORS allowlist |
| `YTSS_REQUEST_TIMEOUT_SECONDS` | `10` | Upstream connect/read timeout |
| `YTSS_MAX_CONCURRENT_ACQUISITIONS` | `4` | Maximum simultaneous provider calls |
| `YTSS_CACHE_TTL_SECONDS` | `900` | In-memory successful-result TTL; `0` disables |
| `YTSS_CACHE_MAX_ENTRIES` | `128` | In-memory LRU capacity |
| `YTSS_REQUEST_LIMIT_PER_MINUTE` | `60` | Single-process API limit |
| `YTSS_API_TOKEN` | unset | Optional bearer token for experiments |
| `YTSS_DETECTOR_VARIANT` | `frozen_rules` | `contextual_v1` opt-in preview comparison |

The cache, rate limiter, and in-flight request registry are intentionally process-local. This is sufficient for one free Render instance; scaling to multiple processes would require a shared design or acceptance of per-process limits.

## Render experiment

`render.yaml` and `Dockerfile` define a single free web service. Connect the repository in Render, select the blueprint, and verify that the service remains on the **Free** plan before creating it. No database, custom domain, or proxy is required.

Run the same corpus against the assigned `onrender.com` URL:

```bash
.venv/bin/python scripts/run_acquisition_experiment.py \
  --base-url https://YOUR-SERVICE.onrender.com \
  --environment render-free \
  --attempts 2 \
  --output results/render-free.json
```

Do not warm the service before the first attempt if measuring cold-start latency. Compare `end_to_end_latency_ms` with `provider_latency_ms`: a large first-request difference indicates cold start, while `IP_BLOCKED` or `REQUEST_BLOCKED` indicates transcript acquisition failure.

## Detection labeling template

`data/labeling_template.xlsx` contains CSV-compatible **Videos** and **Segments** sheets. See `docs/labeling-format.md` before labeling or importing data. Acquisition outcomes are evidence about caption retrieval, not promotion labels.

The imported validation set is documented in `docs/validation-import-report.md`. Held-out and partial-review rows are excluded from development playback fixtures and must remain outside detector tuning.

The rules baseline is documented in `docs/detector-baseline.md`. The 14-video manual transcript
import is documented in `docs/manual-transcript-import-report.md`; the preserved unchanged-detector
tune result is in `docs/detector-tune-report.md`. Render's bounded follow-up is in
`docs/render-small-experiment.md`.

The bounded alternative-library investigation is in `docs/node-acquisition-experiment.md`. Neither
Node package passed the two-video gate, so neither was added to deployment. The exact 14-video
manual collection checklist and normalized JSON contract are in
`docs/tune-transcript-collection.md`.

The automatic-acquisition evidence, current vendor costs, and weighted decision framework are in
`docs/acquisition-options-decision.md`. The $0 browser-context probe is now implemented behind an
off-by-default development flag; its architecture and still-unrun Chrome protocol are in
`docs/browser-acquisition-probe.md`. No managed account or paid service was added.

The tune-only detector iteration and before/after metrics are in
`docs/detector-tune-iteration.md`. The strategy comparison and current official model/API facts are
in `docs/detection-strategy-decision.md`. A provider-neutral, disabled model-assisted contract,
cost model, and failure policy are in `docs/model-assisted-detector-design.md`; no model provider
SDK or inference path is installed.

## Reproduce the manual tune baseline

```bash
.venv/bin/python scripts/import_manual_transcripts.py \
  "/Users/anuvikdas/Downloads/SponsorSkip Manual 14 Transcript Collection.docx"

.venv/bin/python scripts/evaluate_detector.py \
  --source-dir data/transcripts/tune \
  --detector-commit 0d065eccc10952ac3f1c2a416a0b7e4929e39026 \
  --output data/evaluation/tune-baseline-0d065ec.json
```

The imported files preserve source starts and mark all constructed durations as derived analysis
spans. They must not be interpreted as source-supplied caption or promotion boundaries.

## Reproduce the improved tune-only detector result

```bash
.venv/bin/python scripts/evaluate_detector.py \
  --source-dir data/transcripts/tune \
  --detector-commit 3c35ceb02c84d1facd025ec8d012e09d592a6e00 \
  --output data/evaluation/tune-rules-3c35ceb.json
```

This remains tune-set development evidence. `held_out` labels have not been evaluated and the
result is not connected to playback.

## API behavior

The local preview milestone is documented in [docs/local-preview-milestone.md](docs/local-preview-milestone.md).
The extension's disabled-by-default **Preview detected promotions** setting calls
`GET /api/v1/detections/{video_id}?mode=conservative|aggressive&source=saved|supadata` with a
validated `X-Request-ID`. Saved mode is the development default and does not acquire captions;
Supadata is explicit and budgeted. Both use the same unchanged detector. Predictions are shown
in the popup only and cannot trigger playback skips.

`GET /api/v1/transcripts/{video_id}?languages=en` returns a typed transcript document. Stable error responses distinguish unavailable captions, invalid input, upstream changes, timeouts, and IP/request blocking. Original snippet `text`, `start_seconds`, and `duration_seconds` are preserved; caption duration is display timing, not a detected promotional boundary.
