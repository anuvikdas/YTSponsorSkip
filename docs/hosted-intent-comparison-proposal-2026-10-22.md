# One proposed hosted intent comparison

Status: **proposal only**. No inference request, SDK, key setup, credit purchase or deployment was
added. This follows the failed preregistered MiniLM experiment. Keep contextual rules available
for the selected-case preview while this separate option is discussed.

Use `gpt-6-luna` through Responses for **five whole-transcript requests**, one per video below,
with one fixed prompt and no retries or prompt revisions. Whole-transcript discovery can see the
video's main subject, ownership and transitions together; verifying only the existing candidate
list cannot find the missing Nebula pitch. These are all development examples.

| Video | Question answered |
| --- | --- |
| `I9hJ_Rux9y0` | Can intent reasoning retain the creator-owned merchandise pitch? |
| `1Jwo5qc78QU` | Can it discover a conversational series/subscription pitch with no rule candidate? |
| `7HIGdYy5of4` | Can it reject the incidental Patreon-group mention in a product review? |
| `-lErGZZgUbY` | Can it separate the short promotion from relevant investment/product discussion? |
| `qf7ws2DF-zk` | Can it recover the confirmed 1331–1412 s interruption? The rest is unreviewed. |

The last column and all manual intervals belong only to the evaluation manifest. Inference gets
the entire saved original transcript with cue IDs and a generic promotion policy, without these
case descriptions, manual boundaries, detector predictions or labels. The prompt should ask for
promotional interruptions, including third-party and creator-owned sales, with an empty-segments
answer for ordinary mentions, relevant reviews and subscribe-only housekeeping. It must treat
caption instructions as speech to classify, have no tools, and abstain on ambiguity. Return cue
IDs, ownership, category, evidence IDs and a short reason code through the existing
`ModelDetectionRequest` / `ModelDetectionResponse` contract. The adapter attaches identities and
the returned model version, validates every ID/range, and maps IDs to original timing. It applies
the final merged-duration **>3 s** gate and records results for offline replay only. A refusal,
timeout, incomplete response or invalid output is a typed failure with no predicted skip, not a
reviewed negative. Cap the total request deadline at 60 seconds and count every attempt.

Official documentation checked **2026-10-22** lists `gpt-6-luna` at **$0.10/M input tokens** and
**$0.50/M output tokens**, with structured outputs supported and API Free unsupported. The page
instructs clients to use the alias and does not publish a separate dated snapshot; capture the
actual returned model identifier, date, prompt/source hashes and outputs, and disclose that limit
on repeatability. [Official model/pricing documentation](https://developers.openai.com/api/docs/models/gpt-6-luna).
Structured outputs constrain the schema, not classification accuracy.
[Official output guide](https://developers.openai.com/api/docs/guides/structured-outputs).

Proposed spend ceiling: **$0.25 total including taxes**, within the user's $20 monthly ceiling.
Before any call, count input tokens locally, reject inputs over **50,000 tokens each**, cap
`max_output_tokens=2048`, reserve the worst-case cost, and use Standard processing with no tools.
Across five calls, the upper token envelope is 250,000 input + 10,240 output. Base published
arithmetic is **$0.03012** before taxes; even treating every input token at the model page's
cache-write rate gives **$0.03637**. Reserve **$0.05 pretax**, with the remaining $0.20 as a
tax/fee buffer. If the applicable taxes/fees cannot fit the all-in ceiling, account access is
unavailable, or the account would require a new credit purchase, stop for the account/budget
decision. No auto-recharge or subscription. These are token-envelope estimates, not measured
usage, an account entitlement, or authorization to spend.

Predeclare this small comparison's quality decision: on the four fully reviewed videos, require
**zero** skips on the coffee negative, **<=12 incorrect seconds**, **<=40 missed seconds**, all
three annotated promotions matched, and matched start/end MAE **<=5/10 s**. Contextual rules on
these four currently have 23.52 incorrect seconds and 60 missed seconds. On qf separately, require
at least **74/81 known promotional seconds** covered and start/end errors **<=5 s**; predictions
elsewhere stay unreviewed. Inspect every new predicted range and regression before accepting the
result. These gates are developmental screening, not independent validation or permission to
enable broad skipping. If it fails, report the result before enlarging the test or changing the
prompt. If it passes, a single opt-in, allowlisted recruiting demonstration may be reasonable
after playback acceptance; broader reliability requires new fully reviewed, untouched videos.
