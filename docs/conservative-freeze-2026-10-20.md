# Conservative detector freeze — 2026-10-20

This manifest was written before inspecting or generating held-out predictions. It freezes the
existing rules, not their quality. No held-out label is a detector input. Git base: `b0ded87`.

## Implementation identity

| Component | SHA-256 |
| --- | --- |
| `backend/src/ytsponsorskip/detector.py` | `764f1dba6f1929b1e00bbe5785f183f91a496bf10ce472603a7552bea185e62c` |
| `backend/src/ytsponsorskip/evaluation.py` | `b211aa4f02ef8aab2e3db6b1235285d761ad327007de81c6953c848cdbe191e7` |
| `scripts/evaluate_detector.py` | `54578328abafc6b863509e4902f0ce885d09727ba80d70828d6d02ec2c4c2d0e` |
| Revised video labels | `e931d4969aae5c015230b4afe9b75adfd59f6974432e6548e6859004230b3fe1` |
| Revised segment labels | `f5ae20577aca2acbd8dc8c4c576eeb7bd70b6d752784423c9547b109427b366c` |

Detector: `PromotionDetector(RulesWindowClassifier(), window_seconds=30, overlap_seconds=15)`;
mode `conservative`. Scores are heuristic, not calibrated probabilities. Transcript windows
overlap by 15 seconds and retain original cue indices. Conservative candidate anchors require
the `qualifies` combinations in source; neighboring supported windows can extend a candidate
across at most one neutral window, and selected groups join across at most 20 seconds. Cue-level
and 2–3-cue evidence refines start/end; a return-to-content phrase can shorten the end. The
refiner discards spans shorter than 10 seconds, then validates finite, nonnegative, increasing
times and merges overlapping intervals. It does not infer exact speech boundaries. Saved tune
cue durations are derived from starts; Supadata native durations are provider-reported
milliseconds normalized to seconds. Neither source guarantees exact promotional boundaries.

Policy: third-party sponsorships, affiliate sales, creator-owned merchandise/products/services,
and substantive Patreon/membership appeals can be promotional interruptions. Ordinary
subscribe/notification requests, names, reviews, and educational discussion alone are not.
Ambiguous relevant-content overlap remains a conservative error risk, not a reason to rewrite
annotations after evaluation. Playback policy separately merges touching/overlapping final
predictions and retains only durations **strictly greater than 3 seconds**. Predicted automatic
skipping remains disabled regardless of this evaluation.

Evaluator: `calculate_video_metrics` unions interval ranges, measures predicted-but-unannotated
and annotated-but-unpredicted seconds, and greedily matches positive-overlap pairs in descending
overlap order, one-to-one. Matched start/end errors are absolute seconds. Unmatched predictions
and annotations remain explicit counts. Partial reviews are excluded. `none` is a reviewed
negative, never a missing transcript. Raw detector output and playback-policy output are reported
separately. Matching depends on overlap, not semantic category.

Transcript acquisition for this held-out run: first use validated saved English timed cues, if
any; otherwise at most one native Supadata request per missing reviewed held-out ID, with
`lang=en`, `text=false`, `mode=native`, bounded polling/timeout, local free-credit preflight,
and the persistent 50-attempt ledger. A response must have usable timestamped English text.
Caption type remains unknown unless explicitly established. No generated transcription,
retries, paid services, or credential export. Acquisition failure means no detector result and
is excluded from conditional detector-quality denominators. The extension's live preview still
uses in-memory caching/coalescing; offline evaluation reads saved normalized inputs.

## Pre-held-out reference and exploratory criteria

The revised tune run (`data/evaluation/tune-rules-revised-2026-10-19.json`) covers 14/14 reviewed
tune videos: Conservative incorrectly predicted 25 seconds, affected 0/3 reviewed negatives,
missed 112 promotional seconds, matched 10 segments, mean absolute start/end error 2.8/7.7
seconds, and took 195.796 ms in that local run. These are reference observations, not held-out
acceptance thresholds.

For a **limited, explicit opt-in demo**, before seeing held-out predictions, require:

1. Usable timed English transcripts for all eight held-out videos. Otherwise acquisition is a
   separate blocking concern for a general live demo, even if conditional detector scores look good.
2. No predicted playback-eligible skip on any fully reviewed negative (safety-first on a tiny
   sample), and no more than 30 incorrectly predicted seconds in total. The 30-second ceiling
   allows roughly one modest boundary overrun, comparable to the tune result, but not a long
   irrelevant jump.
3. Miss no more than 25% of annotated promotional seconds and match every annotated segment.
   Missing more means a live skip demo is too inconsistent, even if it remains safe. Mean matched
   start and end errors should each be at most 10 seconds; longer errors need review before
   exposing automatic seeks.
4. No transcript-validation, detector, or stale-result error in the local demo checks. Live
   acquisition latency is reported separately rather than hidden in detector runtime; it is not
   a hard quality threshold because playback begins immediately and free-provider availability
   may vary.

These thresholds are deliberately exploratory, not a statistically supported reliability
claim. Eight videos and especially few negatives cannot bound rare false skips. A pass would
justify only a clearly opt-in, revocable local demonstration, with Undo and no default skipping;
it would not justify enabling skipping by default or claiming production reliability. A failure
points to detector or acquisition work depending on which criterion failed. Using held-out
mistakes to tune a later version retires this set as an untouched final test.
