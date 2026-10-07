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

## 2026-10-07 — Playback verification and detector baseline

- Record the manual Chrome fixture check as user-reported verification, separately from automated tests.
- Keep detector predictions disconnected from automatic playback until tune evidence is available and reviewed.
- Start with a deterministic, replaceable English rules classifier and no paid inference.
- Do not evaluate held-out annotations until rules and policy thresholds are frozen.
- Stop the bounded Render acquisition probe after `REQUEST_BLOCKED`; do not run the full corpus while blocking persists.

## 2026-10-07 — Tune iteration and browser acquisition probe

- Preserve the `0d065ec` baseline and iterate only on the 14 fully reviewed tune videos; keep all
  partial and held-out labels outside tuning.
- Keep Conservative as the default after the tune iteration: it trades 35 more missed seconds than
  Aggressive for 82 fewer incorrect predicted seconds, while neither mode affects the 4 negatives.
- Treat the iteration as tune feedback, not generalization evidence; do not freeze it or connect it
  to playback.
- Keep any future model-assisted detector behind a transcript-level `ContextClassifier` contract;
  a network/batched full-context call should not be hidden inside the synchronous per-window
  classifier.
- Prefer a local semantic classifier as the next $0 comparison. Discuss hosted-model privacy,
  latency, and costs before adding a provider dependency or key.
- Implement the browser-context acquisition probe as disabled-by-default development code with a
  strict page-to-extension boundary. Unit tests do not count as Chrome acquisition evidence.
