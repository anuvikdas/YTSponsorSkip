# Experimental local demo — 2026-10-22 (EDT)

Implemented on `codex/transcript-provider`, starting from `d6d0381`. Selected detector remains
**contextual_v1 / Conservative**, version **`contextual-v1-sha256:cfee4293e5f725c8`**. No detector
rules, labels, frozen reports, browser acquisition probe, deployment, or model calls changed.
Experimental skipping is **off by default**, has no video allowlist, and is not a reliability claim.

## Start / verify the backend

From the project root, with the existing ignored `.env` containing `SUPADATA_API_KEY`:

```bash
cd /Users/anuvikdas/Downloads/YTSponsorSkip/YTSponsorSkip
YTSS_DETECTOR_VARIANT=contextual_v1 YTSS_REQUEST_TIMEOUT_SECONDS=30 \
  .venv/bin/uvicorn ytsponsorskip.main:app --app-dir backend/src \
  --host 127.0.0.1 --port 8000
```

At handoff, the updated server is already running: **PID 28629**, **127.0.0.1:8000**. Do not start
a second listener. Only the previously verified project Uvicorn processes were terminated to
restart it; no unrelated process was stopped. If restarting later, identify the listener first
with `lsof -nP -iTCP:8000 -sTCP:LISTEN`, and stop only your project process.

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/demo-status
```

Expect `contextual_v1`, the version above, and **3 remaining native attempts**. Prediction cache
keys include transcript identity/hash, detector version, and sensitivity. The version hashes both
frozen and contextual source code. The extension pins the actual version obtained from the
backend before acquisition; a mismatch is rejected before acquisition and on response validation.
While experimental results are active, read-only version checks run every 10 seconds, with a
5-second timeout. Seeking requires verification fresher than 15 seconds. A failed check clears
intervals and Undo and shows unavailable; reload the video after fixing the backend. These checks
never request a transcript or retry a failed acquisition.

## Chrome setup and one acceptance checklist

1. **Close other YouTube watch tabs first.** Settings are shared across tabs: enabling Supadata
   on several unfamiliar videos can spend several attempts. At `chrome://extensions`, reload
   **YTSponsorSkip**, whose unpacked folder is
   `/Users/anuvikdas/Downloads/YTSponsorSkip/YTSponsorSkip/extension`. Reload the watch page too:
   extension reload alone does not replace an already injected content script.
2. Open the extension's **Settings**. Enable **Enable extension** and **Experimental automatic
   skipping**; select **Saved reviewed-tune transcript**, **Conservative**, and backend
   **http://127.0.0.1:8000**. Keep **Preview detected promotions**, manual fixtures, and browser
   probe **off**. Save. The experimental switch forces Conservative. For preview-only instead,
   check Preview (which unchecks experimental skipping) and Save.
3. **Positive + Undo:** open [Friends at 11:20](https://www.youtube.com/watch?v=I9hJ_Rux9y0&t=680s).
   Popup should say **Experimental auto-skip ON**, **Saved transcripts**, actual contextual
   version, and **11:23–11:55**. Play from before 683 seconds: expect a seek to 715 and an Undo
   notification. Click Undo promptly: expect the actual pre-skip position (not simply 683), no
   immediate skip loop, and unchanged play/pause state. The popup also has an Undo button after
   the six-second notice disappears. Let playback leave the interval, seek to 680, then play:
   it becomes eligible again. Deliberately seeking **into** 683–715 suppresses it instead.
4. **Same-tab negative:** navigate in that tab to
   [C in 100 Seconds](https://www.youtube.com/watch?v=U3aXWizDbQ4).
   Friends predictions/Undo must clear, followed by **No promotions detected by the current
   rules** and zero intervals. Playback must remain normal. This is success with zero predictions,
   not detection unavailable. Disable experimental skipping while a prediction is pending/loaded
   to check that no old skip can occur; re-enable for the next step.
5. **Supadata path:** while still in Saved mode, navigate that same tab to the preselected
   [unfamiliar smoke-test video at 25:57](https://www.youtube.com/watch?v=DxL2HoqLbyA&t=1557s).
   Pause before 1560 seconds if needed. Then select **Supadata native captions** in Settings,
   keep experimental/Conservative on, and Save. This video's transcript is now locally persisted:
   expect **Supadata native captions (local saved reuse)**, **26:00.1–27:12.2**, and no new
   acquisition attempt. Play across 1560.09: expect skip to 1632.18 + working Undo. Do not seek
   directly into the predicted interval to test auto-skip: that intentionally suppresses it.
   For a genuinely new video later, a supported English prerecorded watch URL will acquire on a
   disk/memory miss; there is no hard-coded allowlist. That consumes one of the **three** attempts.
6. Capture the popup's behavior/source/version/intervals/remaining allowance and a short screen
   recording of skip → Undo → normal playback, plus same-tab navigation to C. Check a paused
   arrival (stays paused), deliberate seek into an interval (no skip), and feature-off (no skip).
   An error must show **Detection unavailable**, not zero predictions, and must not stop playback.

In the Supadata test, first playback is never held for acquisition. If the viewer has already
passed a predicted interval when results arrive, there is no rewind. If already inside, only
the remainder is skipped, except when a deliberate user seek into that interval takes priority.
Switch back to Saved or disable experimental skipping before browsing unrelated videos if you
do not intend to spend the remaining allowance.

## Measured software/acquisition evidence (not Chrome acceptance)

| Actual local HTTP request | Outcome | Client / provider / detector latency |
| --- | --- | --- |
| Friends, Saved/Conservative | 200; 683–715 s | 13.410 / 0.926 / 10.230 ms |
| C, Saved/Conservative | 200; zero intervals | 3.998 / 0.472 / 1.941 ms |
| `DxL2HoqLbyA`, Supadata/Conservative | 200; 1560.09–1632.18 s | 1674.079 / 1641.434 / 30.308 ms |

The unfamiliar video was selected **before** inspecting its transcript or predictions, with
no previous request in our ledger: [selection record](../data/experiments/unfamiliar-demo-selection-2026-10-22.json).
It was not replaced with another example. Native acquisition returned HTTP 200, **566 English
cues**, caption type **unknown**, valid finite nonnegative ordered timing, first start **0.060 s**,
last start **1632.180 s**, last cue end **1634.043 s**. Original text, overlaps, and milliseconds
converted to seconds are preserved. The final cue is a closing thank-you, and no pagination/job
response occurred; this is evidence against obvious truncation, not an independently verified
complete transcript or exact speech boundary. Caption manual/generated type remains unknown.

Post-output transcript inspection supports a genuine Brilliant sponsor pitch in the predicted
region, but also suggests a **missed lead-in** beginning near the cue at 1554.72 s (roughly 5.37 s
before the prediction). This is qualitative transcript review, **not a manual full-video accuracy
label**; no false-positive rate or exhaustive miss count can be claimed. No rules were patched
to improve this result. The last thank-you at 1632.18 is outside the predicted range. Watch the
transition yourself before describing its boundaries as correct.

After restarting the backend, the same ID returned `transcript_provider=supadata-native-saved`,
`transcript_disk_cache_hit=true`, with no memory hit and no additional attempt: **25.354 ms** API
work (provider file read **1.306 ms**, detector **23.279 ms**). The next request had transcript and
detection memory cache hits: **0.672 ms** API work. Wrong expected detector version returned
HTTP **503 / PROVIDER_ERROR**, without acquisition. Both reuse checks kept the allowance at 3.
Local raw responses and full smoke results are in ignored `results/`, not committed as bulky data.

### Budget and persistence

Only **one** new acquisition was made this task: `DxL2HoqLbyA`. Supadata's billable-request header
reported **1**; read-only Free-account snapshots changed from **15/100 to 16/100 credits used**.
No purchase, recharge, generated fallback, model call, or paid service was added; incremental
spending was **$0**. The original authorization is five distinct attempts total: prior qf + this
video = **2 used, 3 remain**. Timeouts, failures, interrupted attempts count; failed IDs cannot
be retried by this path. Global ledger moved from 16 to 17 attempts, separately from campaign count.

`PersistentNativeProvider` first reuses saved native files, then atomically reserves a campaign
attempt in `results/trial-budget.sqlite3`, and delegates to the existing native-only provider
with Free-credit preflight, existing global limits, and bounded job polling. No automatic retries
or fallback exist. Both CLI collection and FastAPI share this campaign ledger. Do not delete
the ledger/attempt markers to reset the allowance. Successful normalized transcripts and raw
observations are saved atomically in ignored `results/development-transcripts/`, without keys or
request headers. `TranscriptService` still supplies memory caching, coalescing, concurrency and
timeouts; `DetectionService` still supplies versioned prediction caching. No additional Node or
model dependency was added.

## What is implemented versus verified

- **Implemented:** default-off arbitrary-supported-video experimental path, separate preview,
  visible source/version/behavior/budget, persistent reuse, actual prediction delivery to the
  existing PlaybackController, notices and popup Undo. Validated ordered, finite, nonnegative
  intervals merge first, and only merged spans **strictly >3 s** are eligible. The controller
  checks actual finite video duration and target bounds immediately before seeking; unknown,
  invalid, live, ad-playing, stale, or unsupported state cannot seek.
- **Automated:** **87 backend tests**, **34 extension tests**, lint and diff checks pass. Nine new
  integration tests run the real contextual detector on saved Friends/C transcripts (no labels
  passed to inference), then simulate worker → content → real PlaybackController. They cover
  playing/paused arrivals, late no-rewind, exact Undo/no loop/replay, user seeking, rapid navigation,
  disable/source/mode/version changes, wrong versions, invalid duration/live guard, errors/timeouts,
  late responses after timeout, and preview with no seeks. Unit tests also cover adjacent merging,
  >3-second policy, malformed input, metadata arrival, failed seeks, persistence, redaction and
  atomic limits. Simulated media/Chrome APIs are **not actual Chrome playback**.
- **Actual Chrome this task:** read-only C page inspection established finite duration **144.641 s**
  and a hidden Live badge. This exposed and fixed a guard bug; a regression test now covers it.
  It does **not** verify skipping, Undo, reload, or navigation of updated code.
- **Carried-forward UI evidence:** the user-supplied screenshot observations show Friends 683–715
  and C zero predictions. Record these as **screenshot-supported UI checks**, not uninterrupted
  playback, same-tab navigation, or detector-version evidence. Previous fixture playback checks
  remain **user-reported**, not new automated/Chrome acceptance evidence.
- **Requires manual Chrome acceptance:** checklist above. Browser tooling denied access to the
  extension's non-HTTP settings/reload pages, so the updated code could not be reloaded/configured
  or its detector-driven skip/Undo verified in Chrome. No workaround was used to bypass that block.

## Main functions and tradeoffs

`checkForVideoChange` identifies standard watch IDs and creates a fresh request identity on
navigation/settings changes, clearing old state immediately. `acquirePreview` is shared by preview
and experimental operation, but sends intervals to playback only in the latter. It verifies actual
backend version, response identity, source, English language and Conservative policy. Backend errors
remain unavailable, distinct from a successful empty interval array. Runtime status checks invalidate
obsolete detector results without reacquisition.

`PlaybackController.setIntervals` normalizes/merges and considers late arrival; `evaluatePlayback`
checks current position/duration/eligibility and never seeks backward. `skipInterval` records the
actual pre-skip position. `undoLastSkip` restores it and suppresses that interval. `handleSeeking`
and `handleSeeked` recognize controller-owned targets within 0.35 seconds; other seeks are treated
as viewer intent. Suppression lasts until leaving the interval, allowing replay from before it.
Target-based seek attribution is necessarily heuristic; unusual competing scripts or rapid near-target
seeks still need browser testing. No call to `play()` or `pause()` is made, preserving user playback.

Settings are shared across tabs; caches/coalescing are process-local; the atomic campaign budget and
successful transcript files survive restart. This is intentionally a single-user, local prototype,
not a hardened publicly exposed service. Backend restart/version failure clears experimental results
on the next health check (within ~10 seconds normally); freshness expires at 15 seconds if timers stall.

## Demo explanation and remaining step

Say: **“This is an opt-in experimental detector. The end-to-end flow acquires captions, produces
timestamped predictions, skips them without delaying playback, and supports Undo. It can miss or
misclassify promotions; a miss means normal playback continues, not that a hard-coded timestamp
will be substituted.”** Use Undo for a false positive and show preview when inspecting predictions.

Known contextual development results remain 36.52 incorrect predicted seconds, one of nine negative
videos affected, and 208.96 missed promotional seconds on 22 reviewed **development** videos. Broad
sales-language windows can flag normal reviews; subtle creator pitches and transitions can be missed;
derived cue ends limit boundaries. These unchanged numbers are not independent validation. Previously
held-out examples already used for development are not new tests; the frozen report stays unchanged.

The smallest remaining step is the **manual Chrome skip + Undo + same-tab negative acceptance**
above. No further detector research, acquisition batch, or hosting change is needed for a limited
recruiting demonstration. Broader reliability would require new untouched fully reviewed videos,
more acquisition-session evidence, and acceptable false-skip/boundary metrics after freezing.

Re-run correctness checks without acquisition:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check backend scripts
node --test extension/tests/*.test.js
git diff --check
```

`scripts/demo_smoke.py` records the bounded HTTP experiment and refuses to rerun if its local
output already exists. Inspect that record instead of deleting it to force another acquisition.
