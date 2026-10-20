# Partially reviewed development example: `qf7ws2DF-zk`

This is a **tune/development** example, not an untouched test item. The user manually confirmed
that a promotion begins **around 22:11 (1331 s)**. The actual end has **not** been reviewed. The
user reported that a Conservative Chrome preview predicted **23:18.3–23:28.4
(1398.3–1408.4 s)**, a start gap of **67.3 s** relative to the approximate manual opening. The
user-reported preview's transcript source and detector version were not provided. Category,
caption type, title, exact start, and end remain unfilled in
`data/development/partial-qf7ws2DF-zk.json`.

This record is deliberately separate from the versioned 24-video validation CSV pair: changing
that pair would invalidate the frozen held-out evaluation hashes, and a segment with no confirmed
end cannot satisfy its complete-interval schema. It is **not** a negative video or a completed
positive interval. Do not include it in full-video false-skip, missed-seconds, matched-segment,
or end-boundary metrics. A future comparison can report approximate opening lag for this
development example, with its uncertainty clearly marked.

## Stage-trace status

No saved transcript for this ID was found in tracked tune/held-out data, ignored local response
records, or Downloads during this check. The persistent Supadata ledger already contains **one**
`supadata-native` acquisition for this video at **2026-10-20 05:45:29 UTC**, consistent with the
user's preview, but the backend's preview response holds intervals rather than source cues. A
duplicate credit-bearing acquisition was not sent. Thus the cause of the missing opening is
**unresolved**, not confirmed as candidate exclusion or boundary trimming.

When a normalized, original timed transcript for this same acquisition/source is available, run
the label-free stage tracer from the repository root:

```bash
.venv/bin/python scripts/trace_detector_stages.py \
  --source data/transcripts/development/qf7ws2DF-zk.json \
  --focus-seconds 1331 \
  --output results/qf7ws2DF-zk-stage-trace.json
```

The source must use the existing normalized JSON form: `video_id`; `transcript` with English
`language_code`, provider/version, and unknown `is_generated` if not established; and a nonempty
ordered `snippets` array with `index`, original `text`, `start_seconds`, and `duration_seconds`.
Do not fabricate durations or replace provider cue text. `focus-seconds` selects diagnostic
output **after** `build_windows`, `RulesWindowClassifier.score`, `assemble_candidates`, and
`PromotionDetector.detect` run on the entire transcript. The report lists nearby original cues,
windows, anchor/support scores, candidate spans, and final intervals:

- If 1331 lies within available cue timing but outside every candidate, the opening was lost
  during window scoring or candidate assembly.
- If it lies inside a candidate but outside final intervals, boundary refinement or its
  ten-second minimum removed it.
- If it lies outside available cue timing, source completeness/timing must be investigated.

Because 1331 is approximate, inspect neighboring cues and windows rather than treating one point
classification as an exact boundary diagnosis. Also verify that offline predictions reproduce
the reported **1398.3–1408.4 s** interval before attributing the Chrome result to the frozen
rules: a different transcript source, cue segmentation, or detector version could change it.
The script never uses manual sponsor times to select candidates, score cues, or refine boundaries.

## Context-aware comparison requirement

This case is an explicit **opening-recall diagnostic** for the next $0 local semantic experiment.
Compare all-window discovery against broad rule-candidate verification on the same saved cues.
Record whether each arm exposes the cue neighborhood around the approximate 1331-second opening
to its classifier, whether it recognizes a promotional interruption rather than topical content,
and whether its boundary module retains the opening. Candidate-only verification cannot recover
speech that its candidate stage never supplies. Conversely, a wider semantic discovery pass may
increase false skips on product reviews and ordinary mentions. Keep the unchanged rules as the
baseline, record the transcript/config hashes, and leave predicted automatic skipping disabled.
Do not set a video-specific threshold or cue exception. Once the actual end is reviewed, version
the annotation and only then consider complete-interval metrics.
