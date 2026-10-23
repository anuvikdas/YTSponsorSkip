# Validation-label import report

Source workbook: `/Users/anuvikdas/Downloads/SponsorSkip_Validation.xlsx`  
Source SHA-256: `7d6bc34d90ccee15fa9311bf52340048b0a16bfc77ae358bb4b0a180248e2c38`  
Source preserved unchanged: `true`

## Result

- Import errors: 0
- Videos: 24
- Videos with promotions: 12
- Promotional intervals: 13
- Reviewed negatives: 10
- Partial reviews retained as `in_progress` / `unknown`: 2
- Split counts: 16 tune, 8 held_out
- Duration-bound checks performed: 0

`Development` was mapped to `tune`; `Held-out` was mapped to `held_out`. `Fully reviewed`, `Partial`, `Present`, and `None` were mapped to the project enums without changing label meaning. Only `review_notes` was mapped into Videos `notes`; candidate-selection metadata was excluded from normalized labels.

These are user-supplied manual annotations. The import validates structure and consistency; it does not independently verify the labels against the videos.

## Incomplete annotations, not import errors

- Unknown caption type: 24 videos
- Missing review date: 24 videos
- Missing video duration: 24 videos
- Missing segment category: 13 intervals
- Missing boundary certainty: 13 intervals

Blank category and boundary-certainty fields remain blank. Unknown caption types remain `unknown`. No review dates, durations, categories, or certainty values were invented. Held-out rows are retained for future evaluation but must not be used by development fixtures or detector tuning.

## Validation errors

- None.

## Warnings

- No source video durations were supplied; timestamp bounds could not be checked against video duration.
