# Isolated Node transcript-acquisition probes

These scripts test alternative open-source acquisition paths without replacing the Python
`TranscriptProvider`. They are development tools, not backend dependencies.

## Runtime and locked versions

- Node.js 20 or newer for the combined locked dependency tree (the recorded experiment used
  Node.js `v25.2.0`). `youtube-transcript` itself declares Node.js 18 or newer; YouTube.js 18.1.0
  has no direct Node engine declaration, but its locked `meriyah` dependency requires Node 20.
- `youtubei.js` `18.1.0`
- `youtube-transcript` `1.3.1`

Install exactly the lock-file versions and run the offline unit tests:

```bash
cd tools/transcript-acquisition-node
npm ci --ignore-scripts
npm test
```

Run one bounded request at a time:

```bash
npm run acquire:youtubejs -- \
  --video aircAruvnKk \
  --output /tmp/airc.youtubejs.normalized.json \
  --raw /tmp/airc.youtubejs.raw.json

npm run acquire:youtube-transcript -- \
  --video aircAruvnKk \
  --output /tmp/airc.youtube-transcript.normalized.json \
  --raw /tmp/airc.youtube-transcript.raw.json
```

The normalized success format is accepted by `scripts/evaluate_detector.py`. Both adapters
preserve source order, text, overlaps, and a stable zero-based snippet `index`. YouTube.js
`start_ms`/`end_ms` values are converted to seconds. `youtube-transcript` can parse either
millisecond `srv3` `<p t d>` XML or second-based classic `<text start dur>` XML; the adapter
inspects the captured response before converting because the package exposes both through the
same `offset` and `duration` property names.

`caption_type` is `manual`, `generated`, or `unknown`. Unknown remains unknown and is never
coerced to manual. `is_generated` is consequently `true`, `false`, or `null`.

Raw files may contain large upstream responses and are intentionally written only to the path
the caller supplies. Keep them out of Git. The scripts do not load cookies, credentials, or a
browser profile, and they do not open YouTube's transcript panel.
