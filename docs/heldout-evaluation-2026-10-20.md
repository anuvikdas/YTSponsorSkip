# First frozen held-out evaluation — 2026-10-20

The Conservative freeze and exploratory criteria were recorded in
`docs/conservative-freeze-2026-10-20.md` **before** any held-out predictions were generated. This
is the first evaluation of the eight fully reviewed held-out videos. The original manual labels
and frozen detector were not edited. The labels are user annotations, not independently verified
ground truth. `data/evaluation/held-out-rules-frozen-2026-10-20.json` contains exact input file
hashes, transcript-identity hashes, source/config hashes, every prediction and match, separate
acquisition timings, and detector runtimes.

## Acquisition and coverage

No saved held-out transcript existed before this run. All eight IDs received exactly one native
Supadata acquisition: `mode=native`, `text=false`, `lang=en`, no generated transcription, no retry,
and a Free-credit check before each request. Each returned HTTP 200 with a nonempty English
timestamped cue list. Caption type remains **unknown**. Local ledger: **5/50 → 13/50**, with zero
job polls. The Free account counter moved **4/100 → 12/100** used credits. This is an observed
8-credit change, not a pricing guarantee. Cash spend for this run was $0. The two separately
authorized Chrome-check attempts were **not** used.

| Video ID | Cues | First–last cue start (s) | Acquisition (ms) |
| --- | ---: | ---: | ---: |
| `WVDQEoe6ZWY` | 146 | 0–428.32 | 1101.874 |
| `vIfC4Aj05Ps` | 82 | 0.12–243.06 | 1451.516 |
| `1Jwo5qc78QU` | 841 | 1.72–2542.2 | 1987.286 |
| `7HIGdYy5of4` | 690 | 0.08–1338.64 | 1920.779 |
| `e0kQ5WqjcU8` | 1073 | 0.12–2320.922 | 1841.864 |
| `rb7TVW77ZCs` | 77 | 7.09–257.898 | 1240.102 |
| `v-NEr3KCug8` | 74 | 7.704–280.579 | 1432.461 |
| `0_KhihMIOG8` | 172 | 0.08–874.08 | 1248.494 |

Acquisition mean **1528.047 ms**, range **1101.874–1987.286 ms**. This excludes detector
runtime. A 200 response and cue count do not prove full-video completeness: no independent video
duration was available for this check. Notably, the last `0_KhihMIOG8` cue ends at 883.84 s while
the user's second annotation ends at 890 s. At least the final 6.16 annotated seconds are beyond
the available cue timing; they remain missed in the primary metric. The lack of cues there may be
ordinary caption ending, truncation, or annotation-edge uncertainty; no cause is asserted.

## Conditional detector quality on eight usable inputs

Raw Conservative predictions and the strictly-greater-than-three-second playback-policy view
are **numerically identical in this run**; both retained the two predicted intervals. That does
not make the playback gate redundant generally. Automatic skipping remains disabled.

| Metric | Raw detector | Playback-eligible view |
| --- | ---: | ---: |
| Reviewed held-out coverage | 8/8 | 8/8 |
| Incorrect predicted seconds | 11.52 | 11.52 |
| Reviewed negatives with a predicted skip | 1/6 | 1/6 |
| Missed promotional seconds | 128.96/176 (73.27%) | 128.96/176 (73.27%) |
| Matched / unmatched annotated intervals | 1 / 2 | 1 / 2 |
| Unmatched predicted intervals | 1 | 1 |
| Mean matched start / end absolute error | 21.2 / 43.76 s | 21.2 / 43.76 s |
| Total offline detector runtime | 148.955 ms | same detector run |

Matching is one-to-one greedy by positive overlap, largest overlap first. Incorrect seconds are
the union of predicted ranges minus their overlap with annotated ranges. Missed seconds are the
union of annotated ranges minus that overlap. Boundary errors apply only to matched segments;
there is only one match here, so the means are that pair's absolute errors. Missing inputs never
count as negatives. All eight had inputs, so conditional detector coverage equals end-to-end
acquisition coverage in this one session, not a general availability estimate.

## Representative errors

- `7HIGdYy5of4` is a reviewed negative. The rule predicts **85.04–96.56 s** because a window
  combines product-review language with “mostly by my Patreon group” at 88.159 s. Evidence was
  `creator_owned`, `membership`, `sales`; the actual context explains how espresso machines were
  selected, not a Patreon pitch. This is a **classification/context** false positive, not a cue
  boundary problem. It alone accounts for all 11.52 incorrect predicted seconds.
- `1Jwo5qc78QU` has a user-labeled **2339–2399 s** promotion but no prediction. The transcript
  says “Over on Nebula, I've got a new series” near 2340.66 s, then discusses the series,
  CuriosityStream pricing near 2389.54 s, and a free trial/link near 2395.3 s. The frozen
  window-anchor combinations never assemble a qualifying candidate across this long, varied
  pitch. This is primarily a **classification/candidate assembly** miss, not merely an end-time
  adjustment. The routine “like, comment” at 2337.46 s remains non-promotional under the freeze.
- `0_KhihMIOG8` has user labels **55–59 s** and **778–890 s**. The short early line, “This video
  is sponsored by CuriosityStream and Nebula. More on them later,” starts at 55.84 s. The
  frozen refiner's ten-second minimum excludes this four-second annotation. That is a policy/
  minimum-duration interaction to review, not an acquisition failure. The later prediction is
  **799.2–846.24 s**: its late start omits the Nebula introduction at 778 s, and the end stops
  after the 26%-off/price cue although channel support and link language continue through about
  874 s. This is a **boundary/candidate-support** miss. Its last 6.16 annotated seconds lie past
  the final available cue, adding source-timing uncertainty. The primary metric still counts the
  entire label; no annotation was adjusted to improve the result.

The six reviewed negatives produced no other predictions. A video titled “This Video Is
Sponsored By ___ VPN” is a reviewed negative in the supplied labels and has no predicted skip;
its title alone did not become detector evidence. These specific snippets are diagnostic context,
not new labels and not rule-development inputs during this run.

## Predeclared decision and Chrome status

The freeze required 8/8 coverage (met), **0/6** negative videos with eligible skips (failed),
at most 30 incorrect seconds (met), at most 25% missed annotated time and all three segments
matched (failed), and at most 10-second mean matched start/end errors (failed). Therefore the
evidence supports **further detector work**, not an opt-in automatic-skipping demo yet. The
limited, zero-cost Supadata run supports local acquisition feasibility for this corpus/session;
cross-session reliability and independent completeness remain unverified. Held-out mistakes may
guide a future version only if this set is retired as an untouched final test; collect a new final
set before making generalization claims.

The user separately reported that the **saved-mode** Chrome checklist passed: ice cream showed
9:25–10:11 in Conservative mode; playback did not auto-skip; navigating to C in 100 Seconds
cleared the old interval and showed none; YouTube Home showed unsupported; and the popup named
the saved source and preview-only status. This is **user-reported** verification, not a new
automated Chrome test. No supporting screenshot file was supplied or saved in this repository
for this turn, so this report does not claim independent screenshot review.

For the requested **live Supadata** Chrome check, computer control hit a browser security-policy
block on the extension settings URL. No alternate route or acquisition request was attempted.
The local server was listening on `127.0.0.1:8000`, but that is not Chrome verification. To
complete the manual check: open extension Settings; keep preview on, Conservative selected,
fixtures and browser probe off, choose Supadata, save, then open
[ice cream](https://www.youtube.com/watch?v=O7sQBfpQCvU) and
[C in 100 Seconds](https://www.youtube.com/watch?v=U3aXWizDbQ4) in the same tab. The popup
should say Supadata; the first should show its actual interval, the second should show
**No promotions detected** rather than an error; neither should seek. Rapidly
navigate while loading and confirm the popup shows only the current video; reopen it and confirm
no extra attempt in `results/trial-budget.sqlite3`. Do not repeat either video after an error.
At most **two** Chrome-check attempts remain authorized, including failures. Capture popup
screenshots. In `chrome://extensions`, open the YTSponsorSkip service worker's Inspect view
**before** navigating, then use its Network panel to inspect the two existing detection
responses without sending duplicate requests. Record `provider_latency_ms`,
`detection_latency_ms`, `total_latency_ms`, `transcript_cache_hit`, and
`detection_cache_hit`. A popup reopen should cause no new Network entry or ledger reservation.
The two prior local API live checks in `docs/local-preview-milestone.md` are not this Chrome check.

Reproduce the offline evaluation from saved normalized transcripts without another API call:

```bash
.venv/bin/python scripts/evaluate_heldout.py --output /tmp/heldout-audit.json
```

The script intentionally refuses to overwrite an existing result and verifies frozen hashes. The
raw provider response records and the local ledger remain ignored under
`results/`; only normalized, secret-free transcript inputs and evaluation outputs are committed.
