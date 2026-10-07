# Detection strategy decision

Reviewed 2026-10-07. Vendor availability and prices are time-sensitive. “Measured” below means this
repository produced the result; model capability statements are expectations from documentation
until evaluated on our fixed data.

## Recommendation

For the $0 MVP, keep the improved deterministic rules as an explainable candidate detector in
shadow mode. Do not enable automatic skipping yet. The next comparison should add one local,
replaceable semantic classifier while keeping deterministic snippet-ID boundary mapping. With only
14 fully reviewed tune videos, train/evaluate by video rather than treating correlated windows as
independent examples, and collect more reviewed negatives before fitting a model.

The likely upgrade path is hybrid:

1. broad, inexpensive rules or a small local classifier propose candidates;
2. a semantic verifier distinguishes promotional interruption from relevant review/education;
3. deterministic code maps accepted original snippet IDs to time and applies Conservative policy;
4. failures, low-confidence cases, and invalid outputs produce no skip; and
5. compare a full-transcript audit against candidate-only verification, because a candidate filter
   can create an unrecoverable false negative before the verifier sees the text.

Only consider a hosted model after a shadow evaluation demonstrates enough gain to justify privacy,
latency, and nonzero operational cost. Keep rules as an auditable fallback and regression oracle.

## Strategy comparison

| Strategy | Expected strengths | Important failure modes and boundaries | Cost, privacy, deployment | Evidence needed |
| --- | --- | --- | --- | --- |
| Rules / lightweight NLP | Deterministic, inspectable, milliseconds, $0, easy regression tests. Token-aware matching (for example spaCy `Matcher`) can tolerate syntax better than raw regex. | Brittle paraphrases; context and sarcasm; rule growth; coarse cue boundaries. Conservative rules reduce false skips but miss implicit pitches. | CPU-only, local, no transcript leaves the service. Lowest maintenance while rules remain small. | Frozen tune procedure, more negative/review videos, perturbation tests for generated-caption errors, then held-out once. |
| Local statistical classifier | TF-IDF + logistic regression is cheap and explainable by feature weights. A small sentence-embedding/SetFit classifier can generalize beyond exact wording and run on CPU. | Four negative videos and ten positive videos are not enough independent units; correlated windows make random window splits leak. Probabilities require calibration. It still needs deterministic segment assembly and boundaries. | $0 software and local CPU; model artifact/version maintenance. SetFit adds PyTorch/model downloads. | More video-grouped labels, tune-only cross-validation, negative-video false-skip rate, calibration plot, runtime/RAM, and caption-noise tests. |
| Hosted LLM | Strong semantic context and typed structured output; can distinguish review subject from interruption and reason over creator ownership. | Semantic mistakes remain despite valid JSON; prompt injection in transcripts; variable latency/rate limits; full context can dilute signals; windows duplicate cost and lose distant context. Self-reported confidence is not calibrated. | Backend-only key, transcript disclosure to provider, API and hosting cost. Free quota is not an SLA. | Shadow run with pinned model/prompt, repeated latency/cost measurement, adversarial transcript tests, full-vs-window ablation, and fixed-label comparison. |
| Local open-weight generative model | Transcript stays local; weights are inspectable and can be adapted. Gemma 4 has small quantized variants; `gpt-oss-20b` supports structured output. | Smaller models can be weaker on ambiguity; JSON/schema support varies by runtime; startup and token latency; prompt injection still applies. “Free weights” do not make GPU/CPU time or hosting free. | Gemma 4 E2B Q4 is documented around 2.9 GB model memory and E4B Q4 around 4.5 GB; `gpt-oss-20b` requires about 16 GB. Free Render CPU is not a credible low-latency model host. | Local hardware benchmark, exact quantization/runtime, schema adherence, quality against tune, cold/warm latency, and an honest deployment-cost estimate. |
| Hybrid candidate + verifier | Concentrates expensive semantic work, retains explainable boundaries, and allows Conservative confidence gates. | Candidate recall caps total recall. The current Conservative rules still miss 104 labeled seconds, so blindly sending only its intervals would hide known text from the verifier. Multiple stages add versioning and diagnosis work. | Can remain $0 with local classifier; hosted verifier cost scales with candidate text. | Candidate-recall audit, periodic/full-transcript control arm, end-to-end latency, component ablations, and failure/no-skip tests. |

Rules have the clearest current evidence: on the tune set they find all 10 promotion videos with no
skip on 4 negatives, but miss 104 seconds in Conservative mode. None of the model alternatives has
been run in this repository.

## Current concrete model/API facts

### OpenAI hosted API

The current cost-sensitive hosted option is
[`gpt-5.6-luna`](https://developers.openai.com/api/docs/models/gpt-5.6-luna): a 1.05M-context model
with Structured Outputs, priced at $0.20/M input, $0.02/M cached input, and $1.20/M output tokens.
Its official model page lists the API Free tier as unsupported. A ChatGPT subscription is not API
credit; API billing and limits are separate. Structured Outputs constrain JSON Schema shape, but
the [official guide](https://developers.openai.com/api/docs/guides/structured-outputs) explicitly
notes that outputs can still contain mistakes and that refusals/incomplete responses need handling.

### Gemini hosted API

[`gemini-3.5-flash-lite`](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite) is a
current stable low-cost model with a 1,048,576-token input limit, structured output, and a documented
price of $0.30/M input and $2.50/M output tokens. The
[pricing page](https://ai.google.dev/gemini-api/docs/pricing) lists free-of-charge free-tier input
and output, but the [rate-limit page](https://ai.google.dev/gemini-api/docs/rate-limits) says actual
limits depend on account/tier and must be checked in AI Studio; they are not guaranteed capacity.
The [unpaid-service terms](https://ai.google.dev/gemini-api/terms) allow submitted content and
responses to be used to improve products and potentially reviewed by humans. Paid-service data is
treated differently. A Gemini consumer subscription is not assumed to include Developer API usage.

Both vendors support schema-constrained output suitable for the proposed contract. Neither has been
called, no account/key was created, and no provider dependency was installed.

### Open-weight options

Open-weight is not the same as free hosted inference.

- [Gemma 4](https://ai.google.dev/gemma/docs/core) publishes E2B, E4B, 12B, 26B A4B, and 31B
  variants. Google's approximate Q4 model-memory figures range from 2.9 GB (E2B) to 17.5 GB (31B),
  before application overhead and context/cache needs. It can run through local frameworks, but a
  production host still costs compute and operations.
- [OpenAI `gpt-oss`](https://openai.com/index/introducing-gpt-oss/) weights are Apache 2.0 and not
  served by the OpenAI API. The 20B model is documented at about 16 GB memory; the 120B model at
  about 80 GB. They are much heavier than the MVP needs.
- A small pretrained NLI zero-shot classifier or [SetFit](https://huggingface.co/docs/setfit/en/conceptual_guides/setfit)
  is a better first local semantic experiment than a generative 20B model. SetFit is designed for
  few-shot text classification and can run on CPU, but this dataset still needs more independent
  video-level examples to estimate generalization.

### What “Jev” refers to

“Jev” is identifiable: it is TypeSafe AI's early-access **System One** decision model, not a
generative chat LLM. The [official introduction](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
describes unstructured state plus typed probabilistic decisions. Its
[API documentation](https://docs.typesafe.ai/api) provides `choice`, `score`, and yes/no `noul`
questions. Current [`jev-1.13.0` model documentation](https://docs.typesafe.ai/models) lists a 64K
request context, $0.042/M input tokens, free output tokens, and dynamic rate limits.

It could classify each candidate window as third-party, creator-owned, or not promotional, but it
cannot generate arbitrary boundary objects; code would ask bounded questions over known snippet
ranges. It is vendor-hosted, early, and not $0. Its own
[jaggedness documentation](https://docs.typesafe.ai/model-jaggedness/jev-1.13) warns about literal
reading, irrelevant long state, adversarial content, option-order effects, and weak numeric
precision. Vendor claims of calibrated probabilities must still be tested on our distribution.
Therefore Jev is an interesting future comparison, not the MVP recommendation.

## Adoption gate

Before freezing any detector version, require:

- a written, versioned evaluation procedure and a candidate/prompt/model version;
- video-grouped tune comparisons that include false skipped time, negative videos affected, missed
  promotional time, boundary errors, runtime, and acquisition exclusions;
- perturbation and prompt-injection tests;
- repeated end-to-end latency including acquisition and any model call;
- measured token usage and a monthly-cost cap with no hidden retry loop; and
- explicit review before the one-time held-out evaluation or detector-driven playback.
