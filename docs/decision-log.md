# Decision log

## 2026-10-06 — MVP platform and behavior

- Target an unpacked desktop Chrome Manifest V3 extension.
- Start playback immediately; never rewind for a segment that detection missed.
- Treat both third-party and creator-owned pitches as eligible only when separable from the video's main content.
- Default to Conservative behavior; Aggressive is opt-in.
- Continue playback normally whenever acquisition or detection is unavailable.

## 2026-10-06 — Transcript acquisition

- Evaluate `youtube-transcript-api` 1.2.4 first.
- Run acquisition in a Python 3.12 FastAPI backend.
- Hide the package behind a `TranscriptProvider` protocol and project-owned domain types.
- Preserve each snippet's text, start, and duration; do not treat caption display timing as exact promotion boundaries.
- Test the same corpus locally and on Render Free before treating the provider or host as reliable.
- Normalize provider exceptions into a stable public API contract.

## 2026-10-06 — Cost and infrastructure

- Initial target is $0/month.
- Package the settings UI inside the extension.
- Use a single process-local TTL/LRU cache, duplicate-request coalescing, bounded provider concurrency, and a request limit for the experiment.
- Do not add a database, managed cache, custom domain, paid proxy, or paid inference without measured need and prior discussion.
- Keep cloud cold-start latency distinct from YouTube IP blocking in experiment reports.
