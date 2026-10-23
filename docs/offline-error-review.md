# Offline error-review checkpoint — 2026-10-11

No detector rules changed. No acquisition, model inference, credentials, SDK, service, or expense
was introduced. The browser acquisition probe and extension were left unchanged. Predicted skips
remain disconnected from playback. The 14 fully reviewed tune transcripts are the entire scope;
partial reviews and held-out examples are excluded. Previous evaluations remain preserved.

## Open the review

Open `data/reviews/tune-2026-10-11/index.html` directly in Chrome (File → Open File). No backend
is needed. Conservative is selected initially. Select **Compare both**, search by title or video
ID, select **Only errors**, and expand **Timestamped transcript context**. Video titles and cue
times link to YouTube; nothing contacts YouTube until you click. The page does not load external
scripts, fonts, assets, or data. If a preview blocks inline JavaScript, open the file in Chrome.

The adjacent `error-review.md` contains all 14 videos, annotated/predicted interval comparisons,
exact false/missed ranges, candidate-stage spans, matching errors, and timestamped source text.
`review.json` is the machine-readable equivalent. Review interpretations are in
`data/reviews/tune-review-notes.json`; these never modify annotations or detector inputs.

## Findings against the supplied annotations

| Mode | Incorrect predicted seconds | Missed promotion seconds | Negative videos skipped | Start / end MAE |
| --- | ---: | ---: | ---: | ---: |
| Conservative | 25 | 104 | 0 / 4 | 4.6 / 8.3 s |
| Aggressive | 107 | 69 | 0 / 4 | 7.8 / 9.8 s |

Both overlap all ten annotated tune promotions. This is not perfect classification: matching
accepts **any positive overlap**, and the corpus is small and already used for tuning. Aggressive
recovers 35 annotated seconds while adding 82 incorrectly skipped seconds; that is not a good
default tradeoff. Original saved runtimes were 192.838 / 208.130 ms for the whole tune corpus;
new measured runtimes are separately recorded in `data/evaluation/comparison-2026-10-11.json`.
Replay time is validation/scoring overhead, not inference speed.

The new local run measured 182.999 ms Conservative / 184.575 ms Aggressive for all fourteen videos.
Its quality totals exactly reproduce the preserved current-rules result. The comparison also replays
the older `0d065ec` outputs (Conservative 16 false / 579 missed seconds), explicitly without claiming
to have re-executed that older detector or treating its replay overhead as detector latency.

The Conservative missed-time partition is disjoint:

- **95 s inside assembled candidate spans:** subsequently removed by cue-level refinement/policy.
  This locates the stage, not proof that all 95 s should be skipped.
- **1 s inside the observed transcript span but outside candidates:** candidate coverage omission.
- **8 s after the observed analysis span:** source/annotation uncertainty, not established
  classification failure. All 104 s still count in the original metric; none were silently removed.

Concrete cases:

- **Panels app, `MRtg6A1f2Ko`:** Conservative predicts 25–90 s against 35–104 s. The first cue
  mixes phone-review context and an app launch. The last explicit sales cue ends at 90; the
  app discussion continues until 104. Sparse lexical boundary evidence causes the short tail,
  not the return-to-content regex. Semantic continuation might help, but cue timing cannot locate
  the exact spoken transition within the mixed opening cue.
- **Charging products, `9lx11dy9J30`:** prediction ends at 942 versus label 962 despite continued
  benefits and a call to action. Aggressive only reaches 950. A later cue mixes a sales phrase and
  outro; snapping a return marker to the beginning of that cue would still lose promotional text.
- **Framework, `-lErGZZgUbY`:** 12 excess seconds partly reflect mixed cues; the transcript still
  describes security features and a sales link beyond the annotated end at 74. This needs video
  review before calling every excess second an actual content-damaging skip.
- **Immune, `lXfEK8G8CUI`:** a candidate covers 538–637, but refinement selects 561–619. Pre-order
  explanation and a link are dropped. Annotation 637–645 is beyond the source's derived end;
  its final cue starts at 633 and receives the importer's 4-second fallback.

### Annotation questions, not automatic corrections

1. `I9hJ_Rux9y0` is a reported negative. At 683–715 s the text offers pins, matching posters, and
   the creator's shop. This appears to fit our creator-owned promotion definition. Conservative
   has no candidate; Aggressive creates one but later rejects it. A future semantic detector
   could find a legitimate pitch yet score a false positive under this label. Please review it.
2. `O7sQBfpQCvU`: label ends 617; at 611 the speaker returns to making ice cream. Our 6-second
   measured miss might instead be a desirable boundary. Review the video, not only the text.
3. `aircAruvnKk`: label starts 992 during ordinary subscribe/notification discussion; explicit
   Patreon support starts 1010. Decide whether ordinary subscribe requests are in scope.

No labels were changed. Manual labels are not independently verified ground truth. Keep current
results immutable; if you revise an annotation, version the label set and rerun every comparator.

## How the tools separate responsibilities

- `offline_common.load_tune`: filters metadata to reviewed tune before opening transcripts or
  consuming segment values, validates cues, and hashes exact source files. No provider calls.
- `trace_rules`: runs existing window scoring/assembly **without labels**. Its candidate spans
  explain where time is lost, not a new detector or an oracle boundary selection.
- `review_video`: compares saved predictions with labels using existing interval math, partitions
  missed time, and selects nearby original cues. Only this evaluation/report stage sees labels.
- `render_html` / `render_markdown`: render the same review object. HTML escapes text and is
  standalone; controls filter existing content, with no frontend framework or local server.
- `summarize_rows`: the existing evaluator's aggregation extracted unchanged for reuse. Seconds
  use union/intersection, so overlapping predictions are not double-counted. Matching is greedy
  one-to-one by greatest overlap; start/end MAE use matched pairs only. Unmatched segments remain
  visible and are not hidden by the boundary average.
- `compare_detectors`: runs the current rules, then optionally replays saved evaluation/model
  outputs. It recomputes quality metrics; it never trusts a recording's old metric totals.

Classification and boundary diagnostics are not absolute semantic judgments. All ten labels have
overlapping predictions, so observed discrepancies are predominantly edge errors. Candidate
omissions and unpaired detections can reveal classification/assembly failures. Mixed-purpose cues,
derived end times, annotation policy, and source omissions can produce identical numeric symptoms.
Original starts/text/order remain untouched. No sponsor timestamp is used for windows, scores,
candidates, boundaries, or any proposed model request.

## Reproduce and compare

From the repository root with the existing Python 3.12 environment:

```bash
cd /Users/anuvikdas/Downloads/YTSponsorSkip/YTSponsorSkip
.venv/bin/python scripts/build_error_review.py --output-dir results/review-new
.venv/bin/python scripts/compare_detectors.py \
  --replay-evaluation data/evaluation/tune-rules-3c35ceb.json \
  --output results/comparison-new.json
.venv/bin/pytest
.venv/bin/ruff check .
node --test extension/tests/*.test.js
```

Use new output names on each run: tools intentionally refuse overwrites. You may also replay
`data/evaluation/tune-baseline-0d065ec.json` to compare the original rules without checking out old
code. New outputs record run time, Git HEAD, Python version, exact detector/evaluator/helper source
hashes, configuration/hash, selected label hash, corpus/hash, per-transcript SHA-256, predictions,
per-video quality and runtime. Git HEAD alone is insufficient for an uncommitted working tree;
the source hashes bind the actually executed code. Runtime varies by host/load, not determinism.

`paired_quality` includes only videos evaluated by **every** run in that mode. Per-run coverage and
missing recorded outputs remain visible; missing responses never become clean negatives. Quality
on unequal coverage is not a fair ranking. Empty paired cohorts return null metrics, not zero error.

### Optional model replay contract (no live-call path)

Pass `--replay-model path/to/recording.json` with this envelope:

```json
{
  "config": {
    "configuration_version": "experiment-identifier",
    "context_strategy": "whole_transcript_or_candidates",
    "boundary_version": "snippet-end-mapping-v1"
  },
  "records": []
}
```

Each actual record must contain `transcript_sha256`, `origin` (`recorded_model_response` or
`synthetic_fixture`), `request` conforming to `ModelDetectionRequest`, and `response` conforming to
`ModelDetectionResponse`. `provider_runtime_ms` is optional, measured at original collection time,
not replay time. See `docs/model-assisted-detector-design.md` for payload types. Request mode,
video/language, exact cue text/timing, request identity, prompt identity, evidence IDs and ranges
are validated. A segment may not bridge source cues omitted from its request. For overlapping
window calls, aggregate/resolve ranges into one validated record per video/mode before replay;
duplicate records are rejected rather than silently overwritten.

The contract keeps third-party and creator-owned promotions distinct. Replay maps IDs to the
source analysis spans, not invented precise spoken boundaries. Config identifies the experiment;
each row records actual prompt/model version and request/response hashes so mixed-version files
are auditable. A replay is not proof of a real provider call: `origin` is a provenance declaration,
not attestation. Synthetic tests do not establish model quality. No real model recordings are
included here. No SDK, key handling, inference method, retry, or billing code exists in this runner.

## Next decision

Review the three annotation-policy questions first. Then discuss the bounded $0 semantic experiment
in `docs/next-detection-experiment.md`. Do not freeze this detector, run final held-out evaluation,
or connect predictions to playback based on these tune results.

## Verification performed

- **Automated Python:** 42 tests passed, including 12 new tests for source provenance, tune-only
  selection, error-range arithmetic, exact missed-time partition, fresh/replayed metric equality,
  absent recordings, invalid ranges, model-contract replay, original cue identity, omitted-cue gaps,
  HTML escaping and overwrite refusal. Synthetic contract fixtures involve no model inference.
- **Automated JavaScript:** all 16 existing extension tests passed. These are not new manual
  playback or acquisition evidence. Ruff and `git diff --check` passed.
- **Actual automated browser:** isolated headless Google Chrome 155.0.8059.39, fresh temporary
  profile, local file only. Verified 14 videos; default Conservative; both-mode switching; title/ID
  search; 9 Conservative / 10 Aggressive error-video filters; empty search; context expansion;
  YouTube timestamp link format; annotation warning; mobile viewport without page overflow.
  No page errors or external page requests. Desktop/mobile screenshots were visually inspected.
  YouTube links were not followed, and no live acquisition or user-profile interaction occurred.
- **User-reported prior playback verification:** remains user-reported, not newly repeated here.
  The separate manual Chrome acquisition experiment is still being conducted by the user.

No final held-out evaluation or model-quality experiment has been run. Changes are local on
`codex/transcript-provider`; this checkpoint does not merge, push or deploy anything.
