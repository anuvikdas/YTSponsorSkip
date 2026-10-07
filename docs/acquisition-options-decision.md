# Automatic transcript acquisition: evidence and next experiment

Reviewed 2026-10-07. Prices and vendor interfaces are time-sensitive. This document distinguishes
project observations from vendor documentation and untested hypotheses. No paid service was
started and no acquisition architecture was replaced.

## Actual evidence so far

| Path | Environment and evidence | Result |
| --- | --- | --- |
| `youtube-transcript-api` 1.2.4 | Local/server-side | Six manual transcripts succeeded in an early 11-video smoke run. A later formal Docker run returned `IP_BLOCKED` for all 42 eligible attempts. |
| Same Python provider | Render Free/server-side | One manual transcript succeeded and was demonstrably cached; the next distinct generated-caption request returned `REQUEST_BLOCKED`, so the bounded experiment stopped. Cold start was not measured. |
| YouTube.js 18.1.0 | Local/server-side Node | Both bounded videos failed at `get_transcript` with HTTP 400. No blocking signal and no transcript. |
| `youtube-transcript` 1.3.1 | Local/server-side Node | Both bounded videos returned the package's `Transcript is disabled`; instrumentation showed upstream responses missing the expected track metadata for one video. No transcript. |
| Browser-side acquisition | Not tested | Unknown. Server-side Node failures neither prove nor disprove browser-context access. |
| Transcript-panel extraction | Not tested | Unknown automatically; manual copying produced this milestone's 14 transcripts. |
| Managed APIs / speech recognition | Not tested | Documentation and prices only, not reliability evidence. |

The Python provider exposes text, start, duration, language, and generated/manual metadata, but its
own documentation warns that it uses undocumented YouTube behavior and that cloud IPs are often
blocked. A proxy also does not guarantee success. See the official
[`youtube-transcript-api` documentation](https://github.com/jdepoix/youtube-transcript-api#working-around-ip-bans-requestblocked-or-ipblocked-exception).

The Node probes and exact latencies are preserved in `docs/node-acquisition-experiment.md`. Their
failure is why Node.js should not be added to the backend or Render image now.

## Decision criteria

Use a 0–5 score only after a candidate has been tested. Proposed weights:

| Criterion | Weight | Why |
| --- | ---: | --- |
| Reliable complete timestamped coverage | 40% | Without it the detector cannot run; a nominally fast or free failure has no product value. |
| Result ready before upcoming promotions | 20% | Playback starts immediately, so late results miss early and near-term segments. |
| Development and pilot cost | 15% | The initial target is $0, but a low bounded cost can be compared honestly if free acquisition fails. |
| Implementation and maintenance | 10% | Undocumented parsers and page structures impose recurring repair work. |
| User friction | 10% | Opening panels, clicking, signing in, or repeated prompts undermines automatic skipping. |
| Privacy, permissions, architecture fit | 5% | Keys must stay server-side and requested browser access should remain narrow. |

Reliability receives the largest weight, followed by latency and cost as requested. A weighted
total is intentionally **not** calculated yet for any untested candidate: replacing an unknown
reliability score with a guess would make the ranking look more precise than the evidence.

## Compact option matrix

`Observed` means this project measured it; `documented` is a supplier/library claim; `unknown`
means the proposed experiment has not run.

| Option | Coverage/failure evidence | Timestamp and latency evidence | Cost under assumptions below | Effort, permissions, privacy | Architecture fit |
| --- | --- | --- | --- | --- | --- |
| Python provider | Observed intermittent success, then local `IP_BLOCKED` and Render `REQUEST_BLOCKED`; missing/unavailable cases are typed | Observed original start/duration and generated/manual metadata; earlier successes ~0.83–1.24 s provider time | $0 library/Render Free; paid hosting would not change egress blocking by itself | Existing maintenance; no user credentials; undocumented upstream | Already behind `TranscriptProvider`; not a reliable live path in the tested environments |
| YouTube.js / `youtube-transcript`, server-side | Observed 0/2 for each; parser/request-path failures, not explicit IP blocking | Documented timing fields, but no successful project payload or latency-to-ready evidence | $0 software; adds Node runtime and deployment surface | High additional maintenance; no credentials in probe | Poor current evidence; keep as isolated development probes |
| Watch-page caption metadata/internal request | **Unknown** browser reliability; may use track data already available to the user's watch page | Expected source cue timing, but completeness and navigation-to-ready latency are unmeasured | $0 | Medium/high maintenance against undocumented page data; no cookie export; a narrow YouTube page-world bridge is needed | Best next experiment; can normalize to the current contract and bypass cloud egress |
| Transcript panel, automatic | **Unknown**; DOM/UI changes and panel load races are likely failure modes | Starts are visible, ends usually absent in copied text; readiness unmeasured | $0 | High UI brittleness; clicking/opening visible UI can disrupt the viewer | Reject as primary if visible interaction is required |
| Transcript panel, user-assisted | Manual collection succeeded 14/14 by user report; not automatic product evidence | This collection has starts only and user-reported completeness | $0 money, high user time | Highest friction; no account data leaves the browser | Useful dataset fallback, unsuitable for automatic skipping |
| Scrape Creators managed API | **Unknown** on our corpus; documents public-caption retrieval and null/no-charge for no matching captions | Documents `startMs`/`endMs`; vendor cache metadata is explicit; project latency unknown | 100 free credits, then $47 one-time/25k | API key must remain in FastAPI env; third party receives video URL/ID | Clean fallback adapter; do not test until user approves free account setup |
| Supadata managed API | **Unknown** on our corpus; documents existing transcript retrieval and optional ASR generation | Documents millisecond `offset`/`duration`; project latency unknown | 100 credits/month; native-caption pilot could fit $17/month; ASR can be much more | Server-held API key and third-party video disclosure | Clean adapter; ASR is a separate latency/cost product decision |
| SearchAPI managed API | **Unknown** on our corpus | Documents start/duration and manual/auto selection; example timing is not our evidence | 100 free, then $40/month minimum | Server-held key; 20% of plan credits/hour; third-party disclosure | Clean adapter but weakest small-pilot price |
| Self-hosted speech recognition | **Unknown**; also requires a lawful/reliable audio source that we do not have | Can generate segment/word timings, but audio download and processing latency are unresolved | Model is open source; free-host compute suitability and operational cost are unknown | Largest compute/deployment change; audio handling increases privacy and resource scope | Later fallback only, not a caption-acquisition replacement now |

Relevant primary documentation:

- [YouTube.js](https://github.com/LuanRT/YouTube.js) and
  [`youtube-transcript`](https://github.com/Kakulukian/youtube-transcript) both rely on unofficial
  interfaces; the latter explicitly warns it can break.
- Chrome says normal content scripts run in an isolated world while sharing the DOM; `MAIN`-world
  scripts share the page's JavaScript environment and can be interfered with by the host page.
  Cross-origin requests from content scripts remain same-origin restricted, while an extension
  service worker can use declared host permissions. See
  [content scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts),
  [manifest worlds](https://developer.chrome.com/docs/extensions/reference/manifest/content-scripts),
  and [network requests](https://developer.chrome.com/docs/extensions/develop/concepts/network-requests).
- Scrape Creators documents [one credit per transcript, `startMs`/`endMs`, language selection, and
  zero-credit cache hits](https://docs.scrapecreators.com/v1/youtube/video/transcript/) plus
  [100 free credits and $47/25,000 nonexpiring credits](https://scrapecreators.com/).
- Supadata documents [100 free monthly credits, $17/3,000 and $47/30,000 monthly plans, opt-in
  auto-recharge, and hard stopping without it](https://supadata.ai/pricing), as well as
  [millisecond offset/duration fields](https://supadata.ai/video-transcript-api).
- SearchAPI documents [start/duration fields and manual/auto track selection](https://www.searchapi.org/docs/youtube-transcripts)
  and [100 free requests followed by a $40/month 10,000-request plan](https://www.searchapi.io/pricing).
- Open-source [Whisper](https://github.com/openai/whisper) can transcribe audio and emit timestamped
  outputs, but requires the audio plus model/FFmpeg compute. That capability does not solve our
  unresolved audio-access or pre-segment latency requirements.

## Explicit cost assumptions

- Development: 100 distinct, uncached video transcripts per month.
- Small pilot: 20 users × 5 new video loads/day × 30 days = 3,000 loads/month.
- Assume 40% of pilot loads repeat a video already in the application cache: 1,800 upstream
  requests/month. This reuse estimate is an assumption, not measured behavior.
- Caption retrieval is one provider request/credit unless the provider says otherwise. Taxes are
  excluded. Prices above were reviewed on 2026-10-07 and must be rechecked before purchase.

| Service | Development | 1,800-upstream-request pilot | Overage control |
| --- | ---: | ---: | --- |
| Existing/browser/self-hosted caption paths | $0 acquisition | $0 acquisition | Our rate limit/circuit breaker; reliability remains unresolved |
| Scrape Creators public captions | $0 within 100 credits | $47 upfront for 25,000 nonexpiring credits; about 13.9 months at this assumed load, or ~$3.38/month amortized | Prepaid balance; documented provider cache hits cost 0 |
| Supadata native captions | $0 within 100 credits | $17/month for 3,000 credits | Auto-recharge is optional; without it requests stop at the limit |
| SearchAPI | $0 within 100 requests | $40/month minimum for 10,000 | Failed requests not charged; hourly use limited to 20% of plan credits |

Supadata's optional generated transcript costs two credits per source minute, not one credit per
video. At an explicit 12-minute average, 100 ASR videos would consume 2,400 credits (about
$17/month), while 1,800 would consume 43,200 credits (about $77 for a $47/30,000 plan plus three
$10/5,000 recharges). That is a different, paid fallback and is not proposed now.

## What resilience mechanisms do—and do not—do

- **Success cache:** avoids repeated upstream work/cost for the same video, lowers latency, and lets
  later viewers reuse a prior result. It cannot help the first request for an unseen video or fix a
  stale/bad transcript without versioning and expiry.
- **In-flight coalescing:** makes simultaneous requests for the same key share one provider call.
  It cannot turn a blocked or unsupported provider response into a transcript.
- **Bounded retries:** can recover from a small number of timeouts, connection resets, or retryable
  5xx responses. Do not retry invalid IDs, unavailable/no-caption results, parser failures, or clear
  IP/request blocking; retries would add latency and load without new evidence.
- **Circuit breaker:** stops calls after a threshold of systematic upstream/blocking failures and
  fails fast while cooling down. It protects the upstream and user experience, but deliberately
  makes acquisition unavailable until a probe succeeds; it is not a bypass.

All four fit around the existing `TranscriptProvider` boundary. They cannot manufacture captions,
repair an upstream schema change, make a private/unavailable video public, or guarantee a result
before an early promotion.

## Recommended experiment—discussion checkpoint

### Primary: browser watch-page caption metadata

Test browser-context acquisition before introducing a service account or recurring cost. This is a
hypothesis, not a conclusion: the user's browser may receive caption-track metadata that blocked
server egress does not, but the experiment must show that it can be accessed consistently and
early without opening the transcript panel.

Smallest architectural change:

1. Add a development-only `BrowserTranscriptProvider` in the extension. Do not replace the Python
   provider or enable predictions.
2. Add a narrow declared `MAIN`-world script on `youtube.com` that reads only the current video's
   caption-track metadata/player updates and performs only a fixed YouTube timed-text request. Do
   not export cookies, credentials, or arbitrary page data.
3. Send a schema-validated result—video ID, navigation token, language/type metadata, original cue
   text and timing—back to the existing isolated content script. Reject mismatched video/token
   responses exactly as the current backend path rejects stale navigation results.
4. Normalize into the existing transcript contract so the detector, cache key, status UI, and
   offline evaluator remain reusable. Keep the FastAPI provider available as a separately selected
   path during the experiment.

Prefer a declared `MAIN`-world content script over adding broad cross-origin permissions. The host
page can observe or interfere with MAIN-world code, so the isolated receiver must validate every
field, accept only the active video ID/token, cap payload size, and never accept an arbitrary URL
to fetch.

### Prespecified test

Use eight public videos: three confirmed manual English, three confirmed generated English, one
confirmed no-English/no-caption case, and one unavailable case. Run the same set in two fresh
Chrome sessions at different times, with the experiment cache cleared between sessions. Do not use
held-out sponsor labels; caption status is acquisition metadata, not detector tuning.

Success criteria, fixed before implementation:

- **Coverage:** at least 11/12 eligible attempts overall and at least 5/6 for each of manual and
  generated captions. Both negatives must return the correct typed unavailability rather than an
  empty “success.” A systematic blocking signal stops the session.
- **Timing/completeness:** every successful cue has preserved text plus finite, nonnegative source
  start and end/duration; ordering and overlaps are retained; no unexplained pagination/truncation;
  source cue count and last cue are recorded. Caption type remains unknown if the page does not
  expose it.
- **Latency:** measure navigation-to-ready, metadata discovery, and timed-text fetch separately.
  Warm-session median must be at most 2 seconds and p95 at most 5 seconds; at least 90% of eligible
  results must be ready before 15 seconds of ordinary playback.
- **Repeatability:** meet coverage criteria in both fresh sessions without a previously opened
  panel or exported session material.
- **Navigation safety:** ten rapid A→B transitions with zero stale A results accepted on B. Playback
  must continue normally on every failure.
- **User interaction/privacy:** no visible transcript panel, login request, cookie export, account
  credential, or broad arbitrary-host fetch. If opening the panel is required, reject this as the
  automatic primary path and classify it as user-assisted.

### At most one fallback: Scrape Creators free-tier probe

If the browser experiment fails its gate, discuss a 12-request Scrape Creators free-tier test on
the same eight-video mix before any integration or purchase. The adapter would live behind the
FastAPI `TranscriptProvider`; its API key would exist only in server environment configuration,
never extension storage. Preserve the current cache/coalescing/rate-limit/error contract. Apply
the same coverage, timestamp, typed-negative, latency, and two-session/repeat criteria. Vendor
claims are not evidence until this project measures them.

No account should be created and no key requested during this milestone. The next decision is
whether to approve implementation of the $0 browser experiment. Only if it fails should the free
managed-API probe be discussed.
