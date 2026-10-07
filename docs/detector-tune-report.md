# Offline detector tune-set report

Run date: 2026-10-07. Detector: deterministic rules baseline. Split: `tune` only.

The follow-up Node experiment tested YouTube.js 18.1.0 and `youtube-transcript` 1.3.1 on
`aircAruvnKk` and `U3aXWizDbQ4`. Neither returned snippets, so the coverage and metric status below
is unchanged. See `docs/node-acquisition-experiment.md` for exact failures and latencies.

## Transcript inventory and coverage

The inventory examined the ignored earlier local experiment files and both attached Render responses. Earlier successful local records predate snippet preservation and therefore contain acquisition metadata but no transcript text. The two attached files contain the same 61-snippet `dQw4w9WgXcQ` manual transcript, which is not a labeled tune video.

Of 16 tune rows, two partial reviews (`jHP942Livy0` and `DTsQjiPlksA`) were excluded. Of the remaining 14 fully reviewed tune videos:

- usable saved transcripts: 0/14;
- `aircAruvnKk`: an earlier success record exists, but it contains no snippets;
- the other 13: no saved transcript with snippets;
- held-out rows used: 0;
- manual segment timestamps used as detector inputs: 0.

Acquisition stopped after the bounded Render request returned `REQUEST_BLOCKED`. No transcript or label was fabricated.

## Tune metrics

| Metric | Conservative | Aggressive |
| --- | ---: | ---: |
| Evaluated reviewed tune videos | 0 | 0 |
| Incorrectly predicted promotional seconds | unavailable | unavailable |
| Negative videos with any predicted skip | unavailable | unavailable |
| Missed promotional seconds | unavailable | unavailable |
| Matched intervals | unavailable | unavailable |
| Mean start/end boundary error | unavailable | unavailable |
| Detection runtime | unavailable | unavailable |

These values are unavailable, not zero: the detector was not run on any labeled tune transcript. Acquisition coverage is the blocker; this is not a detector failure or a favorable detector result. There are consequently no honest tune-set representative mistakes to report yet. The documented limitations and synthetic tests are expectations, not observed real-video errors.

As a non-evaluative smoke check, the detector processed the attached, unlabeled `dQw4w9WgXcQ` transcript in 0.737 ms for Conservative mode and 0.691 ms for Aggressive mode on this machine. Both produced zero intervals across 14 windows. This demonstrates execution only; the video is outside the labeled tune set, so these numbers do not contribute to accuracy metrics or representative mistakes and are not a stable performance benchmark.

## Metric definitions

Predicted and annotated intervals are merged separately before duration calculations. Incorrect predicted seconds are the prediction union outside the annotation union. Missed promotional seconds are the annotation union outside the prediction union.

Boundary error uses one-to-one greedy matching: all prediction/annotation pairs with positive temporal overlap are ranked by overlap duration, then the largest unused pair is selected repeatedly. Start and end error are absolute timestamp differences for those matched pairs only. Unmatched annotations contribute to missed time; unmatched predictions contribute to incorrect predicted time.

Partial reviews are excluded from full-video metrics. Acquisition failures and records without snippets are coverage exclusions, not detection errors.

## Reproduce the inventory

```bash
.venv/bin/python scripts/evaluate_detector.py \
  --source results/local.json \
  --source results/local-docker.json \
  --source /Users/anuvikdas/Downloads/response_1791398895131.json \
  --source /Users/anuvikdas/Downloads/response_1791399042162.json \
  --output /tmp/ytsponsorskip-detector-tune.json
```

The evaluator is ready to recompute both modes once snippet-bearing tune transcripts are available. Held-out evaluation must wait until rules and thresholds are frozen.
