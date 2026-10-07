# Transcript-acquisition study

Run date: 2026-10-06. Provider: `youtube-transcript-api` 1.2.4. This study measures caption acquisition, not promotion detection.

## Corpus and method

`data/acquisition_corpus.csv` contains 26 videos from different channels and durations:

- 21 videos whose English caption tracks were confirmed during corpus curation: 9 manual and 12 automatically generated.
- 5 explicit negative cases: captions disabled, no matching English transcript, an unavailable video, a deliberately unavailable ID, and a syntactically invalid ID.

The Docker run used two ordered passes with 1.1 seconds between requests. The first successful request for a video would be uncached and the second would be an in-memory cache hit. Failed acquisitions are not cached. The JSON runner now preserves every successful response's original snippet text, start, and duration. Raw result JSON stays under ignored `results/` because caption text can be large and is experiment output rather than source code.

## Current local Docker run

The container image built and the API health endpoint returned 200. Before the formal run, a live request returned `IP_BLOCKED`; the formal corpus then produced the same environmental block for every otherwise eligible video.

| Measure | Result |
| --- | --- |
| Eligible-caption attempts | 42 (21 videos × 2 passes) |
| Eligible-caption successes | 0 |
| Manual | 0/18; all 18 unexpectedly `IP_BLOCKED` |
| Generated | 0/24; all 24 unexpectedly `IP_BLOCKED` |
| Expected-negative attempts | 10 |
| Expected failures observed | 10/10 |
| Unexpected failures | 42, all `IP_BLOCKED` |
| Failed request latency | median 1,173.43 ms; p90 1,351.34 ms; max 1,692.13 ms |
| Successful cached/uncached latency | unavailable in this blocked run |
| Timing granularity/overlap | unavailable in this blocked run |

The 0% eligible-caption result describes this run from this IP after it was blocked. It must not be generalized as library reliability or reinterpreted as missing captions.

## Earlier local baseline, before the IP block

The earlier 11-video smoke run returned six successful manual transcripts and five expected acquisition failures. Its 54.5% all-corpus success rate mixed positive and intentionally negative cases, so it is not a reliability estimate among eligible captioned videos.

For its six successes:

- End-to-end latency: median 1,050.79 ms, range 833.88–1,240.66 ms.
- Provider latency: median 1,043.56 ms, range 830.80–1,226.18 ms.
- Median start gap per transcript: median 2.795 seconds, range 2.302–5.000 seconds.
- Median snippet duration per transcript: median 2.718 seconds, range 2.080–5.000 seconds.
- Four of six transcripts contained overlapping snippets; the largest had 126 overlapping adjacent pairs.
- 3,944 original snippets were returned across the six transcripts.

These overlaps and multi-second gaps demonstrate why `start + duration` is caption display timing, not an exact promotion boundary.

## Cache interpretation

The service test suite verifies that the second identical successful request is served from cache and that its provider latency is `null`, rather than incorrectly repeating the first upstream duration. The blocked live run has no successful responses to cache, so it cannot supply an honest live cached-versus-uncached comparison. That comparison remains required on an environment that can acquire at least one transcript.

## Render comparison still required

Run the same corpus unmodified on Render Free. Record the very first end-to-end request separately, then compare warm uncached end-to-end latency with provider latency. A slow first request with later successful acquisition is cold start; `IP_BLOCKED` or `REQUEST_BLOCKED` from a warm service is acquisition blocking. Paying for a larger instance would not by itself change the egress-IP result.
