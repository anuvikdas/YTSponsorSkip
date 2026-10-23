# Explainable detector tune iteration

Reviewed 2026-10-07. This is a tune-only development result, not a held-out estimate and not a
frozen detector. Predictions remain disconnected from playback.

## Scope and reproducibility

- Input: all 14 fully reviewed `tune` transcripts; 10 promotion videos and 4 reviewed negatives.
- Excluded: both partial reviews and every `held_out` video.
- Labels: evaluation targets only. No video ID, brand, label timestamp, or label text was added to
  the rules.
- Preserved baseline: `data/evaluation/tune-baseline-0d065ec.json` from detector commit `0d065ec`.
- Iteration: detector commit `3c35ceb`; source SHA-256
  `764f1dba6f1929b1e00bbe5785f183f91a496bf10ce472603a7552bea185e62c`.
- Result: `data/evaluation/tune-rules-3c35ceb.json`.

Reproduce the iteration without reading held-out labels:

```bash
.venv/bin/python scripts/evaluate_detector.py \
  --source-dir data/transcripts/tune \
  --detector-commit 3c35ceb02c84d1facd025ec8d012e09d592a6e00 \
  --output data/evaluation/tune-rules-3c35ceb.json
```

## What changed

`RulesWindowClassifier.score` now records separate, auditable signals for disclosure, affiliate
language, creator ownership, membership, offers, calls to action, URLs, sales language, and
transitions. A disclosure alone is not enough. `qualifies` requires a relationship signal plus a
commercial action, while `supports` lets nearby promotional context extend an anchored candidate.

The changes are deliberately general:

- typographic punctuation and whitespace are normalized before matching;
- sponsorship, spoken URLs (`example dot com`), and calls to action have less literal forms;
- creator-owned books, courses, apps, shops, memberships, and services are distinct from ordinary
  product discussion;
- sales evidence requires both a product concept and a commercial action, avoiding cases such as
  “of course” accidentally matching “course”;
- `assemble_candidates` may bridge a small neutral gap only when it reconnects to relationship
  evidence; and
- `_boundary_signal_positions` checks one-, two-, and three-snippet spans, retaining evidence that
  exists only when generated captions split a phrase across cues.

`refine_boundaries` still maps evidence back to original snippet identities. It rejects a signal
core under 10 seconds, scans for explicit return-to-content language, and expands one neighboring
snippet only in Aggressive mode. `validate_intervals` remains responsible for finite, nonnegative,
ordered, merged output intervals.

## Before and after

Runtime is a single local run over all 14 videos, so it shows scale, not a benchmark distribution.

| Mode and detector | Incorrect predicted seconds | Negative videos with a skip | Missed promotional seconds | Matched segments | Mean start error | Mean end error | Runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Conservative baseline | 16 | 0/4 | 579 | 0 | n/a | n/a | 58.994 ms |
| Conservative iteration | 25 | 0/4 | 104 | 10 | 4.6 s | 8.3 s | 192.838 ms |
| Aggressive baseline | 36 | 0/4 | 579 | 0 | n/a | n/a | 74.467 ms |
| Aggressive iteration | 107 | 0/4 | 69 | 10 | 7.8 s | 9.8 s | 208.130 ms |

All 10 annotated promotion videos now have an overlapping prediction. Conservative is the safer
current policy: compared with Aggressive it gives up 35 seconds of recall but avoids 82 seconds of
additional incorrect skipping. That tradeoff supports keeping Conservative as the default.

This is training-set feedback. The same 14 videos informed the rule changes, so these numbers
cannot establish generalization.

## Representative outcomes

- `iWeu2dxHRDg`: Conservative predicts 1050–1098, exactly the annotated interval. Combined offer,
  call-to-action, sales, and URL evidence works without a sponsor-name rule.
- `094y1Z2wpJg`: Conservative predicts 1254–1326 versus 1248–1327, missing 7 seconds but adding no
  time outside the annotation.
- `aircAruvnKk`: creator-owned membership evidence finds 1010–1023, but misses the first 18 seconds
  because the opening language lacks a strong commercial anchor.
- `lXfEK8G8CUI`: creator-owned/offer evidence finds 561–619 versus 558–645, missing 29 seconds. The
  trailing product explanation stops producing explicit signals before the human boundary.
- `-lErGZZgUbY`: Conservative predicts 50–83 around a 53–74 label. It recovers the short pitch but
  adds 12 seconds because cue-level evidence and derived cue ends are coarse.
- `MRtg6A1f2Ko`: Conservative starts 10 seconds early and ends 14 seconds early. Candidate detection
  is correct, but boundary language is not explicit enough for exact refinement.
- All four reviewed negative videos receive no predicted interval in either mode.

## Timing limitation

The manually collected source contained cue starts but no source end/duration. Import therefore
derived each analysis span from the next cue start (and a documented final-cue fallback). The
detector preserves those values, but `start + duration` is not a human promotional boundary and is
not necessarily the exact time speech ends. Consequently:

- end-boundary error includes import granularity as well as detector error;
- one neighboring cue can move an interval several seconds;
- overlap seconds are appropriate for comparing versions on this fixed data, but not precise
  claims about real playback; and
- future acquisition with original cue durations must remain distinguishable from derived spans.

Do not freeze thresholds or evaluate `held_out` until browser-acquisition evidence and the next
candidate detector comparison are reviewed.
