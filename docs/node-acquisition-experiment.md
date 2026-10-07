# Alternative Node transcript-acquisition experiment

Run date: 2026-10-07. Environment: local, server-side Node.js `v25.2.0` on macOS.
Cost: $0. Browser cookies, account credentials, and transcript-panel interaction: none.

This experiment tested isolated adapters. It did not replace the Python `TranscriptProvider`,
change the Render service, or send detector labels to an acquisition tool.

## Libraries and support model

| Library | Locked version | Runtime | Transcript interface | Timing exposed by the installed version |
| --- | --- | --- | --- | --- |
| YouTube.js (`youtubei.js`) | 18.1.0 | Node.js, Deno, or a modern browser; this lock tree requires Node >=20 through `meriyah` | `MediaInfo.getTranscript()` | transcript segments expose `start_ms` and `end_ms` |
| `youtube-transcript` | 1.3.1 | Node.js >=18 | `fetchTranscript(videoId, options)` | `{ text, offset, duration, lang }`; units depend on the timed-text XML form |

Both packages use unofficial YouTube interfaces. Registry metadata inspected on 2026-10-07 shows
YouTube.js 18.1.0 published on 2026-09-22 and `youtube-transcript` 1.3.1 on 2026-04-25. YouTube.js
has an actively maintained, larger codebase, but its issue tracker includes current
transcript-endpoint failures. `youtube-transcript` has no runtime dependencies, but its own README
warns that the unofficial API can break, and open issues describe false transcript-disabled and
production failures. Publication recency is not evidence of transcript reliability.

The probe scripts and lock file live in `tools/transcript-acquisition-node/`. The
`youtube-transcript` adapter inspects raw XML before interpreting timing units: `srv3` `<p t d>`
attributes are milliseconds, whereas classic `<text start dur>` values are seconds.

## Bounded local results

`aircAruvnKk` was chosen because the earlier acquisition corpus identifies it as confirmed manual
English. That caption type is prior project evidence, not something either Node probe reconfirmed.
`U3aXWizDbQ4` is a fully reviewed tune negative. Its normalized caption type is unknown; it was
not relabeled as generated merely to satisfy the preferred test pairing.

| Video | Library | Result | Latency | Caption data | Completeness evidence |
| --- | --- | --- | ---: | --- | --- |
| `aircAruvnKk` | YouTube.js 18.1.0 | HTTP 400 from `/youtubei/v1/get_transcript` | 1232.438 ms | unavailable | 0 snippets; truncation/pagination cannot be assessed |
| `U3aXWizDbQ4` | YouTube.js 18.1.0 | HTTP 400 from `/youtubei/v1/get_transcript` | 1094.907 ms | unavailable | 0 snippets; truncation/pagination cannot be assessed |
| `aircAruvnKk` | youtube-transcript 1.3.1 | package error: `Transcript is disabled` | 831.695 ms | unavailable | 0 snippets; truncation/pagination cannot be assessed |
| `U3aXWizDbQ4` | youtube-transcript 1.3.1 | package error: `Transcript is disabled` | 1290.604 ms | unavailable | 0 snippets; truncation/pagination cannot be assessed |

YouTube.js emitted parser warnings before both HTTP 400 responses. These failures are classified
as upstream compatibility/unsupported transcript behavior, not access blocking: there was no
HTTP 429, CAPTCHA challenge, `IP_BLOCKED`, or `REQUEST_BLOCKED` signal.

For `U3aXWizDbQ4`, the instrumented `youtube-transcript` run captured an Android player response
(HTTP 200, 4,949 bytes) and a watch page (HTTP 200, 1,283,972 bytes). Neither representation
contained `playerCaptionsTracklistRenderer`, so the package collapsed “no track metadata in these
responses” into “Transcript is disabled.” The watch HTML included generic reCAPTCHA configuration
and CSS, but no observed CAPTCHA challenge. This is unsupported/request-path behavior, not proof
that the video lacks captions. The first `aircAruvnKk` failure predates failure-body capture, so its
network-level details are not available and it was not retried.

All four results are server-side Node results. No browser-side package test was performed.

## Comparison with existing provider evidence

The Python `youtube-transcript-api` path previously acquired `aircAruvnKk`, establishing that a
manual English transcript was available at that time, although the old saved record omitted its
snippets. Later formal runs were IP/request blocked, including the bounded Render experiment.

The Node probes did not show that block, but they also did not acquire a transcript. Different
failure modes do not make either Node library a successful fallback. No further videos were sent
because neither method passed the two-video gate.

## Decision

- Tune transcript coverage remains **0/14** usable snippet-bearing files.
- The collection phase and real tune-set detector evaluation did not run.
- Adding Node.js to the backend or Render image is not justified by this evidence. The probes stay
  development-only and preserve the replaceable-provider boundary.
- Reliability across sessions is unknown because there was no successful session to repeat.
- Manual collection, or a later narrowly scoped browser-side experiment that does not export
  cookies or credentials, is the next decision point. The exact checklist and accepted file format
  are in `docs/tune-transcript-collection.md`.

## Primary references

- YouTube.js package and runtime summary: <https://www.npmjs.com/package/youtubei.js>
- YouTube.js repository and API documentation: <https://github.com/LuanRT/YouTube.js>
- `youtube-transcript` package: <https://www.npmjs.com/package/youtube-transcript>
- `youtube-transcript` source and warning: <https://github.com/Kakulukian/youtube-transcript>
- Current YouTube.js issues: <https://github.com/LuanRT/YouTube.js/issues>
- Current `youtube-transcript` issues: <https://github.com/Kakulukian/youtube-transcript/issues>
