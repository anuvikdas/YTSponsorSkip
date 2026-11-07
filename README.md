# YTSponsorSkip

YTSponsorSkip is an experimental Chrome extension that uses YouTube captions to find sponsor reads and creator-owned promotions. It can preview timestamped predictions or, with experimental auto-skip enabled, skip the predicted interval and offer Undo. Playback starts immediately while detection runs. If captions or predictions are unavailable, playback continues normally.

**Status:** Local Manifest V3 prototype. The saved-transcript demo needs no API key or hosted backend. Detector-driven skipping is off by default. Automated tests cover the playback flow, and the manual Chrome acceptance checklist is still pending.

## Try the saved-transcript demo

From the repository root, with **Python 3.12** and desktop Chrome:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
YTSS_DETECTOR_VARIANT=contextual_v1 \
  .venv/bin/python -m uvicorn ytsponsorskip.main:app --host 127.0.0.1 --port 8000
```

1. At `chrome://extensions`, enable **Developer mode**, select **Load unpacked**, and choose `extension/`.
2. In the extension settings, enable **Enable extension** and **Experimental automatic skipping**. Select **Saved reviewed-tune transcript** and keep the backend URL at `http://127.0.0.1:8000`. Leave manual fixtures and the browser caption probe off. Save.
3. Open [How To Make Friends at 11:20](https://www.youtube.com/watch?v=I9hJ_Rux9y0&t=680s). The backend predicts **11:23–11:55**. Play into the interval from before 11:23 to exercise the skip, then click **Undo** to return to the pre-skip position.
4. In the same tab, navigate to [C in 100 Seconds](https://www.youtube.com/watch?v=U3aXWizDbQ4). The previous interval and Undo state should clear, and the popup should report zero detections.

To inspect predictions during normal playback, enable **Preview detected promotions** in place of experimental skipping. To check the API independently of Chrome:

```bash
curl 'http://127.0.0.1:8000/api/v1/detections/I9hJ_Rux9y0?mode=conservative&source=saved'
```

See the [demo handoff](docs/experimental-demo-handoff-2026-10-22.md) for the full acceptance checklist and optional native-caption setup.

## How it works

1. **Acquire captions.** The extension service worker calls a typed FastAPI endpoint. A replaceable transcript provider reads checked-in cues or, in the optional local Supadata experiment, retrieves native English captions. The transcript service coalesces duplicate in-flight requests and bounds concurrency. Successful results go into a process-local TTL/LRU cache. The optional provider also reuses successful acquisitions from disk and tracks its trial budget in SQLite.
2. **Detect intervals.** The contextual rules look for a commercial relationship and pitch evidence across neighboring cues, then map predictions back to source timestamps. The prediction cache keys results by transcript identity, detector version, and sensitivity. The backend defaults to frozen rules unless the contextual variant is selected explicitly.
3. **Protect playback.** The extension checks video, request, and detector identities before using a result. The playback controller validates seek targets and skips only eligible merged intervals longer than three seconds. It respects deliberate user seeks, avoids rewinding when a late result has already passed, and prevents an immediate re-skip after Undo.

Start with the [transcript service](backend/src/ytsponsorskip/service.py), [contextual detector](backend/src/ytsponsorskip/contextual_detector.py), or [playback controller](extension/playback-controller.js).

## What the evaluation showed

The Conservative policy prioritizes avoiding incorrect skips. On **22 reviewed development videos**, contextual rules reduced missed promotional time by **32 seconds** compared with frozen rules, with the same **36.52 seconds** of incorrect predictions.

| Conservative detector | Incorrect predicted time | Missed promotional time | Negative videos with a prediction | Matched intervals |
| --- | ---: | ---: | ---: | ---: |
| Frozen rules | 36.52 s | 240.96 s | 1/9 | 11/14 |
| Contextual rules | 36.52 s | 208.96 s | 1/9 | 12/14 |

These are development results. Eight of those videos were originally held out, then inspected during development. On the [original frozen held-out run](docs/heldout-evaluation-2026-10-20.md), the frozen detector missed **128.96 of 176** annotated promotional seconds and flagged **one of six** negative videos. In the later development comparison, the MiniLM prototype produced zero eligible intervals and failed its recall gates, so the demo uses contextual rules. See the [comparison and error cases](docs/recruiting-demo-checkpoint-2026-10-22.md).

Caption acquisition can dominate response time. In one [local native-caption smoke test](docs/experimental-demo-handoff-2026-10-22.md#measured-softwareacquisition-evidence-not-chrome-acceptance), the client measured **1.67 s** for the request, of which **1.64 s** was provider time and **30.31 ms** was detector time. This was a single request. Broad acquisition reliability and the current detector’s accuracy on a fresh test set remain open.

## Verify and explore

With the Python environment above and Node.js installed, run from the repository root:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check backend scripts
node --test extension/tests/*.test.js
```

- [Playback flow tests](extension/tests/experimental-flow.test.js) cover late responses, navigation, user seeks, Undo, and failure handling.
- [Offline error review](docs/offline-error-review.md) explains the labeling, timing metrics, and commands for reproducing the historical tune comparison.
- [Acquisition study](docs/acquisition-study.md) and [Render experiment](docs/render-small-experiment.md) document provider and deployment tradeoffs separately from detector accuracy.
- [OpenAPI UI](http://127.0.0.1:8000/docs) is available while the local server is running. See [backend settings](backend/src/ytsponsorskip/config.py) for defaults and [`.env.example`](.env.example) for optional native-provider setup.
