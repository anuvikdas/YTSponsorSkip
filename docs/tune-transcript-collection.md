# Tune transcript collection checklist

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
conversion must be documented. If no end or duration exists, preserve the raw acquisition outside
the detector input and record the limitation; the current detector requires finite, nonnegative
`duration_seconds` and must not receive a fabricated value.

SRT/VTT conversion must remove only container syntax, preserve cue text and order, convert cue
start/end into seconds, and record the original format in `source`. A transcript is complete only
after comparing first/last cue timestamps with the source track/video and checking for continuations
or pagination; a nonempty response alone does not establish completeness.

Once files exist, evaluate both modes without any network requests:

```bash
.venv/bin/python scripts/evaluate_detector.py \
  --source data/transcripts/tune/094y1Z2wpJg.json \
  --source data/transcripts/tune/bHIhgxav9LY.json \
  --output /tmp/ytsponsorskip-detector-tune.json
```

Repeat `--source` for every collected file. The evaluator uses manual intervals only as expected
outputs when calculating metrics; it never passes them to the detector.
