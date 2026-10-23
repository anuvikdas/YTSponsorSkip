# Revised tune evaluation — 2026-10-19

The user corrected four decisions after watching the videos. The versioned CSV pair is in
`data/validation/revised-2026-10-19/`; the original imported CSVs and earlier reports remain
untouched. These are user-verified manual annotations, not independently verified ground truth.
Only the 14 fully reviewed tune videos enter this report; both partial reviews and all held-out
videos remain outside evaluation. There are now **11 positive** and **3 negative** reviewed tune
videos, with **11 labeled intervals**. Across the entire 24-video sheet, the revised counts are
13 positive, 9 negative, 2 partial, and 14 labeled intervals. No caption type, category field,
boundary certainty or original review date was inferred.

Promotion policy: creator-owned merchandise and Patreon appeals are eligible promotional
interruptions, as are relevant third-party pitches. A routine subscribe/notification request
alone is not a skippable promotion. A brand name, product review, or educational mention alone
is also insufficient. Mixed-purpose content requires conservative treatment; do not extend the
confirmed Framework annotation beyond 53–74 s. These decisions update evaluation labels and
manual development fixtures, **not** detector rules.

| Mode | Labels | Incorrect predicted seconds | Negative videos with skips | Missed promotional seconds | Matched segments | Start/end mean absolute error |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Conservative, original | Original | 25 | 0/4 | 104 | 10 | 4.6 / 8.3 s |
| Conservative, revised | Revised | 25 | 0/3 | 112 | 10 | 2.8 / 7.7 s |
| Aggressive, original | Original | 107 | 0/4 | 69 | 10 | 7.8 / 9.8 s |
| Aggressive, revised | Revised | 111 | 0/3 | 81 | 10 | 6.4 / 9.6 s |

These changes are from labels only: the detector source and saved transcript inputs are
unchanged. The conservative 683–715 s merchandise pitch is a 32-second missed promotion rather
than a reviewed negative, while corrections at ice cream and neural network remove previously
counted misses. Aggressive also misses the merchandise pitch and now counts 4 additional seconds
past the corrected ice-cream end. The negative denominator drops from four to three. Mean
boundary errors shift because two corrected labels moved; no detector boundary was retuned.
Runtimes on this local run were 195.796 ms Conservative and 196.274 ms Aggressive for all 14
videos; these are run-to-run measurements, not effects of the annotation correction.

The separate playback-policy view merges touching/overlapping final predictions and keeps only
intervals **strictly longer than 3 seconds**. All final predictions in this particular run already
pass that gate, so the playback-policy metrics numerically equal the revised detector metrics.
This equality is data-dependent, not a claim that the gate has no effect in general. Shorter
predictions remain in detector output and evaluation. Automatic skipping from detector predictions
is still disabled; current extension fixtures are explicitly manual development data.

Representative remaining issues: Conservative entirely misses the 32-second merchandise pitch
(`I9hJ_Rux9y0`), a classification/candidate-assembly failure; it ends the immune-system and
iPhone-impressions promotions early, contributing 29 and 20 missed seconds respectively, where
cue-level boundary refinement and incomplete candidate support matter. Framework predicts
50–83 s against the retained 53–74 s label, creating 12 excess seconds. Those edges are partly
uncertain because source cue durations were derived, and neither the labels nor source transcript
give exact speech boundaries. See the timestamped, per-video
`data/reviews/tune-revised-2026-10-19/index.html` for candidate traces and cue context.

Reproduce without acquisition or inference:

```bash
.venv/bin/python scripts/evaluate_detector.py --source-dir data/transcripts/tune \
  --videos data/validation/revised-2026-10-19/videos.csv \
  --segments data/validation/revised-2026-10-19/segments.csv \
  --detector-commit 3c35ceb02c84d1facd025ec8d012e09d592a6e00 \
  --output /tmp/tune-rules-revised-check.json
```

The canonical saved evaluation is `data/evaluation/tune-rules-revised-2026-10-19.json`; the
new review HTML and Markdown live in `data/reviews/tune-revised-2026-10-19/`. Original artifacts
are intentionally not overwritten. Manual sponsor timestamps enter only the metrics and error
review after detection returns; they are never detector inputs.
