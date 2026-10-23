# Recruiting preview checkpoint — 2026-10-22

Selected: **contextual_v1 / Conservative** for a clearly limited, saved-transcript recruiting
demonstration. The local semantic experiment failed its declared recall and boundary criteria.
The extension still previews predictions without seeking. The default backend detector remains
the frozen rules unless the contextual variant is explicitly selected at startup.

## Backend ready for Chrome acceptance

No listener on port 8000 was found before startup. A new contextual Uvicorn process (PID 10720)
was started on **http://127.0.0.1:8000**; no other process was terminated. Exact startup command,
from the project root:

```bash
cd /Users/anuvikdas/Downloads/YTSponsorSkip/YTSponsorSkip
YTSS_DETECTOR_VARIANT=contextual_v1 YTSS_REQUEST_TIMEOUT_SECONDS=30 \
  .venv/bin/uvicorn ytsponsorskip.main:app --app-dir backend/src \
  --host 127.0.0.1 --port 8000
```

The actual HTTP checks used `source=saved&mode=conservative`, never a live acquisition source:

| Check | Actual response |
| --- | --- |
| `I9hJ_Rux9y0` | HTTP 200; 683–715 s; first response 11.87 ms API work |
| `U3aXWizDbQ4` | HTTP 200; zero intervals; 3.05 ms API work |
| Friends repeated | HTTP 200; transcript and detection cache hits; 0.263 ms API work |

Every response identified **`contextual-v1-sha256:cfee4293e5f725c8`**. The server was fresh, and
`DetectionService.detect` keys predictions by exact transcript identity, detector source version,
and mode. The contextual version hashes both the frozen and contextual source files. Frozen
predictions therefore cannot be served under a contextual cache key. The ordinary transcript
cache can be shared safely because it holds original cues rather than predictions. The extension
also checks video/request/mode/source identities and clears old state on navigation. Reopening the
popup reads session state; it does not initiate another backend request.

Manual Chrome acceptance remains pending for this variant. Automated HTTP checks do not establish
browser playback behavior. At `chrome://extensions`, reload the unpacked extension from
`/Users/anuvikdas/Downloads/YTSponsorSkip/YTSponsorSkip/extension`. In its Settings select:
**Preview detected promotions**, **Saved reviewed-tune transcript**, **Conservative**, and backend
**http://127.0.0.1:8000**. Keep manual fixtures and the browser acquisition probe unchecked.

1. Open [How To Make Friends at 11:20](https://www.youtube.com/watch?v=I9hJ_Rux9y0&t=680s).
   Expect **11:23–11:55** in the popup, **Preview only — automatic skipping off**, and normal
   playback through the interval.
2. Navigate in that same tab to [C in 100 Seconds](https://www.youtube.com/watch?v=U3aXWizDbQ4).
   The Friends prediction should clear immediately, then show **No promotions detected**.
3. Reopen the popup and confirm the current video's zero-prediction state remains. For a response
   identity check, inspect the extension service worker's Network response and verify the version
   above. No extra acquisition is needed.

Automated verification passed: **83** backend/view tests, **4** isolated semantic adapter and
partial-review evaluator checks, **23** extension tests, lint and diff checks. The extension tests
include preview without seeking, stale-result rejection, user seeks, Undo and the final merged
duration gate. These do not substitute for the manual acceptance steps above.

## New manual interval, with review scope preserved

`data/development/qf7ws2DF-zk-2026-10-22.json` records the user's confirmed **1331–1412 s**
promotion, with an approximate start. Only that interval is reviewed. Its previous partial
annotation, the versioned validation CSVs and the original frozen reports remain unchanged.
The saved Supadata transcript from the prior task is reused from Git-ignored
`results/development-transcripts/qf7ws2DF-zk.json`. No new Supadata request was made.

| qf known interval only, 81 s | Frozen rules | Contextual rules | Local semantic, each threshold |
| --- | ---: | ---: | ---: |
| Predicted range | 1398.33–1408.38 | 1334.49–1408.38 | None eligible |
| Known promotional seconds covered | 10.05 | 73.89 | 0 |
| Known promotional seconds missed | 70.95 | 7.11 | 81 |
| Matched start / end error | 67.33 / 3.62 s | 3.49 / 3.62 s | Unavailable |

The opening error is relative to the approximate manual start. Any prediction outside this
confirmed interval is unreviewed; it cannot be called a false skip from this annotation. No
full-video negative, precision or recall claim is made for qf. Cue durations also remain
approximate speech boundaries.

## Bounded local semantic experiment

The configuration and success criteria were committed **before inference** in `4337e88` at
`data/experiments/local-semantic-v1.json`. It freezes generic promotional/non-promotional
prototypes, an absolute positive similarity floor of 0.4, and margins 0.05/0.10/0.15. No
prototype or threshold was revised after results. The success gates were: **<=25 incorrect
seconds, zero negative videos with skips, <=188.96 missed seconds, >=12 matched intervals**, and
matched start/end MAE <=5/11 s. These demand both precision and recall improvement over contextual
rules; predicting nothing cannot pass.

The single local approach uses the frozen public `sentence-transformers/all-MiniLM-L6-v2` model,
revision **1110a243fdf4706b3f48f1d95db1a4f5529b4d41**, with ONNX Runtime **1.23.2**, Tokenizers
**0.22.1**, and NumPy **2.2.6** in an isolated development environment. The model publisher
describes a 384-dimensional sentence/paragraph embedding model and a 256-word-piece default
truncation limit. We use 224-token inputs, with no truncation. The implementation follows its
attention-mask mean pooling and L2 normalization instructions.
[Publisher model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).
[Official CPU runtime instructions](https://onnxruntime.ai/docs/get-started/with-python.html).

`build_views` scans every original cue using token-bounded views, targeting 32 overlapping tokens
at cue boundaries. Long cues are split only into exact-text analysis views, keeping their original
ID and timing. Boundary views prioritize each cue and include up to one neighbor on each side
when they fit. `LocalSemanticEncoder` embeds and caches those views, then scores maximum positive
prototype cosine similarity minus maximum negative similarity. `LocalSemanticDetector` exposes
cues from qualifying discovery windows, retains cues whose small context also qualifies, merges
touching/overlapping source ranges, and the shared evaluator applies final duration **>3 s**.
No source text, order, overlap or duration is edited. There is no label-derived context selector.
The approach is offline only and is not imported by FastAPI or the extension.

Similarity measures related wording and topic. It does not by itself identify persuasive intent,
creator ownership, or whether the passage interrupts the main content. All-window discovery can
expose subtle pitches with no rule anchor; candidate-only verification cannot see omitted content.
The second, cue-level semantic gate tests whether that broad semantic signal can also yield usable
boundaries without simply skipping the whole broad window. This is one narrow hypothesis test,
not a test of every possible local semantic model or supervised classifier.

## Results and failure stages

All **22** fully reviewed development videos were evaluated: the original 14 tune videos and
the eight formerly held-out videos now used as development evidence. Their 14 intervals total
**763 promotional seconds**, and nine videos are reviewed negatives. The original frozen
held-out report's SHA-256 remains
`6bf40b644b98cdec43733829998d8e0291056f30d4aaa14447e9825be92f1722`.
These results are not independent validation. Partial videos stay outside these totals.

| Conservative / eligible intervals | Incorrect seconds | Negative videos with skips | Missed seconds | Matches | Matched start/end MAE | Runtime for 22 videos |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen rules | 36.52 | 1/9 | 240.96 | 11/14 | 4.473 / 10.978 s | 0.325 s |
| Contextual rules | 36.52 | 1/9 | 208.96 | 12/14 | 4.100 / 10.063 s | 0.336 s |
| MiniLM margin 0.05 | 0 | 0/9 | 763 | 0/14 | Unavailable | 36.625 s |
| MiniLM margin 0.10 | 0 | 0/9 | 763 | 0/14 | Unavailable | 36.625 s |
| MiniLM margin 0.15 | 0 | 0/9 | 763 | 0/14 | Unavailable | 36.625 s |

All semantic settings fail the recall, match and boundary criteria. Their zero false skips come
from producing zero eligible intervals; that is not a worthwhile accuracy improvement. Relative
to contextual rules, all **554.04** previously covered promotional seconds are lost. Per-video
regressions and exact predictions are recorded in
`data/evaluation/local-semantic-development-2026-10-22.json`.

Representative evidence, inspected only after inference:

- **Friends creator pitch:** the all-window view at **662–715 s** contains both the friendship
  conclusion and the merchandise ask. Its positive similarity is **0.1045**, with margin
  **−0.0448**. It fails discovery before boundary refinement. The original cues at **683 s**
  (“we’ve created a few things”) and **710 s** (“our shop ... support us”) explain why the
  contextual rule retains 683–715 s, but these labels/cue locations were never supplied to the
  semantic encoder. This is a 32-second regression for semantics.
- **Nebula long pitch:** unlike frozen rules, margin 0.05 discovers a view at
  **2332.8–2392.68 s** with similarity **0.4832** and margin **0.0863**, including “Over on Nebula,
  I've got a new series” at **2340.66 s**. Cue-context classification then retains only fragments
  **2369.64–2370.72** and **2373.76–2376.72 s**. Both are removed by the final >3-second gate.
  The approach exposes a genuine rule-discovery gap but does not assemble a usable segment.
  Margins 0.10 and 0.15 do not qualify any discovery window.
- **Espresso negative:** the **74.48–115.52 s** review view has margin **−0.2874**, so semantics
  rejects the incidental “proposed mostly by my Patreon group” cue at **88.16 s**. Contextual
  rules still incorrectly predict **85.04–96.56 s**, because their broad window combines
  membership and ordinary product-review sales language. Fixing this one false skip does not
  compensate for losing every usable promotion.
- **qf:** the all-window views covering the confirmed interruption have negative margins.
  The **1331.91–1390.32 s** view scores **0.1788 / −0.0815**, so it is rejected during discovery.
  The direct sponsor and offer cues can resemble prototypes in short contexts while their broad
  surrounding explanation remains closer to non-promotional language. Contextual rules retain
  the sponsor-introduction link but still miss the first **3.49** and final **3.62** labeled
  seconds; those edges were not patched in this task.
- **Mixed Framework review:** contextual rules still predict **50–83 s** versus the user's
  **53–74 s** interval, creating 12 excess seconds. Saved cue ends were derived, so both semantic
  classification and source timing limit exact edges. The semantic setting merely abstains.

There were **496 discovery views and 6,249 boundary views** across the 22 videos plus qf; every
source cue was covered, max input 224 tokens, zero silent truncations. Dataset embeddings were
computed once on local CPU; all three settings reused that same evidence. Rule calls were fresh
local computations, not replayed predictions. Model load was **152 ms**, prototype encoding
**21 ms**, and incremental peak process memory approximately **402 MB** (462 MB total peak).
The reviewed-video encoding/scoring pass took **36.622 s**, mean **1.665 s/video**, range
**0.346–6.007 s**; five videos exceeded the 2-second warm target. qf added **2.009 s**. The table
charges that shared pass to each semantic option for fair latency comparison, not three separate
model passes. Weight download and installation are excluded. Cached embeddings and raw scores
remain Git-ignored, with model/view/transcript hashes; a rerun reports `cached_local_embeddings`
rather than presenting replay latency as fresh inference.

macOS NumPy emitted matmul floating-point warnings. Before accepting results, an independent
direct sum-of-products audit of every stored vector/prototype pair found zero non-finite scores,
unit-norm error <=5.97e-8 and maximum positive-similarity difference <=4.18e-7. The model output
shape was confirmed as token states with 384 channels. No scoring settings changed after this
audit. This numerical check does not establish classification accuracy.

## Reproduce and remaining demo work

The isolated runtime and model weights are excluded from Git and absent from production
dependencies. Reproduction uses the committed configuration, asset hashes and package lock:

```bash
.venv/bin/python -m venv tools/local-semantic/.venv
tools/local-semantic/.venv/bin/python -m pip install -r tools/local-semantic/requirements.lock.txt
tools/local-semantic/.venv/bin/python -m pip install --no-deps -e .
tools/local-semantic/.venv/bin/python tools/local-semantic/download_model.py
tools/local-semantic/.venv/bin/python scripts/run_local_semantic_experiment.py \
  --output /tmp/semantic-recheck.json --evidence-output /tmp/semantic-recheck-evidence.json
tools/local-semantic/.venv/bin/python -m unittest discover -s tools/local-semantic -p 'test_*.py'
```

No paid service or transcript acquisition was used; the persistent acquisition ledger remains at
**16 attempts**. The outcome supports stopping this prototype experiment. The next proposed
accuracy comparison is the single five-video, capped hosted intent test in
`docs/hosted-intent-comparison-proposal-2026-10-22.md`; it is not implemented or executed.

For the shortest **selected-case** recruiting demo, finish the Chrome preview acceptance above,
then add an explicit, default-off experimental skipping switch restricted to the agreed demo
video allowlist. Pass validated current-video predictions into the existing `PlaybackController`,
with final merged intervals >3 s. Connect its notification and Undo callbacks; preserve the
actual pre-skip position, user-seek suppression, and replay eligibility. Add integration checks
for predicted interval arrival while playing/paused, late results, Undo without immediate
re-skipping, and video/mode/source navigation, then repeat those in Chrome. Saved captions should
be visibly identified as saved input while intervals remain actual detector predictions. This
can demonstrate the engineering on selected videos despite known detector errors elsewhere.

Broader reliability claims require new fully reviewed, diverse videos kept untouched until the
detector is frozen, reliable acquisition/completeness evidence across sessions, and acceptable
false-skip and boundary rates on that independent set. They are separate requirements from a
clearly labeled, opt-in recruiting demonstration. Automatic skipping remains disabled today.
