# Next detection experiment — proposal only, 2026-10-11

**2026-10-20 status note:** This document preserves the original proposal and historical
thresholds. The first eight-video held-out evaluation has since run; see
`docs/heldout-evaluation-2026-10-20.md`. A new partially reviewed tune example,
`qf7ws2DF-zk`, has an approximately confirmed promotional opening but no confirmed end or
saved timed transcript. See `docs/development-example-qf7ws2DF-zk.md`. It belongs in the
context-aware comparison as a qualitative opening-recall diagnostic, **not** full-video accuracy.
Do not tune against the previously evaluated held-out set while calling it untouched. A new
untouched final set would be required after further rule/model development.

No model was downloaded, installed, or invoked for this checkpoint. No API calls or costs.
This dated comparison supplements the older strategy documents; their historical price tables
are not a current purchasing recommendation. Official documentation was checked on 2026-10-11.

## Two options

| | Lightweight local semantics | Hosted contextual LLM |
| --- | --- | --- |
| Concrete option | Frozen `sentence-transformers/all-MiniLM-L6-v2` embeddings, similarity to generic promotional and non-promotional prototypes | `gpt-6-luna`, JSON-structured snippet-ID segments under the existing provider-neutral contract |
| Proposed strengths (not measured) | May recognize paraphrased sales/continuation text beyond literal regexes; local, cached, no per-call charge | Can jointly reason about the video's subject, sales intent, creator ownership and topical return |
| Risks | Similarity is not promotional intent; reviews/education may resemble sales, short context misses ownership, thresholds can overfit | Can invent spans, follow caption instructions, miss short pitches in long input, vary across calls, incur latency/failures/cost |
| Boundaries | Cue-level semantic score/continuation, still source-timing limited | May select better cue IDs, but cannot infer reliable word timing from start-only cues |
| Deployment now | Development-only CPU experiment; measure load/RAM/runtime before considering backend | Not compatible with a guaranteed $0 budget for this named API option; discussion only |

The publisher describes MiniLM as a sentence/short-paragraph encoder producing 384-dimensional
vectors; default truncation starts beyond 256 word pieces. It is not an off-the-shelf sponsorship
classifier. Use tokenizer-bounded views with overlap and cue-ID mappings, not a silently truncated
full transcript. Keep original source cues unchanged even when a long cue is split for encoding.
[Publisher model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).

OpenAI currently lists GPT-6 Luna standard input at **$0.10 / million tokens**, output at
**$0.50 / million**, structured outputs supported, and **API Free not supported**. For an illustrative
3,000 input + 250 output tokens, base inference is $0.000425/video; fourteen such calls are $0.00595,
before retries, reasoning/output variation, or other infrastructure. These are assumptions, not
measured corpus token counts or a spending commitment. A 1,200-input/200-output candidate call
would be $0.00022 under the same assumptions; long transcripts or repeated windows can cost more.
No paid test is recommended under the current budget. [Official model/pricing page](https://developers.openai.com/api/docs/models/gpt-6-luna).

Structured output constrains response shape, not promotion accuracy. Refusals, incomplete responses,
unknown cue IDs, mismatched identities and unsupported ranges must fail closed, with no skips.
Treat transcript text as untrusted data; give the classifier no tools, secrets or labels.
[Official structured-output guide](https://developers.openai.com/api/docs/guides/structured-outputs).

## Whole-transcript analysis versus candidate verification

For a hosted model, whole-transcript analysis sees distant topic/ownership context and can discover
a promotion with no lexical anchor. It also increases request size, wait time and distraction;
one failure affects the whole video. Chunked all-window analysis can finish incrementally but loses
global context and needs overlap/merging. For MiniLM, “whole transcript” means **scanning all
token-bounded windows**, never averaging a whole video into one vector or exceeding its token limit.

Candidate verification is cheaper and narrower, but its recall ceiling comes from what is supplied.
Verification only of **final Conservative predictions** cannot recover 104 missing labeled seconds.
Unrefined Conservative candidates cover 95 of those seconds; a modest, predeclared context margin
may help the additional 1 second, but nothing establishes the missing 8-second source tail. Candidate
coverage is not permission to skip whole candidates: they contain substantial ordinary content.

Even broad candidates can miss subtle affiliate pitches, creator products introduced conversationally,
membership appeals without the current lexical anchors, a pitch distant from its disclosure, noisy
caption paraphrases, and promotions mistaken for the video's main topic. `I9hJ_Rux9y0` illustrates
this concern if its apparent shop pitch is confirmed: Conservative has no candidate there. Hence a
candidate arm needs an **all-window discovery control**, not only a precision score on candidates.

## Does this dataset support training?

Not a reliable supervised classifier yet. There are fourteen independent reviewed tune videos,
ten labeled promotions and four reported negatives, with identified annotation-policy questions.
Thousands of overlapping windows do not create thousands of independent examples. Training and
testing on randomly split windows would leak speaker, channel, topic and near-duplicate text.

A frozen encoder with generic prototypes is a feasible hypothesis test. It is not trained on these
labels, but choosing thresholds based on tune metrics is still tuning. Later, compare a small
regularized classifier only with substantially more diverse, consistently labeled videos, grouped
by video/channel. Any internal cross-validation uses tune only; the current held-out set stays
untouched until model, taxonomy, policy and failure behavior are frozen. Four negative examples
cannot establish a useful low false-skip rate in production.

## Recommended bounded experiment, for approval

**Budget: $0 service/inference spend.** Existing local CPU/storage/electricity only; no cloud
resources. One open-model download, pinned revision/package versions, in an isolated development
environment after approval. Do not add it to the production requirements, Docker image or extension.
Stop if it needs paid compute; no hosted fallback. Cap exploratory work at the 14 saved tune videos,
three predeclared similarity-margin settings (0.05/0.10/0.15, heuristic not probabilities), two context
arms and one timing repeat of the chosen setting. Do not keep searching thresholds until they fit.

1. Resolve/version the annotation questions with the user. Preserve original labels/results and
   recompute the unchanged rules on any revised targets. Define whether subscribe-only appeals count.
2. Freeze generic positive prototypes for explicit third-party pitches and creator-owned sales,
   plus negative prototypes for reviews, brand mentions, education and ordinary channel housekeeping.
   Do not use annotated timestamps, copied labeled passages, video IDs or brand-specific exceptions
   as inference features. Prototype wording and hash become part of configuration.
3. Scan tokenizer-limited overlapping cue neighborhoods (target <=224 word pieces, 32-word-piece
   overlap, no silent truncation). Cache embeddings by transcript/tokenizer/model/view hash. Compare
   **all-window discovery** with **unrefined rule candidates plus two neighboring cues on each side**.
   Preserve source IDs; the candidate path must not use annotations to choose context.
4. Score positive-vs-negative prototype similarity margins. Require contextual interruption/sales
   evidence before proposing a range; do not let similarity to a product name justify a skip.
   Keep the rules as a comparator, not a hidden filter in the all-window discovery control. Initially
   return evidence and cue spans for offline review only. Abstain when ambiguous.
5. Implement a separate local adapter/view builder and recorded-output exporter using the existing
   snippet-ID contract. Reuse this checkpoint's comparison runner and metrics. Record model revision,
   prototype/config hashes, corpus/label hashes, actual outputs, load time, warm runtime, peak memory,
   token truncation checks and abstentions. Keep all live-call paths absent.

Proposed success criteria on the unchanged-label comparison: **<=25 incorrect seconds**, **0/4
negative videos with skips**, **<=80 missed seconds** (at least 24 s improvement), and start/end MAE
no worse than **4.6/8.3 s** while preserving all ten matched promotions. Require inspection of every
new false-skip range and every all-window-only candidate, not just aggregate improvement. These
thresholds are exploratory gates, not statistical assurance. If labels change, freeze corresponding
baseline-relative gates before running; never tune the targets after seeing model results.

Engineering gates: no source text/timing mutation, no silent truncation, no invalid/unmapped IDs;
target <=2 s/video warm CPU time and <=1 GB incremental peak memory on this machine, with load
time reported separately. These are targets, not claimed performance. Failure simply ends the
experiment for discussion. Even a passing result does **not** authorize held-out evaluation,
deployment or automatic skipping; it just supports deciding whether semantic refinement is worth
further work. If candidate discovery misses important cases, prefer fixing recall or widening context
over polishing a verifier that never sees the missing promotion.
