# Offline detector tune-set report

Run date: 2026-10-07. This is the preserved initial real-data baseline, before rule tuning.

## Reproducible scope

- Detector commit: `0d065eccc10952ac3f1c2a416a0b7e4929e39026`
- Detector source SHA-256: `932640533d30c92321f6ae51bc671b9354f68709faa3c3a0218393d60cbfdb92`
- Classifier: `RulesWindowClassifier`
- Windows: 30 seconds with 15-second overlap
- Candidate join gap: 5 seconds Conservative; 15 seconds Aggressive
- Inputs: 14/14 fully reviewed tune transcripts; 14 distinct input hashes are recorded in
  `data/evaluation/tune-baseline-0d065ec.json`
- Excluded: partial tune videos `jHP942Livy0` and `DTsQjiPlksA`; every held-out video
- Manual sponsor intervals were evaluation targets only, never detector input

The detector source was not changed before this run. Detection runtime excludes DOCX parsing,
normalization, and transcript acquisition.

## Aggregate results

The ten positive videos contain 579 annotated promotional seconds in total. Four reviewed negative
videos contain no annotated promotions.

| Metric | Conservative | Aggressive |
| --- | ---: | ---: |
| Evaluated reviewed tune videos | 14 | 14 |
| Incorrect predicted promotional seconds | 16.0 | 36.0 |
| Negative videos with any predicted skip | 0/4 | 0/4 |
| Missed promotional seconds | 579.0 | 579.0 |
| Matched prediction/annotation pairs | 0 | 0 |
| Mean start boundary error | unavailable | unavailable |
| Mean end boundary error | unavailable | unavailable |
| Total detection runtime, one local run | 58.994 ms | 74.467 ms |

This baseline found none of the labeled promotional time. It produced three early-video false
positive intervals, all on positive videos, so the negative-video metric alone would give a
misleadingly favorable impression. Boundary error is unavailable—not zero—because no predicted
interval overlapped an annotation and therefore no pair could be matched. Runtime is a single
machine/run observation, not a benchmark distribution.

## Per-video comparison

An em dash means no interval. Times are half-open seconds `[start, end)`.

| Video | Annotated intervals | Conservative predictions | Aggressive predictions | Conservative incorrect / missed | Aggressive incorrect / missed |
| --- | --- | --- | --- | ---: | ---: |
| `094y1Z2wpJg` | 1248–1327 | — | — | 0 / 79 | 0 / 79 |
| `bHIhgxav9LY` | 813–882 | 0–3 | 0–6 | 3 / 69 | 6 / 69 |
| `iWeu2dxHRDg` | 1050–1098 | — | — | 0 / 48 | 0 / 48 |
| `DTvS9lvRxZ8` | — | — | — | 0 / 0 | 0 / 0 |
| `I9hJ_Rux9y0` | — | — | — | 0 / 0 | 0 / 0 |
| `lXfEK8G8CUI` | 558–645 | — | — | 0 / 87 | 0 / 87 |
| `-lErGZZgUbY` | 53–74 | — | — | 0 / 21 | 0 / 21 |
| `MRtg6A1f2Ko` | 35–104 | — | — | 0 / 69 | 0 / 69 |
| `9lx11dy9J30` | 903–962 | — | — | 0 / 59 | 0 / 59 |
| `Sew4rctKghY` | 724–788 | 0–8 | 0–20 | 8 / 64 | 20 / 64 |
| `O7sQBfpQCvU` | 565–617 | 20–25 | 19–29 | 5 / 52 | 10 / 52 |
| `U3aXWizDbQ4` | — | — | — | 0 / 0 | 0 / 0 |
| `x7X9w_GIm1s` | — | — | — | 0 / 0 | 0 / 0 |
| `aircAruvnKk` | 992–1023 | — | — | 0 / 31 | 0 / 31 |

## Metric definitions

Predicted and annotated intervals are merged independently before measuring time. Incorrect
predicted seconds are the prediction union outside the annotation union. Missed promotional
seconds are the annotation union outside the prediction union.

Boundary matching first enumerates prediction/annotation pairs with positive temporal overlap,
ranks them by overlap duration, and greedily selects the largest still-unused pair. Boundary error
is the absolute start or end difference for selected pairs only. An unmatched annotation adds
missed time; an unmatched prediction adds incorrect time. Partial reviews are excluded from all
full-video metrics. Transcript acquisition failures would be coverage exclusions, not detector
errors; this run had none because all 14 manual imports were usable.

## Representative failures

1. **Disclosure is treated as a skippable pitch.** The three predictions are short opening
   disclosures on `bHIhgxav9LY`, `Sew4rctKghY`, and `O7sQBfpQCvU`. A disclosure phrase alone has
   enough rule score to qualify, although the labels place the promotional interruptions much
   later. Aggressive boundary expansion turns 16 false seconds into 36.
2. **Window evidence is lost during snippet refinement.** Around 895–903 seconds in
   `9lx11dy9J30`, separate snippets combine to say “thanks to Anor for sponsoring this video.” The
   window classifier sees the phrase, but boundary refinement rescoring one snippet at a time does
   not. The candidate disappears before interval validation.
3. **The vocabulary is too literal.** `094y1Z2wpJg` uses “the sponsor of this video,”
   `brilliant.org`, and “link down in the description”; these variants do not satisfy the current
   phrase combinations. `-lErGZZgUbY` also shows generated-caption corruption around a sponsor
   name, exposing brittle exact patterns.
4. **Creator-owned promotions lack robust ownership signals.** `iWeu2dxHRDg`, `lXfEK8G8CUI`, and
   `MRtg6A1f2Ko` discuss a creator's kit/book/app using launch, preorder, subscription, and
   link-in-description language that is outside the narrow current creator-owned patterns.
5. **No boundary behavior was exercised on a true positive.** With zero matched intervals, this
   run cannot validate refinement quality. The source supplies starts only, so even a future match
   will include uncertainty from next-start-derived analysis spans.

## Targeted changes to discuss before implementation

- Separate disclosure-only evidence from an actual sales pitch; a disclosure may locate a nearby
  sponsor but should not by itself create a skippable interval.
- Pass window-level evidence into boundary refinement so phrases split across adjacent snippets do
  not disappear when individual snippets are rescored.
- Add explainable phrase families for creator ownership, calls to action, purchase/subscription,
  affiliate codes, URLs, and description links; require contextual combinations so product names,
  reviews, and educational discussion remain insufficient alone.
- Evaluate each small rule change against all tune positives and negatives, reporting time metrics
  and examples. Freeze the rules only after the tune results are acceptable; then run held-out
  evaluation exactly once.

Predictions remain disconnected from playback and Conservative remains the product default.
