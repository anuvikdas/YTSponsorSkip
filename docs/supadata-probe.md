# Supadata native-caption probe — October 19, 2026

The user reports `TIMED_TEXT_PARSE_ERROR` for both videos in the separate watch-page browser
experiment. That is an observation; the failing layer and root cause are unconfirmed. Browser
probe debugging is paused. No browser-probe source was changed for this test.

## Official contract checked

The [Supadata transcript API](https://docs.supadata.ai/get-transcript) accepts
`GET https://api.supadata.ai/v1/transcript` with an `x-api-key` header. The probe fixes
`mode=native`, `text=false`, and `lang=en`. Native mode retrieves existing captions and does not
invoke generated transcription. A preferred language can fall back to the first available one,
so the adapter checks the returned transcript and cue languages before accepting them. An immediate
200 includes `content` cues with `text`, `offset` and `duration` in **milliseconds**. A 202 includes
a job ID; the [job endpoint](https://docs.supadata.ai/api-reference/endpoint/transcript/transcript-get)
reports queued, active, completed or failed. The documented poll interval is one second; this
probe also limits total time and poll count. Polling a job is documented as uncharged.

The docs currently state **one credit per native transcript**, including a 206 unavailable
response. A 202 `x-billable-requests` header is a precharge estimate, and final usage is reconciled
later. The [account endpoint](https://docs.supadata.ai/api-reference/endpoint/account/me) exposes
plan, maximum credits and used credits. We read those counters before and after, when available;
a counter delta is an observation, not a billing guarantee. No purchase, subscription or recharge
action is part of this probe. The script checks for a clearly labeled Free/Trial plan and at least
two remaining credits before starting, then checks again before the second transcript request;
if this cannot be confirmed, it stops.

## Local key setup and exact probe command

The *repository root* is `/Users/anuvikdas/Downloads/YTSponsorSkip/YTSponsorSkip` (the inner
`YTSponsorSkip` directory). Open its `.env` in a local editor and save one line:

```dotenv
SUPADATA_API_KEY=<your actual key>
```

Do not type the key in a terminal command, paste it in chat, or put it in `.env.example`.
`.env` is Git-ignored and Docker-ignored; `.env.example` contains only a placeholder. The Python
settings loader reads the exact `SUPADATA_API_KEY` name from this file and keeps it as a masked
`SecretStr`. The HTTP adapter sends it only as the Supadata request header. It does not print or
log the value. Use file permissions of your choice; `chmod 600 .env` restricts local read access.

From that repository root, after the key is saved:

```bash
.venv/bin/python tools/supadata_probe.py
```

The script makes one native transcript request for each of `dQw4w9WgXcQ` and `Vw1Qrko8oTs`,
sequentially. It refuses to request them again if a per-video result file exists. It writes
`results/supadata/{video_id}.json` with sanitized raw responses and normalized cues, plus
`results/supadata/report.json`. This directory is ignored by Git; review it locally. Response
bodies are redacted for any literal copy of the key, and request/response header dumps are omitted
except the billable-request count. Console output contains IDs, statuses, counts, language,
latency and error codes only.

`200` is marked usable only when the body has nonempty English timed text with finite,
nonnegative, ordered millisecond offsets/durations. Original text and cue order are retained;
milliseconds are divided by 1000 for the existing `Transcript` domain. `is_generated` and
caption type remain unknown because native retrieval alone does not prove manual versus automatic
captions. The last cue end is derived from its offset and duration; it does not establish the end
of speech or the exact end of the video. Check the saved first/last cues against an independently
observed video duration before asserting completeness.

The probe's outer limit is 30 seconds, with at most 20 one-second polls; network calls have a
five-second maximum per request and use whatever shorter time remains. An unexpected status,
language, shape or timing is saved as an unavailable result and receives no automatic retry.

## Measured results

The first live local probe ran after the key was added to the repository-root `.env`. The script
made exactly one transcript request per video, sequentially, without retries. It did not invoke
generated transcription. Raw API bodies, billing-header observations, normalized cues and summaries
are preserved locally in the ignored files under `results/supadata/`.

| Video | HTTP outcome | Result | Cues | Returned language | Total latency | First cue | Last cue start / derived end |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: |
| `dQw4w9WgXcQ` | 200 | Usable native timed text | 61 | `en` | 2,400.382 ms | 1.36 s | 207.92 / 211.32 s |
| `Vw1Qrko8oTs` | No HTTP response before the 5-second per-request timeout | `ACQUISITION_TIMEOUT` | 0 | Unknown | 5,005.56 ms | N/A | N/A |

For the successful result, all 61 cues had nonempty text, finite nonnegative offsets/durations,
and nondecreasing starts. The first raw cue is 1,360 ms with 1,680 ms duration; the last is
207,920 ms with 3,400 ms duration. After division by 1,000, source text, cue order and overlaps
are preserved. Manual versus automatically generated caption type is **unknown** from this API
response. Supadata's `mode=native` means it retrieved existing captions, not that a person wrote
them. The cue durations still do not define exact speech or promotional boundaries.

For truncation evidence, the complete 61-cue normalized response matches both previously saved
`dQw4w9WgXcQ` Render JSON responses cue for cue, including the last cue at 207.92–211.32 s.
There is no discrepancy against that earlier source. This is a stronger check than HTTP 200 alone,
but without an independently verified video end it does not prove transcript completeness. The
second video's timed-out request yielded no response body, so language, timing and completeness
cannot be assessed; its previously curated generated-caption status is not a live Supadata result.

The account endpoint reported **Free (100/mo), 0/100 credits used** before the experiment and
**1/100 used** both immediately afterward and on a later read-only check. The observed delta is
one free credit, consistent with the documented native transcript charge. It is possible that a
server-side job continued after the timed-out second HTTP request; final billing beyond these
observations is not established. No purchase or paid plan was used. The total cash spend observed
for this probe is $0.

Because only one of the two videos produced usable timed captions, Supadata is **not yet selected
as the FastAPI provider**. The existing Python provider remains configured. This outcome does not
identify the cause of the second timeout or establish Supadata reliability across videos/sessions.
Per the prespecified stop rule, there was no retry, corpus expansion, detector change, or held-out
evaluation. The next smallest experiment is a separate, explicitly bounded decision about whether
to allow one longer-timeout repeat of `Vw1Qrko8oTs`; first confirm current credit usage and preserve
this result as attempt 1. If that repeat succeeds, local FastAPI integration can be tested with
the existing caching/coalescing service. It would still need cross-session reliability evidence
before live skipping.

## Authorized one-attempt follow-up

After the above checkpoint, the user authorized exactly one longer-timeout follow-up for
`Vw1Qrko8oTs`. The development-only `tools/supadata_followup.py` used the same native adapter
with a 30-second overall deadline and per-call ceiling, `mode=native`, `text=false`, `lang=en`,
at most five one-second job polls, no acquisition retry and no generated fallback. It checked the
Free-plan account counter before acquisition, reserved one persistent local budget attempt, and
refuses to rerun once the result file exists.

The follow-up returned **HTTP 200** with **345 usable English timed cues** in **1,811.148 ms**
end to end and **zero polls**. All cues passed the nonempty text and finite/nonnegative ordered
timing checks. The first cue starts at **0.199 s**; the final cue starts at **1001.319 s** and
its source duration gives a derived end at **1004.16 s**. Caption authorship remains unknown.
The saved raw/normalized response is the ignored local file
`results/supadata/Vw1Qrko8oTs-followup.json`. No independent video-duration or alternate
full-transcript comparison has established completeness, so this is usable acquisition evidence,
not proof against truncation. The first timeout's cause remains unconfirmed; it was not evidence
of missing captions or IP blocking.

The account reported Free 100/month with **1 used before** and **2 used after** this follow-up.
That observed increase is one free credit; delayed billing from the earlier timed-out request
cannot be ruled out. Cash spent in this experiment: **$0 observed**. The persistent local ledger
is now **3/50 attempts**: the two seeded prior attempts plus this one. See
`docs/supadata-trial-budget.md` for what that ledger does and does not protect.

With both target videos now yielding native English timed text at least once, Supadata is
selectable for **local** FastAPI trials, while the default Python provider is unchanged.
Endpoint selection, response validation, cache reuse and no-skip errors were verified with mocked
HTTP only; no extra live acquisition request was made. Reliability over sessions or deployment
environments remains untested.
