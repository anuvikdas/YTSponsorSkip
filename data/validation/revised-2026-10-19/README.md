# Manual tune-label revision, 2026-10-19

These CSVs are a versioned copy of `../videos.csv` and `../segments.csv`, with only the four
user-verified tune decisions incorporated. The original import remains intact. They are manual
annotations, not independently verified ground truth. All held-out and partial-review records
are copied unchanged, and neither is used for tune evaluation.

- `I9hJ_Rux9y0`: change reviewed negative to a positive, with a creator-owned merchandise
  interval at 683–715 s.
- `O7sQBfpQCvU`: correct the interval end from 617 to 611 s.
- `aircAruvnKk`: correct the interval start from 992 to 1010 s; ordinary subscribe language
  is excluded, Patreon promotion retained.
- `-lErGZZgUbY`: retain the existing 53–74 s annotation; no interval change.

No caption type, category field, boundary certainty, or review date was inferred. Notes record
the date of the user's correction, not a fabricated original video-review date.
