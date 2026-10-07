# Playback-control milestone

Playback control is independent of transcript acquisition and promotion detection. The extension accepts time intervals and controls the YouTube `<video>` element; it does not decide whether an interval is promotional.

## Controller responsibilities

`extension/playback-controller.js` owns one video's playback state:

- `attachVideo(video)` subscribes to `timeupdate`, `playing`, `seeking`, and `seeked`, and detaches from a replaced YouTube video element.
- `beginVideo(videoId, requestId)` clears intervals, Undo, seek markers, and suppression whenever navigation establishes a new identity.
- `setIntervals(...)` rejects stale identities, validates and sorts intervals, merges overlaps or exact adjacency, and evaluates late-arriving intervals immediately.
- `evaluatePlayback(reason)` skips only when the current time is inside an eligible interval. It never seeks backward.
- `handleSeeking()` and `handleSeeked()` distinguish controller seeks from explicit user seeks.
- `undoLastSkip()` returns to the exact time captured immediately before the skip and suppresses that interval until playback leaves it.

## State transitions

Normal playback entering an interval changes `eligible → internally seeking → outside interval`. The controller captures the current time before assigning `video.currentTime = interval.endSeconds`.

If intervals arrive while playback is already inside one, the same transition skips only the remaining portion. If playback is at or beyond the end, no action occurs. Paused videos remain paused after the position changes.

Before setting `currentTime`, the controller stores an internal-seek target. A matching `seeking`/`seeked` pair is therefore controller-owned. A nonmatching seek is user-owned. If the user lands inside an interval, that effective interval becomes suppressed and is allowed to play. The last explicit landing time is retained across delayed interval arrival: a new interval is suppressed only when both the user's landing point and the current playback position are still inside it.

Undo marks the skipped interval suppressed before restoring the captured pre-skip position. This ordering prevents an immediate skip loop. Suppression is removed when playback leaves the interval, whether through normal playback or another seek. Replaying from before the interval can then skip it again.

Intervals and Undo records carry both `videoId` and `requestId`. Navigation generates a new request ID and clears state. Late fixture or future detector results with either old identity are rejected.

## Development fixtures

`extension/development-fixtures.js` contains only fully reviewed `tune` rows from the normalized manual annotations. Held-out and partial-review rows are excluded. Fixtures are disabled by default, delayed by 1.5 seconds to exercise asynchronous arrival, and labeled `manual-tune-fixture` in notifications. They are not model output.

The future detector can send the same content-script message shape:

```json
{
  "type": "promotion-intervals",
  "videoId": "...",
  "requestId": "...",
  "source": "detector",
  "intervals": [{ "startSeconds": 10, "endSeconds": 20 }]
}
```

## Automated coverage

Run:

```bash
node --test extension/tests/playback-controller.test.js
```

The tests cover normal and paused playback, late arrival without rewinding, a user seek that precedes delayed interval arrival, seeks before/inside/after intervals, Undo, replay eligibility, adjacent intervals, tune-only fixture scope, and stale results after rapid navigation.

## Verification record

On 2026-10-07, the user reported that the manual Chrome playback-fixture checks appeared to work. This is user-reported browser verification, not an automated Chrome result. The automated controller suite remains the reproducible evidence for individual state transitions.
