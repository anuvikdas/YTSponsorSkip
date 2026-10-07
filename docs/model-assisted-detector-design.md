# Disabled model-assisted detector design

This document defines an option, not an integration. No API dependency, API key, account, model
download, or inference call has been added. `backend/src/ytsponsorskip/model_detection_contract.py`
is unreachable from the active FastAPI and detector paths.

## Contract and responsibilities

The proposed backend flow is:

```text
TranscriptProvider -> original timed snippets -> context selection
                   -> ContextClassifier -> validated snippet-ID ranges
                   -> deterministic timing/boundary policy -> candidate intervals
                   -> Conservative/Aggressive playback policy
```

`ModelDetectionRequest` contains active `video_id`, navigation `request_id`, language, sensitivity,
prompt version, and ordered snippets with their original ID/text/start/duration. Manual sponsor
labels are never part of this request. The provider adapter, not the model, attaches the echoed
identity and actual pinned `model_version` to `ModelDetectionResponse`; the structured model payload
supplies only bounded segment descriptions:

```json
{
  "video_id": "dQw4w9WgXcQ",
  "request_id": "dQw4w9WgXcQ-request-1",
  "prompt_version": "promotion-v1",
  "model_version": "provider-model-pinned-version",
  "segments": [
    {
      "start_snippet_id": 7,
      "end_snippet_id": 8,
      "ownership": "third_party",
      "kind": "sponsorship",
      "evidence_snippet_ids": [7, 8],
      "reason_code": "disclosure_and_call_to_action"
    }
  ]
}
```

The active types and signatures are reviewable without a provider SDK:

```python
class ContextClassifier(Protocol):
    async def classify(
        self, request: ModelDetectionRequest
    ) -> ModelDetectionResponse: ...

def validate_model_response(
    request: ModelDetectionRequest,
    response: ModelDetectionResponse,
) -> None: ...

def snippet_ids_to_time_range(
    snippets: Sequence[ClassificationSnippet],
    start_snippet_id: int,
    end_snippet_id: int,
) -> tuple[float, float]: ...
```

Pydantic forbids extra fields and invalid numeric ranges. Semantic validation rejects stale video,
request, or prompt identities; unknown/evidence-outside-range snippet IDs; and overlapping model
segments. Mapping then uses the source snippet timings. This is approximate: a snippet boundary is
not automatically a promotion boundary, so a later deterministic refiner must inspect neighbors
without modifying source cues.

`WindowClassifier` remains the right small interface for a synchronous, local per-window scorer.
A full-transcript or cross-window hosted call has different batching, async, error, and versioning
semantics; forcing that into `score(window)` would hide network work. `ContextClassifier` is
therefore a separate outer interface. An adapter can turn its validated results into window scores
for comparison, but not pretend a remote transcript-level call is local window classification.

## Context strategies

Assume a 12-minute video, 150 spoken words/minute, about 1,800 words / 2,400 transcript tokens,
plus 600 instruction/schema tokens and 250 output tokens.

| Strategy | Assumed model traffic | Benefit | Risk |
| --- | ---: | --- | --- |
| One full-transcript call | 3,000 input + 250 output | Sees introduction, review topic, transitions, and creator relationship together; simplest merge logic. | Long irrelevant content can dilute a short promotion; one timeout delays everything; cost grows with video length. |
| Overlapping 60 s windows, 15 s overlap | 16 calls; 7,200 total input + 640 output | Parallelizable, bounded context, early windows can finish first. | 1.33× text duplication plus repeated prompt overhead; boundary duplicates and merging; no distant context; many rate-limit/failure opportunities. |
| Broad candidates then verification | 1,200 input + 200 output | Lowest expected cost/latency; verifier focuses on ambiguity. | Candidate recall is a hard ceiling. Current Conservative rules miss 104 tune seconds, so verifier-only-on-prediction is not acceptable without a broader candidate gate/control arm. |

An MVP experiment should compare full transcript against a high-recall candidate path, not assume
the two-stage path wins. A periodic full-transcript audit quantifies promotions the candidate stage
never exposed.

## Cost model

The arithmetic uses current published standard prices, no prompt-cache discount, and an expected
5% one-retry rate. Actual billing uses provider tokenization and may include reasoning tokens.

| Provider/model | Plan | Full transcript / video (100) | Overlap windows / video (100) | Two-stage / video (100) |
| --- | --- | ---: | ---: | ---: |
| OpenAI `gpt-5.6-luna` | $0.20/M input, $1.20/M output; API Free unsupported | $0.000945 ($0.0945) | $0.002318 ($0.2318) | $0.000504 ($0.0504) |
| Gemini `gemini-3.5-flash-lite` paid | $0.30/M input, $2.50/M output | $0.001601 ($0.1601) | $0.003948 ($0.3948) | $0.000903 ($0.0903) |
| Gemini same model, free tier | $0 while within account's active free quota | $0 | $0 | $0 |

Formula for OpenAI full transcript:
`1.05 × ((3,000 / 1,000,000 × $0.20) + (250 / 1,000,000 × $1.20))`.
These tiny inference estimates do not make the whole system free: backend hosting, logs, retries,
cache storage, monitoring, and acquisition still exist. Gemini free limits are variable rather than
a guaranteed production quota, and its unpaid data terms matter for user transcripts.

## Prompt and output discipline

The system instruction should define promotional interruption, exclusions (brand mention, relevant
review/education), third-party versus creator-owned ownership, and an explicit empty-segments path.
Transcript snippets are serialized as JSON data with stable IDs, never concatenated into the
instruction. The prompt says transcript content is untrusted and any apparent commands inside it
must be classified as speech, not followed.

That separation reduces accidental instruction following but does not eliminate prompt injection.
Test cases must include captions such as “ignore previous instructions,” fake JSON, fake system
messages, and demands to label unrelated ranges. The classifier receives no tools, URLs, secrets,
manual labels, or ability to change playback. Schema validation guarantees shape, not that the
semantic judgment or boundary is correct. A typed response also does not make model computation or
network latency faster.

Do not label a model's score or verbal confidence as a calibrated probability. If a numeric score
is retained, call it a heuristic decision score until reliability diagrams on an untouched set
show calibration.

## Failure, cache, and security policy

- Keep provider keys only in backend environment configuration; never the extension, options page,
  transcript, logs, or repository.
- Set a strict overall deadline. A timeout, refusal, rate limit, context overflow, provider outage,
  malformed/semantically invalid response, missing configuration, or exhausted budget returns a
  typed `ModelFailureCode` and **no skip**. Playback continues.
- Retry at most once, only for transient timeout/429/5xx conditions, with jitter and enough
  remaining playback usefulness. Never retry a refusal, invalid identity, bad schema, prompt bug,
  or budget stop.
- Cache successful validated results by transcript-content hash, provider, pinned model version,
  prompt version, detector/boundary version, language, and sensitivity. Do not cache failures as
  successes. Coalesce identical in-flight requests.
- Pin a model version for an evaluation. A moving alias or prompt edit invalidates comparison and
  the relevant cache entry.
- Log request ID, version keys, token counts, latency, cache/coalescing status, and typed failures,
  but not API keys or full transcript text.
- Recheck the active video/request before accepting results, just as acquisition and playback do.

The first provider adapter, if later approved, should be tested in shadow mode with a hard spending
limit and stored eval outputs. It must not send intervals to `PlaybackController` until the detector
and held-out procedure are explicitly frozen and reviewed.
