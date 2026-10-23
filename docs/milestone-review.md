# Playback milestone review and next decision

Historical note (2026-10-07): the bounded Render experiment described below was completed and
stopped at `REQUEST_BLOCKED`; see `docs/render-small-experiment.md`. Manual tune transcripts are
now available and the unchanged detector result is in `docs/detector-tune-report.md`. The current
acquisition decision is `docs/acquisition-options-decision.md`.

## What this milestone establishes

Playback control no longer depends on transcript acquisition or a promotion detector. The controller accepts timestamp intervals, rejects stale video/request identities, skips only forward, respects explicit user seeking, supports Undo, and clears video-specific state on navigation.

Development playback intervals are manual annotations from fully reviewed `tune` videos. They are disabled by default and identified as `manual-tune-fixture` in the UI. They are not model detections. No saved transcript is used by this milestone.

The source workbook is preserved outside the repository. The normalized CSVs retain unknown caption types, blank categories, blank boundary certainty, and partial reviews without converting missing information into negatives. Held-out annotations are imported for later evaluation but are not exposed through development fixtures.

## Acquisition decision boundary

The formal acquisition study is recorded as IP-blocked. Playback development does not justify repeatedly sending the same corpus through that environment, adding a proxy, or paying for another service.

The smallest useful next acquisition experiment is one bounded probe from the intended Render Free service after it has gone idle:

1. Call `/health` and record startup time independently from acquisition.
2. Request one known manual-English video with a cache miss.
3. Repeat that request to measure the cache hit.
4. Request one known generated-English video.
5. Request one expected negative case.

This is at most three provider acquisitions. If health succeeds but both eligible captioned videos produce `IP_BLOCKED`, Render is not a viable acquisition host and a larger corpus run would add no useful evidence. If either eligible request succeeds, run one controlled corpus comparison before making a hosting decision. A paid proxy, paid host, or paid inference service remains out of scope until evidence and estimated monthly cost are reviewed.

## Proposed detector milestone

Keep `held_out` untouched until the detector and its decision thresholds are frozen. Iterate only on `tune` examples, using resampling or an internal tune-only validation fold when a comparison needs out-of-sample evidence.

1. **Transcript windows:** preserve original snippets and timing, then create overlapping context windows without treating snippet edges as promotion boundaries.
2. **Window classification:** start with a local, zero-cost baseline that assigns promotion likelihood and an optional supported category. Ambiguous relevant content should remain unskipped in Conservative mode; Aggressive mode can use a lower threshold only after evaluation.
3. **Boundary refinement:** join nearby positive windows, inspect neighboring snippets for topic transitions, and emit approximate interval bounds with uncertainty. Never claim that `start + duration` is an exact editorial boundary.
4. **Evaluation:** freeze the pipeline, then run once on `held_out` and report acquisition coverage separately from detector quality.

Required evaluation measures are:

- false-positive skipping on reviewed negative videos: both seconds skipped and videos with any false skip;
- missed promotional time: annotated promotional seconds not covered by predictions;
- boundary error: absolute start and end error for matched intervals, with the matching rule stated;
- latency: acquisition latency, detector latency, time until intervals become usable, and promotional time missed because results arrived late.

Segment precision/recall and overlap are useful supporting measures, but they do not replace the playback-centered measures above.
