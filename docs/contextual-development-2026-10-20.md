# Contextual detector development checkpoint — 2026-10-20

This is a **development** comparison, not a new independent test. It uses 14 fully reviewed
`tune` videos plus the eight formerly held-out videos, which are now explicitly retired into
development evidence. The original frozen held-out report at
`data/evaluation/held-out-rules-frozen-2026-10-20.json` was not changed. The two partial tune
reviews remain excluded. `qf7ws2DF-zk` is a separate partial opening probe with no confirmed
end; it is excluded from complete-interval metrics. Manual annotations enter only the evaluator
after each detector returns predictions. They are user annotations, not independently verified
ground truth. There is no untouched final evaluation set remaining in this corpus.

## Credit use and strategic coverage

The local backend was not running, so its 900-second in-memory cache could not hold or export the
previously requested `qf7ws2DF-zk` transcript. No saved copy existed. Exactly **one** of the
five newly authorized native acquisitions was used, for that video. The request was `mode=native`,
`text=false`, `lang=en`, with no automatic retry, generated-transcript fallback, or paid service.
It returned HTTP 200, English (`en`), **527** nonempty timed cues in **2347.294 ms**. The provider
caption type is **unknown**. Source offset/duration milliseconds were converted to seconds with
original text, order and overlaps preserved. First cue starts at **0.15 s**, last at **1410.78 s**
and its supplied duration yields an analysis end of **1412.943 s**. This does not independently
prove full-video completeness or exact speech/promotion boundaries. The normalized transcript and
secret-redacted response are in Git-ignored `results/development-transcripts/` for local reuse.
The Free account counter moved **14/100 → 15/100 used credits**, an observed one-credit change;
the local attempt ledger moved **15/50 → 16/50**. Observed cash spending was $0. The prior
`qf7ws2DF-zk` Chrome attempt is separate and was not counted against this new five-attempt cap.

The other **four** allowed attempts were deliberately not used. Existing saved cues and manual
reviews already cover the requested gaps: `1Jwo5qc78QU` and `0_KhihMIOG8` have long promotions;
`I9hJ_Rux9y0` is a creator-owned merchandise pitch; `qf7ws2DF-zk` supplies the subtle
sponsor-introduction transition; and `7HIGdYy5of4` plus `e0kQ5WqjcU8` are reviewed
non-promotional espresso product discussions. Another credit without a new annotation question
would not improve this diagnosis. Do not run the remaining attempts merely to fill a quota.

## Stage evidence and focused change

- **`qf7ws2DF-zk`:** the baseline on the newly saved source exactly reproduces the user-reported
  preview at **1398.33–1408.38 s**. Cues around **1331.9–1334.5 s** contain the sponsor lead-in.
  Disclosure-only 30-second windows scored 3 and did not qualify as anchors; two neutral windows
  then separated them from the actionable offer/URL window. The existing candidate began at
  **1379.13 s** and cue refinement retained only the final 10.05 seconds. The opening was lost
  **before boundary refinement**, in window qualification/candidate assembly. The experimental
  continuity rule links an explicit named sponsor introduction to a same-brand actionable
  candidate no more than 90 seconds later, without crossing an explicit return-to-content cue.
  The unchanged refiner then starts at **1334.49 s** and ends at **1408.38 s**. That is a
  **3.49-second approximate opening lag** versus the user's 1331-second estimate, down from
  **67.33 seconds**. Because the end is unreviewed, no recall or end-error claim is made.
- **`I9hJ_Rux9y0`:** original windows scored `creator_owned + sales` but had no required
  coupon/URL/CTA anchor. A contextual anchor now requires first-person creation/support, a
  first-person shop/store, and a purchase/browse action in the same window. The baseline refiner
  then still drops the candidate because its only cue-level signal is the final shop cue, shorter
  than its ten-second minimum. Only when conventional refinement returns nothing does the
  contextual refiner use the explicit creation cue and shop-ask cue as edges. The result is
  **683–715 s**, matching the user's reviewed interval. This uses transcript text and cue
  timing, never the user's 683–715 label. Derived cue ends remain uncertain speech boundaries.
- **`7HIGdYy5of4`:** the coffee-review false positive at **85.04–96.56 s** remains. A broad
  product-review window combines “my Patreon group” with equipment-selection language and is
  misclassified as a promotion. This is a context/classification error, not boundary trimming.
  The new explicit-pitch rule does not match it, but the frozen classifier still does.
- **`1Jwo5qc78QU`:** the 2339–2399 s Nebula/CuriosityStream pitch remains completely missed.
  The “new series” opening and later offer/URL never make a qualifying candidate. A rule that
  only verifies existing candidates cannot recover it. `0_KhihMIOG8` still has a short
  four-second sponsor disclosure removed by the ten-second refiner gate and a later pitch whose
  candidate spans the opening but cue refinement starts at 799.2 instead of 778 s and ends at
  846.24 instead of 890 s. Its last 6.16 labeled seconds are beyond the final saved cue.

The change is one experimental **explicit-pitch context rescue** in candidate discovery and
its necessary cue-edge fallback. It does not globally pad segments, change the frozen rules,
weaken the three-second playback gate, or add video-ID/timestamp exceptions. It is selectable
with `YTSS_DETECTOR_VARIANT=contextual_v1`; the default remains `frozen_rules`. Automatic skipping
from predictions remains disabled in either variant.

## Before/after on saved, fully reviewed development data

The table uses the evaluator's half-open interval unions, one-to-one maximum-positive-overlap
matching, and playback-eligible final intervals (strictly greater than three seconds). There are
**22/22** usable reviewed transcripts, **13** reviewed positives with **14** labeled intervals,
and **9** reviewed negatives. The total labeled promotional duration is **763 s**. Acquisition
failures are not detector failures; there were no missing reviewed inputs in this offline run.

| Conservative metric | Frozen rules | Contextual v1 |
| --- | ---: | ---: |
| Incorrect predicted seconds | 36.52 | 36.52 |
| Negative videos with any predicted skip | 1/9 | 1/9 |
| Missed promotional seconds | 240.96 (31.6%) | 208.96 (27.4%) |
| Matched labeled intervals | 11/14 | 12/14 |
| Mean matched start / end absolute error | 4.473 / 10.978 s | 4.100 / 10.063 s |
| Total local detector runtime, one run | 337.504 ms | 360.116 ms |

All **32 seconds** of missed-time improvement come from the previously unpredicted creator shop
pitch. No reviewed video regressed in predicted intervals in this corpus; the other 21 complete
video outputs were unchanged. The boundary-error means shift because an exact new match enters
the denominator, **not** because the old matched edges improved. Runtime differences are
run-to-run observations, not an acquisition or latency guarantee. For context, the 14 original
tune videos improve from **112 → 80** missed seconds while retaining **25** incorrect seconds and
**0/3** negatives with skips. The eight retired held-out videos remain at **128.96** missed,
**11.52** incorrect, and **1/6** negatives with skips. Aggressive also gains 32 recalled seconds
but remains unsafe-looking: **220.529** incorrect seconds and **2/9** negatives with skips. See
`data/evaluation/contextual-development-2026-10-20.json` for predictions, matches, per-video
metrics, source hashes, and both mode runtimes.

## Reproduction and preview

From the repository root, without acquisition or inference:

```bash
.venv/bin/python scripts/evaluate_contextual_development.py \
  --output /tmp/contextual-development-recheck.json
.venv/bin/python scripts/trace_detector_stages.py \
  --source results/development-transcripts/qf7ws2DF-zk.json \
  --focus-seconds 1331 --output /tmp/qf-stage-trace.json
```

The stage tracer above intentionally traces the **frozen baseline**; the focus second only
filters its output. The comparison runner includes qf predictions if its ignored transcript is
still present locally. To see the new rule in Chrome without another credit, start the backend
with the opt-in variant and use **Saved reviewed-tune transcript** + Conservative preview on
[`I9hJ_Rux9y0`](https://www.youtube.com/watch?v=I9hJ_Rux9y0):

```bash
YTSS_DETECTOR_VARIANT=contextual_v1 YTSS_REQUEST_TIMEOUT_SECONDS=30 \
  .venv/bin/uvicorn ytsponsorskip.main:app --app-dir backend/src \
  --host 127.0.0.1 --port 8000
```

Expect **11:23–11:55** in the popup with **Preview only — automatic skipping off**; playback
must not seek. Normal startup without `YTSS_DETECTOR_VARIANT` remains the frozen baseline. No
Chrome check of the new variant was automated or user-reported yet. Avoid selecting live
Supadata for a repeat qf preview: that would be another billable acquisition on a cache miss.

## Next decision

The $0 contextual rule is useful for explicit creator-shop language and a named sponsor lead-in,
but it does not solve indirect creator-network pitches, broad product-review false positives, or
long mixed-purpose boundaries. More local hand-written phrase rules are likely to overfit this
small development set. The next bounded comparison should try **local, all-window semantic
discovery** on these saved transcripts, followed by the same boundary module. Candidate-only
verification would miss the Nebula opening because no current candidate exists. Compare against
the unchanged frozen and contextual baselines, and require lower missed time **without any new
negative-video skips** before considering an opt-in auto-skipping demo. No hosted model call,
SDK, or paid inference is authorized by this checkpoint. A new untouched validation set is
required before claiming generalization, because all formerly held-out examples now informed
development. The smallest manual labeling task is to confirm the **end** of the qf promotion
and whether its lead-in around 22:11 should be included, before treating that example as a
complete interval.
