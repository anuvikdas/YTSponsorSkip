# Small Render acquisition experiment

Run date: 2026-10-07. Backend: `https://ytsponsorskip-api.onrender.com`. Cost: $0.

## Deployment health

`GET /health` returned HTTP 200 with `{"status":"ok","environment":"render-free"}`. Measured client latency was 162.676 ms, with first byte at 162.038 ms. This proves the deployment was responsive at that moment. It is not a cold-start measurement because the service's prior idle state is unknown.

## Attached manual-caption responses

| Observation | Request ID | Cache | Coalesced | Provider latency | Caption | Snippets |
| --- | --- | --- | --- | --- | --- | --- |
| First attached response | `c9018b0a7e0c40fd9fc3e5cd6256bdb7` | miss | no | 1,378.468 ms | English manual | 61 |
| Second attached response | `e5d684eecf044445a304ddd25df6fb7b` | hit | no | unavailable on cache hit | English manual | 61 |

Both responses report median snippet duration 2.68 seconds, median start gap 2.84 seconds, zero overlapping adjacent snippets, and a 209.96-second covered span. Their transcript payloads are identical after request/cache metadata is removed.

The second response demonstrates an application cache hit because the API explicitly returned `cache_hit: true`; HTTP 200 alone would not establish that. Its `provider_latency_ms: null` is consistent with avoiding an upstream provider call. The first attached response explicitly reports `cache_hit: false`, but it cannot be called a cold start or assumed to be the first request handled by that Render process. Client end-to-end latency for the two attached requests was not recorded in the JSON files.

## Bounded follow-up

The selected confirmed generated-English corpus video was `Vw1Qrko8oTs`.

| Video | Expected case | HTTP | API result | Request ID | Client latency | Caption/snippets |
| --- | --- | --- | --- | --- | --- | --- |
| `Vw1Qrko8oTs` | generated English | 503 | `REQUEST_BLOCKED`, retryable | `render-small-generated-20261007` | 1,166.345 ms | unavailable |
| `Z_jl71GApQQ` | captions-disabled negative | not sent | stopped after blocking signal | n/a | n/a | n/a |

The experiment stopped immediately after `REQUEST_BLOCKED`, as required. No full-corpus run, proxy, paid host, or paid service was used.

## Conclusion and uncertainty

The Render service itself is healthy, one manual transcript was acquired and then demonstrably cached, and the next uncached generated-caption acquisition was blocked. This is evidence that deployment health, caching, and YouTube acquisition reliability are separate concerns. It is not enough evidence to characterize generated-caption success, negative-case behavior on the current process, cold-start latency, or reliable acquisition across channels. A full corpus run is not justified while the blocking signal persists.
