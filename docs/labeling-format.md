# Promotion-labeling format

The evaluation set is independent from the transcript-acquisition corpus. A video may appear in both, but an acquisition result is never a promotion label. Start from `data/labeling_template.xlsx`, which contains empty **Videos** and **Segments** sheets with validation lists and no fabricated examples.

## Videos table

Columns, in order:

`video_id, url, title, caption_type, review_status, promotion_status, split, notes`

- `video_id`: the 11-character YouTube ID; one row per video.
- `url`: the watch URL used during review.
- `title`: title observed during review.
- `caption_type`: `manual`, `generated`, `none`, or `unknown`.
- `review_status`: `unreviewed`, `in_progress`, or `reviewed`.
- `promotion_status`: `unknown`, `none`, or `one_or_more`.
- `split`: `tune`, `validation`, or `held_out`.
- `notes`: optional review context or ambiguity notes.

A fully reviewed video with no promotions is represented by `review_status=reviewed`, `promotion_status=none`, and zero Segments rows. An unreviewed video has `review_status=unreviewed` and `promotion_status=unknown`; the absence of Segments rows is not evidence that it contains no promotions.

## Segments table

Columns, in order:

`video_id, segment_number, category, start_seconds, end_seconds, boundary_certainty, notes`

- `video_id`: must refer to a Videos row.
- `segment_number`: starts at 1 and is unique within a video; use 2, 3, and so on for multiple promotions.
- `category`: `third_party_sponsor`, `affiliate`, `merchandise`, `membership`, `self_promotion`, `creator_product_service`, or `other_promotion`.
- `start_seconds` and `end_seconds`: playback positions in decimal seconds. Both are nonnegative and `end_seconds` must be greater than `start_seconds`.
- `boundary_certainty`: `exact`, `approximate`, or `uncertain`.
- `notes`: explain overlap with main content, difficult transitions, or other labeling judgment.

Caption snippet timestamps may help navigation, but they are not promotion boundaries. Preserve the reviewer-observed playback boundaries independently from transcript snippet `start` and `duration`.

## Split discipline

Keep every segment for one video in the same split as its Videos row.

- `tune`: may be inspected while changing detector rules, prompts, or thresholds.
- `validation`: may be used for periodic comparison after a candidate detector is defined.
- `held_out`: must not be inspected or used to tune detection. Use it only for the final unbiased evaluation for a milestone.

Do not move difficult examples out of held-out after seeing detector results. Record ambiguous promotion/content overlap in `notes` and `boundary_certainty` rather than silently changing the label.

## Google Sheets and import

Upload `data/labeling_template.xlsx` to Google Drive and choose **Open with Google Sheets**. Keep the two sheet names and header rows unchanged. Google Sheets preserves the dropdown validation, formatting, and numeric timestamp columns.

For a CSV workflow, download each tab separately as `videos.csv` and `segments.csv`. CSV does not preserve dropdowns or styling, so validation happens during import. The planned importer will:

1. Read Videos first and reject duplicate or malformed video IDs and invalid categorical values.
2. Read Segments and verify that every `video_id` exists in Videos.
3. Reject duplicate `(video_id, segment_number)` pairs and invalid or reversed timestamps.
4. Enforce the reviewed/no-promotion and reviewed/one-or-more consistency rules.
5. Keep held-out rows available for evaluation but excluded from detector-tuning inputs.

Do not place formulas, merged cells, explanatory rows, or extra headers inside either table. Put free-form context in the `notes` columns.
