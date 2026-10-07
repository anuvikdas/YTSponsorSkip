# Development-only browser transcript probe

The probe is implemented but disabled by default. Automated contract tests pass; no actual Chrome
acquisition result has been observed in this milestone, so browser reliability remains unverified.
It does not run the detector or send intervals to playback.

## Architecture and safety boundary

`browser-transcript-page.js` is a declared `MAIN`-world script on YouTube watch pages. It remains
idle until the isolated content script dispatches a fixed event containing only the active 11-character
video ID and navigation request ID. It then:

1. reads the matching current player response;
2. waits up to five seconds for caption tracks;
3. chooses English, preferring manual over generated captions;
4. accepts only an HTTPS `https://www.youtube.com/api/timedtext` URL already supplied by the active
   page, forces `fmt=json3`, and makes the same-origin request in the current browser session; and
5. posts only language/type, split latency, and original cue text/start/duration back to the page.

It does not open or click the transcript panel, export cookies, read account credentials, accept a
URL from the content script, or request another host. The existing `youtube.com` content-script
scope is unchanged; no new host permission was added.

`browser-transcript-provider.js` is the isolated-world trust boundary. `validateEnvelope` checks an
exact key allowlist, channel, active video/request identity, typed failure allowlist, finite ordered
timings, sequential indexes, string/payload limits, and split latency consistency. It normalizes a
success into the existing acquisition response contract with provider `youtube-watch-page` and
version `dev-probe-1`. Original order and overlaps are retained.

`content.js.beginAcquisition` selects the probe only when the development flag is true. Navigation
clears the timer and changes both identities; late page messages are rejected. `service-worker.js`
checks the flag again, applies a ten-second timeout, repeats identity/shape checks, stores a success
in `chrome.storage.session` only for inspection, and publishes status. It never emits detector
predictions. A failed probe reports unavailability while YouTube playback continues.

MAIN-world code can be observed or interfered with by YouTube. Strict validation limits what crosses
into extension state, but cannot make an undocumented player/timed-text interface stable.

## Automated checks actually run

- valid page data becomes the current transcript contract;
- source overlaps and timing metrics are preserved;
- stale video/request identities fail;
- arbitrary URL/extra-field injection fails;
- invalid timing/order and non-allowlisted errors fail;
- 16 browser-provider plus playback-controller Node tests pass; and
- JavaScript syntax checks pass for the page bridge, validator, content script, worker, popup, and
  options script.

These are contract tests, not Chrome or YouTube acquisition tests.

## Exact Chrome protocol (still to run)

No backend is required while the probe flag is enabled.

1. Open `chrome://extensions`, enable Developer mode, and load/reload the repository's `extension/`
   directory.
2. Open the extension's **Details → Extension options**. Leave **Enable YTSponsorSkip** on. Under
   **Development**, turn **Use manual playback fixtures** off and **Probe captions from watch page**
   on; save.
3. Open the extension service-worker inspector from `chrome://extensions`. Clear only the
   extension's ephemeral experiment state with `chrome.storage.session.clear()`. Do not clear,
   export, or inspect browser cookies.
4. In a normal signed-in or signed-out YouTube session (whichever you ordinarily use), navigate
   directly to each video below. Do not open the transcript panel. Start a stopwatch at navigation;
   when the extension popup changes, record status, caption type, count, popup request-to-ready,
   metadata, and timed-text milliseconds.
5. For source evidence, run `chrome.storage.session.get().then(console.log)` in the extension
   worker inspector. The `transcript-<tabId>` object should contain the full normalized payload;
   the `tab-<tabId>` object contains the concise status. A success must have nonempty ordered cues,
   finite nonnegative timings, and a plausible last cue near the video end. Record unexplained
   truncation rather than calling it complete.
6. Close all Chrome windows and repeat the eight-video run in a second fresh session at a different
   time, clearing extension session storage first. Caption availability/type can change; report a
   change rather than rewriting the prespecified expectation.
7. For navigation safety, in one tab navigate A→B rapidly ten times before A finishes. After each
   transition, only B's video/request may appear in `tab-<tabId>` and `transcript-<tabId>`.
8. Turn the probe off after the experiment. It is not a production provider.

Prespecified corpus:

| Expected case | Video IDs |
| --- | --- |
| Confirmed manual English when curated | `dQw4w9WgXcQ`, `aircAruvnKk`, `rfscVS0vtbw` |
| Confirmed generated English when curated | `Vw1Qrko8oTs`, `FfwvYyQDRhc`, `SqHwCfc9uv4` |
| No eligible caption expected | `Z_jl71GApQQ` |
| Unavailable expected | `zI_e7jEW4Xc` |

Expected successful UI: “Transcript ready. Detection is not connected yet,” followed by cue count,
manual/generated type, and the three timing values. Expected negative UI: “Skipping unavailable…
Playback is unaffected,” with a typed reason such as `NO_CAPTION_TRACK` or
`PAGE_DATA_UNAVAILABLE`. A different observed error must be recorded exactly.

## Existing gate

- At least 11/12 eligible attempts over two sessions, at least 5/6 manual and 5/6 generated.
- Both negatives typed correctly; a systematic blocking signal stops that environment.
- No unexplained truncation; text/timing/order/overlaps preserved.
- Warm-session median at most 2 seconds, p95 at most 5 seconds, and at least 90% ready before 15
  seconds of playback.
- Both fresh sessions pass without a previously opened panel or exported session material.
- Ten rapid A→B transitions accept zero stale A results on B.
- No panel interaction, login request, cookie export, credential handling, or arbitrary-host fetch.

If this fails, record the failing layer: player data absent, no matching track, timed-text HTTP,
JSON3 parse, timeout, truncation, latency, or stale navigation. Do not rotate libraries or retry a
systematic block. The single bounded fallback remains a 12-request free-tier managed-provider trial
described in `docs/acquisition-options-decision.md`, subject to discussion before account creation.
