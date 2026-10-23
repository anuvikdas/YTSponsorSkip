# Deterministic detector baseline

The first detector is offline, rules-based, replaceable, and free to run. It does not call an LLM, paid inference endpoint, or trained model, and its outputs are not connected to automatic playback skipping.

## Pipeline and main functions

`backend/src/ytsponsorskip/detector.py` contains five stages:

1. `build_windows()` creates 30-second windows with 15-second overlap. Every window retains its original snippet indices and combined text. Overlap preserves context when a disclosure and call-to-action land on opposite sides of a window boundary.
2. `RulesWindowClassifier.score()` emits a heuristic integer score and named evidence. `WindowClassifier` is a protocol so a later classifier can be compared without changing windowing, assembly, boundaries, or evaluation.
3. `assemble_candidates()` selects windows under Conservative or Aggressive policy, deduplicates snippet identities, and joins qualifying windows. Conservative candidates join across at most five seconds; Aggressive candidates allow fifteen seconds.
4. `refine_boundaries()` finds the first and last signal-bearing snippets inside each candidate and stops at a nearby explicit return-to-content phrase. Aggressive mode may add one nearby snippet on each side. Caption timing remains approximate.
5. `validate_intervals()` removes non-finite, negative, and backward intervals, sorts them, and merges overlap.

Each result retains its heuristic score, evidence labels, and contributing snippet identities for debugging.

## Rules and policies

| Evidence | Weight | Examples |
| --- | ---: | --- |
| Explicit disclosure | 4 | “sponsored by”, “paid partnership”, “brought to you by” |
| Affiliate relationship | 3 | affiliate link, earning a commission |
| Creator-owned offering | 3 | my course, our merch, our app, membership |
| Commercial offer | 2 | discount, free trial, promo code, percent off |
| Call to action | 2 | use my code, link in the description, sign up, shop now |
| Separable transition | 1 | before we continue, quick word, but first |

Scores are heuristic evidence totals, not calibrated probabilities.

Conservative mode requires a score of at least four plus either an explicit disclosure, a creator-owned offering paired with an offer/CTA, or an affiliate relationship paired with an offer/CTA. Aggressive mode lowers the evidence requirement but still requires both promotional context and an action/separation signal. Product names, reviews, comparisons, tutorials, and educational discussion alone have no positive rule and cannot qualify.

## Example

Suppose snippets around 100 seconds say:

- 100–104: “Before we continue, thanks to Acme for sponsoring this video.”
- 104–108: “Their service keeps your files organized.”
- 108–112: “Use code SAVE20 for 20% off; the link is in the description.”
- 112–115: “Now back to the camera test.”

Overlapping windows contain disclosure, transition, offer, and CTA evidence. They assemble into one candidate. Boundary refinement begins at the first signal and ends at the start of “Now back,” producing approximately 100–112 seconds. A sentence such as “I reviewed the Acme camera's autofocus” produces no interval because a product name and review context are not commercial intent.

## Known limitations

- Literal phrasing rules miss paraphrases, jokes, and promotions described without a disclosure or CTA.
- A discussion about advertising can quote rule phrases and create a false positive.
- Sparse or inaccurate captions can move or remove evidence.
- Signal-to-signal boundaries favor precision but can miss neutral descriptive seconds inside a long pitch.
- Creator promotions without phrases such as “my course” or “our merch” can be missed.
- Language support is currently English only.

The synthetic unit fixtures test behavior; they are not acquisition data or tune-set evaluation examples.
