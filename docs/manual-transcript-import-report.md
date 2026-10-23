# Manual tune-transcript import

Run date: 2026-10-07. Input: the user-supplied `SponsorSkip Manual 14 Transcript Collection.docx`.

## Outcome

The importer matched all 14 document sections to the 14 fully reviewed `tune` video IDs. It wrote
14 normalized transcript files containing 2,567 snippets to `data/transcripts/tune/`. There were
no missing, duplicate, unexpected, or structurally invalid sections. Held-out videos and the two
partial tune reviews were not imported, and sponsor annotations were not read as detector input.

The original DOCX was read only and retained unchanged. Its SHA-256 is
`15d88d1af0aad45603d53e2b9c7a52785ab0b908c259a33b5d2728c7a864e821`; the hash and source
metadata are also stored in `data/transcripts/tune/import-report.json` and every normalized file.
The document's `Complete`, `Completed`, and misspelled `Competed` values are retained as raw values
and normalized to the user-reported status `complete`. They are not independent proof that the
copied transcript is complete.

| Video | Source layout | Caption type | Snippets | First–last source start | Duplicate starts | Gaps >10 s | Warnings |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `094y1Z2wpJg` | alternating | generated | 492 | 0–1326 | 1 | 1 | 0 |
| `bHIhgxav9LY` | alternating | manual | 374 | 0–885 | 3 | 0 | 0 |
| `iWeu2dxHRDg` | embedded | manual | 159 | 0–1098 | 0 | 14 | 0 |
| `DTvS9lvRxZ8` | embedded | manual | 128 | 0–995 | 0 | 21 | 0 |
| `I9hJ_Rux9y0` | alternating | generated | 150 | 6–710 | 0 | 0 | 1 |
| `lXfEK8G8CUI` | alternating | manual | 157 | 0–633 | 0 | 1 | 0 |
| `-lErGZZgUbY` | embedded | generated | 130 | 0–1054 | 0 | 3 | 0 |
| `MRtg6A1f2Ko` | embedded | manual | 184 | 0–1235 | 0 | 19 | 0 |
| `9lx11dy9J30` | embedded | generated | 122 | 4–968 | 0 | 0 | 1 |
| `Sew4rctKghY` | embedded | unknown | 91 | 0–784 | 0 | 22 | 0 |
| `O7sQBfpQCvU` | alternating | manual | 150 | 0–613 | 0 | 0 | 0 |
| `U3aXWizDbQ4` | alternating | generated | 72 | 0–143 | 0 | 0 | 0 |
| `x7X9w_GIm1s` | alternating | generated | 72 | 0–141 | 0 | 0 | 0 |
| `aircAruvnKk` | alternating | unknown | 286 | 4–1105 | 0 | 0 | 1 |

Caption totals are six manual, six generated, and two unknown. `Sew4rctKghY` was reported unknown.
The document calls `aircAruvnKk` generated while the existing acquisition corpus records it as
confirmed manual; the importer does not choose between conflicting evidence and stores `unknown`.

## Validation findings

- All parsed starts are integral seconds, nonnegative, nondecreasing, and retained at the source's
  one-second precision. Original text and source order are preserved.
- Four duplicate starts across two videos are preserved. Snippets sharing a start also share the
  next distinct start as their derived end, so their analysis spans overlap rather than silently
  dropping or reordering either snippet.
- The report flags 81 consecutive-start gaps greater than 10 seconds. These are review flags only:
  sparse copied cues, chapter transitions, music, and legitimate silence can all produce a gap.
  They are not automatically classified as missing text.
- One opening line in `I9hJ_Rux9y0` has no timestamp and is excluded with
  `UNTIMESTAMPED_TRANSCRIPT_TEXT`. This is an import limitation and possible leading omission.
- The raw `Competed` status for `9lx11dy9J30` is retained and normalized with a warning.
- Chapter labels, section headings, collection notes, and status fields are recorded as excluded
  provenance where applicable and never become snippet text.
- Source video durations were not provided. Therefore trailing completeness and whether the last
  cue reaches the end of each video remain unavailable. Starts at 4 or 6 seconds can reflect a
  silent opening or omitted cues; the importer does not decide which.

## Timing policy

The source has starts but no cue ends or durations. The normalized schema still needs a duration
to build windows, so the importer keeps `source_duration_seconds: null` and separately marks each
`duration_seconds` as derived:

1. A nonterminal cue spans to the next *distinct* source start.
2. Duplicate-start cues all span to that same next distinct start, preserving overlap.
3. The terminal cue uses the video's median positive consecutive-start delta.

These values are analysis spans, not fabricated source facts. They can cover silence, they can be
shorter or longer than spoken text, and they affect detector windows, predicted interval ends, and
future boundary-error measurements. The original source start and text remain available for a
different timing policy later.

## Reproduce

```bash
.venv/bin/python scripts/import_manual_transcripts.py \
  "/Users/anuvikdas/Downloads/SponsorSkip Manual 14 Transcript Collection.docx"

.venv/bin/python scripts/evaluate_detector.py \
  --source-dir data/transcripts/tune \
  --detector-commit 0d065eccc10952ac3f1c2a416a0b7e4929e39026 \
  --output data/evaluation/tune-baseline-0d065ec.json
```

The first command is deterministic for the same DOCX, validation CSVs, acquisition corpus, and
importer version. The generated report is the machine-readable source of the counts above.
