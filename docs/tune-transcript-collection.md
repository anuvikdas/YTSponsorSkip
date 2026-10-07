# Tune transcript collection checklist

Status update, 2026-10-07: the user supplied all 14 sections in a DOCX. They are now normalized in
`data/transcripts/tune/`; validation and timing caveats are in
`docs/manual-transcript-import-report.md`. This page remains the collection/format contract and is
not evidence that an automatic provider works.

The authoritative machine-readable checklist is
`data/validation/missing-tune-transcripts.csv`. It contains all 14 fully reviewed tune videos:

```text
094y1Z2wpJg  bHIhgxav9LY  iWeu2dxHRDg  DTvS9lvRxZ8
I9hJ_Rux9y0  lXfEK8G8CUI  -lErGZZgUbY  MRtg6A1f2Ko
9lx11dy9J30  Sew4rctKghY  O7sQBfpQCvU  U3aXWizDbQ4
x7X9w_GIm1s  aircAruvnKk
```

The two partial tune reviews and every held-out video are intentionally absent. Do not use sponsor
segment annotations to construct or trim transcripts.

## Required file format

Save one UTF-8 JSON file per video at `data/transcripts/tune/<video_id>.json`:

```json
{
  "schema_version": 1,
  "status": "ready",
  "video_id": "aircAruvnKk",
  "acquired_at": "2026-10-07T16:00:00Z",
  "environment": {
    "kind": "manual-browser-collection",
    "browser_context": true
  },
  "source": {
    "library": "source-or-export-tool-name",
    "version": "exact-version-or-unknown",
    "credentials_used": false,
    "cookies_used": false,
    "transcript_panel_opened": true
  },
  "transcript": {
    "language": "English",
    "language_code": "en",
    "caption_type": "manual",
    "is_generated": false,
    "provider": "source-or-export-tool-name",
    "provider_version": "exact-version-or-unknown"
  },
  "timing": {
    "source_unit": "seconds",
    "normalized_unit": "seconds",
    "duration_available": true
  },
  "snippets": [
    {
      "index": 0,
      "text": "Exact source snippet text",
      "start_seconds": 0.0,
      "duration_seconds": 2.3
    }
  ]
}
```

Use `caption_type: "unknown"` and `is_generated: null` unless the source exposes reliable track
metadata. Preserve source text, order, repeated lines, and overlaps. Convert milliseconds to
seconds but do not round away useful precision. Never derive a snippet duration from a sponsor
label. If the source supplies start and end, duration may be computed as `end - start` and that
conversion must be documented. If no end or duration exists, preserve that absence in a
source-specific field and explicitly mark any detector-compatible analysis span as derived. The
current manual importer uses the next distinct source start and a terminal median-delta fallback;
this is a documented approximation, not a source duration or promotion boundary.

SRT/VTT conversion must remove only container syntax, preserve cue text and order, convert cue
start/end into seconds, and record the original format in `source`. A transcript is complete only
after comparing first/last cue timestamps with the source track/video and checking for continuations
or pagination; a nonempty response alone does not establish completeness.

Evaluate both modes without any network requests:

```bash
.venv/bin/python scripts/evaluate_detector.py \
  --source-dir data/transcripts/tune \
  --detector-commit 0d065eccc10952ac3f1c2a416a0b7e4929e39026 \
  --output data/evaluation/tune-baseline-0d065ec.json
```

The evaluator uses manual intervals only as expected outputs when calculating metrics; it never
passes them to the detector.
