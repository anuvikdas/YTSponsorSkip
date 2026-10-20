# Tune error review — all 14 reviewed videos

Generated from the preserved rules evaluation. Conservative is the primary review mode.
Manual annotations are evaluation targets, not independently verified truth. No acquisition or model calls; held-out and partial reviews excluded.

## Reading the report

A matched prediction with an early/late edge is a boundary error; an unmatched prediction/annotation is a possible classification/assembly error. These are diagnostic categories, not proof of semantic cause. A separate label-free candidate trace locates where missed time was lost. Cue tags indicate overlap, not that the entire cue is wrong.
All cue ends below are derived analysis spans. Source starts are preserved; silence, mixed-purpose speech, and the final-cue fallback make exact ends uncertain. Time beyond the observed span is not called a classifier failure.

Metrics reuse half-open union/intersection arithmetic and greedy one-to-one maximum-overlap matching from evaluation.py; any positive overlap qualifies for matching. Boundary errors are absolute endpoint differences for matched pairs only.

Saved evaluation SHA-256: `fea912236139dd52c59462b4f9bce7f0d18b988bc2ff8fa2020280292b9d8b2d`.

| Video | Annotated | Conservative | Aggressive | C false / missed | A false / missed |
| --- | --- | --- | --- | ---: | ---: |
| [094y1Z2wpJg](https://www.youtube.com/watch?v=094y1Z2wpJg) | 20:48–22:07 (1248–1327 s) | 20:54–22:06 (1254–1326 s) | 20:52–22:09 (1252–1329 s) | 0 / 7 s | 2 / 4 s |
| [bHIhgxav9LY](https://www.youtube.com/watch?v=bHIhgxav9LY) | 13:33–14:42 (813–882 s) | 13:39–14:45 (819–885 s) | 13:37–14:47 (817–887 s) | 3 / 6 s | 5 / 4 s |
| [iWeu2dxHRDg](https://www.youtube.com/watch?v=iWeu2dxHRDg) | 17:30–18:18 (1050–1098 s) | 17:30–18:18 (1050–1098 s) | 17:25–18:25 (1045–1105 s) | 0 / 0 s | 12 / 0 s |
| [DTvS9lvRxZ8](https://www.youtube.com/watch?v=DTvS9lvRxZ8) | None | None | None | 0 / 0 s | 0 / 0 s |
| [I9hJ_Rux9y0](https://www.youtube.com/watch?v=I9hJ_Rux9y0) | 11:23–11:55 (683–715 s) | None | None | 0 / 32 s | 0 / 32 s |
| [lXfEK8G8CUI](https://www.youtube.com/watch?v=lXfEK8G8CUI) | 09:18–10:45 (558–645 s) | 09:21–10:19 (561–619 s) | 09:20–10:23 (560–623 s) | 0 / 29 s | 0 / 24 s |
| [-lErGZZgUbY](https://www.youtube.com/watch?v=-lErGZZgUbY) | 00:53–01:14 (53–74 s) | 00:50–01:23 (50–83 s) | 00:43–01:46 (43–106 s) | 12 / 0 s | 42 / 0 s |
| [MRtg6A1f2Ko](https://www.youtube.com/watch?v=MRtg6A1f2Ko) | 00:35–01:44 (35–104 s) | 00:25–01:30 (25–90 s) | 00:21–01:30 (21–90 s) | 10 / 14 s | 14 / 14 s |
| [9lx11dy9J30](https://www.youtube.com/watch?v=9lx11dy9J30) | 15:03–16:02 (903–962 s) | 15:03–15:42 (903–942 s) | 14:55–15:59 (895–959 s) | 0 / 20 s | 8 / 3 s |
| [Sew4rctKghY](https://www.youtube.com/watch?v=Sew4rctKghY) | 12:04–13:08 (724–788 s) | 12:04–13:04 (724–784 s) | 11:53–13:13 (713–793 s) | 0 / 4 s | 16 / 0 s |
| [O7sQBfpQCvU](https://www.youtube.com/watch?v=O7sQBfpQCvU) | 09:25–10:11 (565–611 s) | 09:25–10:11 (565–611 s) | 09:21–10:13 (561–613 s) | 0 / 0 s | 6 / 0 s |
| [U3aXWizDbQ4](https://www.youtube.com/watch?v=U3aXWizDbQ4) | None | None | None | 0 / 0 s | 0 / 0 s |
| [x7X9w_GIm1s](https://www.youtube.com/watch?v=x7X9w_GIm1s) | None | None | None | 0 / 0 s | 0 / 0 s |
| [aircAruvnKk](https://www.youtube.com/watch?v=aircAruvnKk) | 16:50–17:03 (1010–1023 s) | 16:50–17:03 (1010–1023 s) | 16:48–17:07 (1008–1027 s) | 0 / 0 s | 6 / 0 s |

## The Simplest Math Problem No One Can Solve - Collatz Conjecture — 094y1Z2wpJg

[Open video](https://www.youtube.com/watch?v=094y1Z2wpJg). Caption type: generated. Observed analysis span: 00:00–22:09 (0–1329 s).

Annotated: **20:48–22:07 (1248–1327 s)**.

### Conservative

Predicted: 20:54–22:06 (1254–1326 s).

False skips: None.
Missed: 20:48–20:54 (1248–1254 s); 22:06–22:07 (1326–1327 s).

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 7 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 20:29–22:09 (1229–1329 s).

- Matched label 1 / prediction 1: start error 6 s, end error 1 s.

Rule evidence: cta, disclosure, sales, url.
### Aggressive

Predicted: 20:52–22:09 (1252–1329 s).

False skips: 22:07–22:09 (1327–1329 s).
Missed: 20:48–20:52 (1248–1252 s).

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 4 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 20:29–22:09 (1229–1329 s).

- Matched label 1 / prediction 1: start error 4 s, end error 2 s.

Rule evidence: cta, disclosure, sales, url.

### Transcript context

Context 20:40–21:02 (1240–1262 s):

> [20:37–20:42†] cue #453 · C: context · A: context — (gentle music)

> [20:42–20:44†] cue #454 · C: context · A: context — What I love about 3x+1

> [20:44–20:47†] cue #455 · C: context · A: context — is it's a problem almost anyone can understand

> [20:47–20:48†] cue #456 · C: context · A: context — and play around with.

> [20:48–20:50†] cue #457 · C: missed · A: missed — And actually trying to figure things out for yourself

> [20:50–20:52†] cue #458 · C: missed · A: missed — is the best way to learn,

> [20:52–20:54†] cue #459 · C: missed · A: context — which is why I subscribed to Brilliant,

> [20:54–20:56†] cue #460 · C: context · A: context — the sponsor of this video.

> [20:56–20:59†] cue #461 · C: context · A: context — Now, recently, Brilliant have upped their interactivity.

> [20:59–21:01†] cue #462 · C: context · A: context — For example, here is a great lesson

> [21:01–21:03†] cue #463 · C: context · A: context — on the Pythagorean theorem.

Context 21:58–22:17 (1318–1337 s):

> [21:56–21:59†] cue #487 · C: context · A: context — and a community of 8 million other learners,

> [21:59–22:01†] cue #488 · C: context · A: context — go to brilliant.org/veritasium.

> [22:01–22:04†] cue #489 · C: context · A: context — I will put that link down in the description.

> [22:04–22:06†] cue #490 · C: context · A: context — So I wanna thank Brilliant for sponsoring this video,

> [22:06–22:09†] cue #491 · C: missed · A: false skip — and I wanna thank you for watching.

† End is derived, not a source-supplied speech or promotion boundary.

## The Biggest Misconception About Electricity — bHIhgxav9LY

[Open video](https://www.youtube.com/watch?v=bHIhgxav9LY). Caption type: manual. Observed analysis span: 00:00–14:47 (0–887 s).

Annotated: **13:33–14:42 (813–882 s)**.

### Conservative

Predicted: 13:39–14:45 (819–885 s).

False skips: 14:42–14:45 (882–885 s).
Missed: 13:33–13:39 (813–819 s).

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 6 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 13:14–14:47 (794–887 s).

- Matched label 1 / prediction 1: start error 6 s, end error 3 s.

Rule evidence: cta, disclosure, sales, url.
### Aggressive

Predicted: 13:37–14:47 (817–887 s).

False skips: 14:42–14:47 (882–887 s).
Missed: 13:33–13:37 (813–817 s).

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 4 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 13:14–14:47 (794–887 s).

- Matched label 1 / prediction 1: start error 4 s, end error 5 s.

Rule evidence: cta, disclosure, sales, url.

### Transcript context

Context 13:25–13:47 (805–827 s):

> [13:23–13:30†] cue #335 · C: context · A: context — are really what's delivering your power.

> [13:30–13:31†] cue #336 · C: context · A: context — Hey, now that you understand

> [13:31–13:34†] cue #337 · C: missed · A: missed — how electrical energy actually flows,

> [13:34–13:37†] cue #338 · C: missed · A: missed — you can think about that

> [13:34–13:37†] cue #339 · C: missed · A: missed — every time you flick on a light switch.

> [13:37–13:39†] cue #340 · C: missed · A: context — And if you want to take your switches to the next level,

> [13:39–13:41†] cue #341 · C: context · A: context — the sponsor of this video, Caseta by Lutron,

> [13:41–13:43†] cue #342 · C: context · A: context — provides premium smart lighting control,

> [13:43–13:47†] cue #343 · C: context · A: context — including switches, remotes, and plug-in smart dimmers.

Context 14:34–14:55 (874–895 s):

> [14:33–14:35†] cue #367 · C: context · A: context — they're just a click or a call away.

> [14:35–14:37†] cue #368 · C: context · A: context — Learn more about Caseda at Lutron's website,

> [14:37–14:39†] cue #369 · C: context · A: context — lutron.com/veritasium.

> [14:39–14:41†] cue #370 · C: context · A: context — I will put that link down in the description.

> [14:41–14:44†] cue #371 · C: false skip · A: false skip — So, I want to thank Lutron Electronics

> [14:44–14:45†] cue #372 · C: false skip · A: false skip — for sponsoring this video,

> [14:45–14:47†] cue #373 · C: context · A: false skip — and I want to thank you for watching.

† End is derived, not a source-supplied speech or promotion boundary.

## Car Thieves vs the Almost Final GlitterBomb 5.0 — iWeu2dxHRDg

[Open video](https://www.youtube.com/watch?v=iWeu2dxHRDg). Caption type: manual. Observed analysis span: 00:00–18:25 (0–1105 s).

Annotated: **17:30–18:18 (1050–1098 s)**.

### Conservative

Predicted: 17:30–18:18 (1050–1098 s).

False skips: None.
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 17:08–18:25 (1028–1105 s).

- Matched label 1 / prediction 1: start error 0 s, end error 0 s.

Rule evidence: cta, offer, sales, url.
### Aggressive

Predicted: 17:25–18:25 (1045–1105 s).

False skips: 17:25–17:30 (1045–1050 s); 18:18–18:25 (1098–1105 s).
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 17:08–18:25 (1028–1105 s).

- Matched label 1 / prediction 1: start error 5 s, end error 7 s.

Rule evidence: cta, offer, sales, url.

### Transcript context

Context 17:17–17:38 (1037–1058 s):

> [17:17–17:25†] cue #149 · C: context · A: context — Being an engineer is the best, because you can make whatever you can dream up. But what's the first step?

> [17:25–17:30†] cue #150 · C: context · A: false skip — How do you get started down that path? Well, I'll tell you exactly how.

> [17:30–17:39†] cue #151 · C: context · A: context — It's called the CrunchLabs Build Box, and it gets delivered right to your doorstep every month, and then we build it together, while I teach you all the juicy physics that make it work.

Context 18:10–18:33 (1090–1113 s):

> [18:06–18:14†] cue #156 · C: context · A: context — So if you wanna embark on this yearlong journey with me, while there's still time to get it before Christmas, just head on over to crunchlabs.com or use the link in the video description,

> [18:14–18:18†] cue #157 · C: context · A: context — where we're giving it away two months free as a holiday special.

> [18:18–18:25†] cue #158 · C: context · A: false skip — (logo chimes)

† End is derived, not a source-supplied speech or promotion boundary.

## Backyard Squirrel Maze 2.0- The Walnut Heist — DTvS9lvRxZ8

[Open video](https://www.youtube.com/watch?v=DTvS9lvRxZ8). Caption type: manual. Observed analysis span: 00:00–16:42 (0–1002 s).

Annotated: **None**.

### Conservative

Predicted: None.

False skips: None.
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: None.

### Aggressive

Predicted: None.

False skips: None.
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: None.


### Transcript context

Reviewed negative; no error in either mode. The highest-scoring rules window is shown for inspection, not as an error or a new label.

Context 00:00–00:30 (0–30 s):

> [00:00–00:06†] cue #0 · C: context · A: context — - This is a bird feeder, and everything you see surrounding me in my yard is an attempt to protect it from four thieving squirrels.

> [00:06–00:15†] cue #1 · C: context · A: context — If they want the birdseed and the lifetime supply of walnuts in this bank vault, they'll first need to pass through my nine-part obstacle course. By design, it's extremely challenging.

> [00:15–00:18†] cue #2 · C: context · A: context — It's meant to test their mental limits and their physical limits.

> [00:18–00:25†] cue #3 · C: context · A: context — I held back no punches, but I have to admit, in hindsight, I once again completely underestimated my adversary.

> [00:25–00:36†] cue #4 · C: context · A: context — And truthfully, I never thought I'd be that crazy guy in the neighborhood obsessing over the squirrels, but they started it first when they would constantly pillage the birdseed from any bird feeder I would put up about a year ago.

† End is derived, not a source-supplied speech or promotion boundary.

## How To Make Friends — I9hJ_Rux9y0

[Open video](https://www.youtube.com/watch?v=I9hJ_Rux9y0). Caption type: generated. Observed analysis span: 00:06–11:55 (6–715 s).

Annotated: **11:23–11:55 (683–715 s)**.

**Review interpretation (not a label edit):** User verified the creator-owned merchandise pitch at 683–715 s on 2026-10-19. This is now a positive annotation; a miss is not a false-positive skip.

### Conservative

Predicted: None.

False skips: None.
Missed: 11:23–11:55 (683–715 s).

Unmatched predictions: 0; unmatched annotations: 1. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 32 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: None.

### Aggressive

Predicted: None.

False skips: None.
Missed: 11:23–11:55 (683–715 s).

Unmatched predictions: 0; unmatched annotations: 1. Missed within candidate spans (refinement/policy loss): 32 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 11:17–11:55 (677–715 s).


### Transcript context

Context 11:15–12:03 (675–723 s):

> [11:12–11:17†] cue #142 · C: context · A: context — are plenty of people who will be so happy  to have YOU in their life. As a good friend.

> [11:17–11:23†] cue #143 · C: context · A: context — Go get to know them!

> [11:23–11:28†] cue #144 · C: missed · A: missed — so we’ve created a few things you  can share with new and old friends!

> [11:28–11:33†] cue #145 · C: missed · A: missed — Two wormhole pins to connect you and your BFF  no matter where you are. If you want to share

> [11:33–11:38†] cue #146 · C: missed · A: missed — something with your entire friend group – get a  little bird pin for each of them. They are all

> [11:38–11:44†] cue #147 · C: missed · A: missed — unique but fit together like pieces of a puzzle.  Or get matching posters to let your friends know

> [11:44–11:50†] cue #148 · C: missed · A: missed — you’re thinking of them. Or just browse all the  sciency things we made for you! If you like videos

> [11:50–11:55†] cue #149 · C: missed · A: missed — like this, getting something from our shop is the  best way to support us! Thank you for watching.

† End is derived, not a source-supplied speech or promotion boundary.

## How The Immune System ACTUALLY Works - IMMUNE — lXfEK8G8CUI

[Open video](https://www.youtube.com/watch?v=lXfEK8G8CUI). Caption type: manual. Observed analysis span: 00:00–10:37 (0–637 s).

Annotated: **09:18–10:45 (558–645 s)**.

### Conservative

Predicted: 09:21–10:19 (561–619 s).

False skips: None.
Missed: 09:18–09:21 (558–561 s); 10:19–10:45 (619–645 s).

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 21 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 8 s.

Candidate spans before refinement: 08:58–10:37 (538–637 s).

- Matched label 1 / prediction 1: start error 3 s, end error 26 s.

Rule evidence: creator_owned, cta, offer.
### Aggressive

Predicted: 09:20–10:23 (560–623 s).

False skips: None.
Missed: 09:18–09:20 (558–560 s); 10:23–10:45 (623–645 s).

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 16 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 8 s.

Candidate spans before refinement: 08:58–10:37 (538–637 s).

- Matched label 1 / prediction 1: start error 2 s, end error 22 s.

Rule evidence: creator_owned, cta, offer.

### Transcript context

Context 09:10–09:29 (550–569 s):

> [09:08–09:15†] cue #133 · C: context · A: context — While for millions of cells, it was a desperate fight for life and death.

> [09:15–09:20†] cue #134 · C: missed · A: missed — But this is just the beginning of the epic story that unfolds inside you every day,

> [09:20–09:21†] cue #135 · C: missed · A: context — and is told in full in

> [09:21–09:25†] cue #136 · C: context · A: context — "Immune: A Journey into the Mysterious System That Keeps You Alive",

> [09:25–09:29†] cue #137 · C: context · A: context — written by Philipp Dettmer, the founder and head writer of Kurzgesagt.

Context 10:11–10:53 (611–653 s):

> [10:11–10:12†] cue #149 · C: context · A: context — The book will be out in six weeks

> [10:12–10:16†] cue #150 · C: context · A: context — and it would mean the world to us and Philipp if you could pre-order it.

> [10:16–10:19†] cue #151 · C: context · A: context — Pre-ordering is super important in the world of books,

> [10:19–10:23†] cue #152 · C: missed · A: context — and in contrast to games, we can guarantee that it's actually finished

> [10:23–10:26†] cue #153 · C: missed · A: missed — and there will be no day one patch.

> [10:26–10:28†] cue #154 · C: missed · A: missed — There's a link in the description.

> [10:28–10:33†] cue #155 · C: missed · A: missed — This is the end of a decade-long personal journey and we'd love to see what you think.

> [10:33–10:37†] cue #156 · C: missed · A: missed — Thank you for watching.

† End is derived, not a source-supplied speech or promotion boundary.

## My Framework Investment Should NOT Have Worked Out — -lErGZZgUbY

[Open video](https://www.youtube.com/watch?v=-lErGZZgUbY). Caption type: generated. Observed analysis span: 00:00–17:42 (0–1062 s).

Annotated: **00:53–01:14 (53–74 s)**.

**Review interpretation (not a label edit):** User retained the 53–74 s annotation on 2026-10-19. Any prediction beyond this remains measured as excess, though the cue ends are derived.

### Conservative

Predicted: 00:50–01:23 (50–83 s).

False skips: 00:50–00:53 (50–53 s); 01:14–01:23 (74–83 s).
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 00:25–01:46 (25–106 s).

- Matched label 1 / prediction 1: start error 3 s, end error 9 s.

Rule evidence: cta, disclosure, sales.
### Aggressive

Predicted: 00:43–01:46 (43–106 s).

False skips: 00:43–00:53 (43–53 s); 01:14–01:46 (74–106 s).
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 00:25–01:46 (25–106 s).

- Matched label 1 / prediction 1: start error 10 s, end error 32 s.

Rule evidence: cta, disclosure, sales.

### Transcript context

Context 00:35–01:01 (35–61 s):

> [00:34–00:43†] cue #4 · C: context · A: context — desktop did we really need framework to develop modular repairable desktops oh wait hold on a second this

> [00:43–00:50†] cue #5 · C: context · A: false skip — is new modular swappable front IO and look at this you can even swap these

> [00:50–00:58†] cue #6 · C: false skip · A: false skip — tiles this one has a segue to our sponsor ug green are you getting the storage warning on your phone again well

> [00:58–01:06†] cue #7 · C: context · A: context — a ug green NZ could be the solution with up to 64 tabt of storage it can store up to 22 million selfies and to keep them

Context 01:06–01:54 (66–114 s):

> [01:06–01:23†] cue #8 · C: false skip · A: false skip — secure it comes with a built-in security manager to protect your data so check out the ugreen nas sync dxp 2800 at the link in the video

> [01:23–01:32†] cue #9 · C: context · A: false skip — description normally for a multi-product video we go from most exciting to less exciting and then save a pretty good one for the the end but I'm equally stoked

> [01:32–01:39†] cue #10 · C: context · A: false skip — for everything here so game of chance

> [01:39–01:46†] cue #11 · C: context · A: false skip — hey nice one of my biggest disappointments at CES was amd's stricks

> [01:46–01:53†] cue #12 · C: context · A: context — Halo processor not the chip itself of course I mean that could be the coolest thing that I've seen out of AMD in years

> [01:53–02:00†] cue #13 · C: context · A: context — and maybe even the coolest PC CPU on the market right now this thing has a massive integrated GP that boasts

† End is derived, not a source-supplied speech or promotion boundary.

## iPhone 16/16 Pro Review: Times Have Changed! — MRtg6A1f2Ko

[Open video](https://www.youtube.com/watch?v=MRtg6A1f2Ko). Caption type: manual. Observed analysis span: 00:00–20:42 (0–1242 s).

Annotated: **00:35–01:44 (35–104 s)**.

### Conservative

Predicted: 00:25–01:30 (25–90 s).

False skips: 00:25–00:35 (25–35 s).
Missed: 01:30–01:44 (90–104 s).

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 14 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 00:00–02:02 (0–122 s).

- Matched label 1 / prediction 1: start error 10 s, end error 14 s.

Rule evidence: creator_owned, cta, offer, sales.
### Aggressive

Predicted: 00:21–01:30 (21–90 s).

False skips: 00:21–00:35 (21–35 s).
Missed: 01:30–01:44 (90–104 s).

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 14 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 00:00–02:02 (0–122 s).

- Matched label 1 / prediction 1: start error 14 s, end error 14 s.

Rule evidence: creator_owned, cta, offer, sales.

### Transcript context

Context 00:13–00:43 (13–43 s):

> [00:09–00:21†] cue #1 · C: context · A: context — (energetic music) (phone vibrating) Profound new intelligence capabilities that will make our platforms even smarter.

> [00:21–00:25†] cue #2 · C: context · A: false skip — - So this is the iPhone 16, and this is the iPhone 16 Pro.

> [00:25–00:34†] cue #3 · C: false skip · A: false skip — Brand new, and I've been testing them for about two weeks now. But you know what I've been doing way longer than two weeks? Working on a new app that we are finally launching.

> [00:34–00:37†] cue #4 · C: false skip · A: false skip — You guys have always been asking me where I get my wallpapers.

> [00:37–00:45†] cue #5 · C: context · A: context — Like, it's frequently the number one suggested search result under my name, has been for years. So now we've put them all in one place. It's called Panels.

Context 01:22–01:52 (82–112 s):

> [01:21–01:29†] cue #13 · C: context · A: context — I don't want to over promise too much, but it's going to be pretty consistently improving over time, which is part of the reason why we're offering a subscription to support it.

> [01:29–01:30†] cue #14 · C: context · A: context — So go pick it up now.

> [01:30–01:35†] cue #15 · C: missed · A: missed — Poke around, find your new favorite wallpaper, your new favorite artist, and lemme know what you think.

> [01:35–01:44†] cue #16 · C: missed · A: missed — It's kind of fun to be on the other side now, on the development side, where now other people are gonna review what we make, which is always exciting.

> [01:44–01:51†] cue #17 · C: context · A: context — Anyway, so the meta with new smartphones these days is a bunch of incremental hardware improvements

> [01:51–01:57†] cue #18 · C: context · A: context — and then a whole bunch of AI features that also are being added on top, which is where the real value is.

† End is derived, not a source-supplied speech or promotion boundary.

## iPhone 16/Pro Impressions: The Great Separation! — 9lx11dy9J30

[Open video](https://www.youtube.com/watch?v=9lx11dy9J30). Caption type: generated. Observed analysis span: 00:04–16:16 (4–976 s).

Annotated: **15:03–16:02 (903–962 s)**.

### Conservative

Predicted: 15:03–15:42 (903–942 s).

False skips: None.
Missed: 15:42–16:02 (942–962 s).

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 20 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 14:32–16:16 (872–976 s).

- Matched label 1 / prediction 1: start error 0 s, end error 20 s.

Rule evidence: cta, disclosure, sales.
### Aggressive

Predicted: 14:55–15:59 (895–959 s).

False skips: 14:55–15:03 (895–903 s).
Missed: 15:59–16:02 (959–962 s).

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 3 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 14:32–16:16 (872–976 s).

- Matched label 1 / prediction 1: start error 8 s, end error 3 s.

Rule evidence: cta, disclosure, sales.

### Transcript context

Context 14:47–15:11 (887–911 s):

> [14:46–14:55†] cue #111 · C: context · A: context — the actual camera app until later this year via a software update that's just weird too there's just a lot of fun weird stuff going on with the shutter

> [14:55–15:03†] cue #112 · C: context · A: false skip — button but now that you've made it this far let me know in the comment section down below what you want to see in those full reviews as you get subscribed to see them and thanks to Anor for

> [15:03–15:10†] cue #113 · C: context · A: context — sponsoring this video their latest mag go lineup is out the six series and there's a couple changes there's a new Slimmer battery bank there's a battery

> [15:10–15:17†] cue #114 · C: context · A: context — bank with an Apple Watch charger a stand with a rotating click head and one of my favorite items a 3in1 foldable charging

Context 15:34–16:10 (934–970 s):

> [15:25–15:35†] cue #116 · C: context · A: context — W wireless charging and temperature control so it keeps your device is protected by keeping charging under 40° C all in this slim 15 mm body and then

> [15:35–15:42†] cue #117 · C: context · A: context — the anchor Mago wireless charging station this thing charges three devices at once an iPhone airpods and your Apple

> [15:42–15:50†] cue #118 · C: missed · A: context — watch all at the same time it supports ch25 wat fast charging and mag safe charging for iPhones and it just folds up into this compact little package fits

> [15:50–15:59†] cue #119 · C: missed · A: context — in your pocket and it can even fold the other way to make it into a stand to activate Apple standby mode while you charge your phone so yeah check these out at the link below and start charging

> [15:59–16:08†] cue #120 · C: missed · A: missed — your devices faster but yeah that's been it thanks for watching this impress video and I'll catch you guys in the next one soon peace

> [16:08–16:16†] cue #121 · C: context · A: context — [Music]

† End is derived, not a source-supplied speech or promotion boundary.

## Why billions of people won't eat pork (or why we don't know) — Sew4rctKghY

[Open video](https://www.youtube.com/watch?v=Sew4rctKghY). Caption type: unknown. Observed analysis span: 00:00–13:13 (0–793 s).

Annotated: **12:04–13:08 (724–788 s)**.

### Conservative

Predicted: 12:04–13:04 (724–784 s).

False skips: None.
Missed: 13:04–13:08 (784–788 s).

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 4 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 11:39–13:13 (699–793 s).

- Matched label 1 / prediction 1: start error 0 s, end error 4 s.

Rule evidence: cta, offer, sales, url.
### Aggressive

Predicted: 11:53–13:13 (713–793 s).

False skips: 11:53–12:04 (713–724 s); 13:08–13:13 (788–793 s).
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 11:39–13:13 (699–793 s).

- Matched label 1 / prediction 1: start error 11 s, end error 5 s.

Rule evidence: cta, offer, sales, url.

### Transcript context

Context 11:45–12:12 (705–732 s):

> [11:39–11:48†] cue #81 · C: context · A: context — And then it became a way for the Muslims, who inherited the Abrahamic tradition, to distinguish themselves from, say, those dirty crusading Franks with their filthy streets.

> [11:48–11:53†] cue #82 · C: context · A: context — It's easy to imagine why the pork taboo spread, and why it persists to the point where my

> [11:53–12:04†] cue #83 · C: context · A: false skip — pork recipes here in this global platform get noticeably fewer views than my other meat recipes. But where the pork taboo first came from, nobody knows for sure.

> [12:04–12:14†] cue #84 · C: context · A: context — What I do know for sure is that people of all religions and dietary codes can make a beautiful and functional website with Squarespace. Whether you want to spread the good word of

Context 12:56–13:21 (776–801 s):

> [12:52–13:04†] cue #89 · C: context · A: context — once you're ready to publish or register a custom domain, you can do us both a favor and save 10% by going to squarespace.com/ragusea. That link of mine is in the description, thank you, Squarespace.

> [13:04–13:13†] cue #90 · C: missed · A: false skip — And, you know, thank you, piggies.

† End is derived, not a source-supplied speech or promotion boundary.

## Ice cream made with a pan, a spoon and a freezer — O7sQBfpQCvU

[Open video](https://www.youtube.com/watch?v=O7sQBfpQCvU). Caption type: manual. Observed analysis span: 00:00–10:17 (0–617 s).

Annotated: **09:25–10:11 (565–611 s)**.

**Review interpretation (not a label edit):** User corrected the end to 611 s on 2026-10-19, where the video returns to the recipe.

### Conservative

Predicted: 09:25–10:11 (565–611 s).

False skips: None.
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 00:00–00:47 (0–47 s); 08:58–10:17 (538–617 s).

- Matched label 1 / prediction 1: start error 0 s, end error 0 s.

Rule evidence: offer, sales, url.
### Aggressive

Predicted: 09:21–10:13 (561–613 s).

False skips: 09:21–09:25 (561–565 s); 10:11–10:13 (611–613 s).
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 00:00–00:47 (0–47 s); 08:58–10:17 (538–617 s).

- Matched label 1 / prediction 1: start error 4 s, end error 2 s.

Rule evidence: offer, sales, url.

### Transcript context

Context 09:13–09:33 (553–573 s):

> [09:10–09:15†] cue #134 · C: context · A: context — and to let your creativity run wild. Chuck whatever you want in your ice cream and see

> [09:15–09:16†] cue #135 · C: context · A: context — what works.

> [09:16–09:21†] cue #136 · C: context · A: context — The still-freeze method offers an evening of good, wholesome fun for kids of all ages.

> [09:21–09:25†] cue #137 · C: context · A: false skip — And unlike most science experiments, you get to eat this at the end. Just as you'll have

> [09:25–09:29†] cue #138 · C: context · A: context — a website at the end of an evening with Squarespace. Seriously, you could easily get your site

> [09:29–09:33†] cue #139 · C: context · A: context — built in-between the stirrings for one batch of ice cream.

Context 10:03–10:21 (603–621 s):

> [10:00–10:04†] cue #145 · C: context · A: context — published, Squarespace hosts the site for you, they can handle any credit card transactions

> [10:04–10:08†] cue #146 · C: context · A: context — you need to do, they can send out your email blasts — anything you could need. It's a

> [10:08–10:11†] cue #147 · C: context · A: context — one-stop shop. Thank you, Squarespace.

> [10:11–10:13†] cue #148 · C: context · A: false skip — Now walk in your kitchen and make some ice cream. You probably have everything you need

> [10:13–10:17†] cue #149 · C: context · A: context — already.

† End is derived, not a source-supplied speech or promotion boundary.

## C in 100 Seconds — U3aXWizDbQ4

[Open video](https://www.youtube.com/watch?v=U3aXWizDbQ4). Caption type: generated. Observed analysis span: 00:00–02:25 (0–145 s).

Annotated: **None**.

### Conservative

Predicted: None.

False skips: None.
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: None.

### Aggressive

Predicted: None.

False skips: None.
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: None.


### Transcript context

Reviewed negative; no error in either mode. The highest-scoring rules window is shown for inspection, not as an error or a new label.

Context 00:15–00:45 (15–45 s):

> [00:15–00:17†] cue #7 · C: context · A: context — tools like vim and git and countless

> [00:17–00:20†] cue #8 · C: context · A: context — others it was created in 1972 by Dennis

> [00:20–00:22†] cue #9 · C: context · A: context — Richie at Bell Labs where it would be

> [00:22–00:24†] cue #10 · C: context · A: context — used to develop the Unix operating

> [00:24–00:25†] cue #11 · C: context · A: context — system it would go on to become the

> [00:25–00:27†] cue #12 · C: context · A: context — mother of all languages inspiring the

> [00:27–00:31†] cue #13 · C: context · A: context — syntax of C++ CP Java JavaScript Pearl

> [00:31–00:34†] cue #14 · C: context · A: context — and PHP just to name a few it compiles

> [00:34–00:35†] cue #15 · C: context · A: context — directly to machine code and requires

> [00:35–00:38†] cue #16 · C: context · A: context — minimal runtime support but is platform

> [00:38–00:39†] cue #17 · C: context · A: context — dependent meaning the executable is

> [00:39–00:42†] cue #18 · C: context · A: context — designed to run on a specific operating

> [00:42–00:43†] cue #19 · C: context · A: context — system it's a highlevel language

> [00:43–00:45†] cue #20 · C: context · A: context — designed for humans yet provides

† End is derived, not a source-supplied speech or promotion boundary.

## Python in 100 Seconds — x7X9w_GIm1s

[Open video](https://www.youtube.com/watch?v=x7X9w_GIm1s). Caption type: generated. Observed analysis span: 00:00–02:23 (0–143 s).

Annotated: **None**.

### Conservative

Predicted: None.

False skips: None.
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: None.

### Aggressive

Predicted: None.

False skips: None.
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: None.


### Transcript context

Reviewed negative; no error in either mode. The highest-scoring rules window is shown for inspection, not as an error or a new label.

Context 00:00–00:30 (0–30 s):

> [00:00–00:02†] cue #0 · C: context · A: context — python a highlevel interpreted

> [00:02–00:04†] cue #1 · C: context · A: context — programming language famous for its

> [00:04–00:06†] cue #2 · C: context · A: context — zen-like code it's arguably the most

> [00:06–00:08†] cue #3 · C: context · A: context — popular language in the world because

> [00:08–00:10†] cue #4 · C: context · A: context — it's easy to learn yet practical for

> [00:10–00:12†] cue #5 · C: context · A: context — serious projects in fact you're watching

> [00:12–00:14†] cue #6 · C: context · A: context — this YouTube video in a python web

> [00:14–00:16†] cue #7 · C: context · A: context — application right now it was created by

> [00:16–00:19†] cue #8 · C: context · A: context — Guido van rossom and released in 1991

> [00:19–00:21†] cue #9 · C: context · A: context — who named it after Monty Python's Flying

> [00:21–00:22†] cue #10 · C: context · A: context — Circus which is why you'll sometimes

> [00:22–00:25†] cue #11 · C: context · A: context — find spaming eggs instead of Foo and bar

> [00:25–00:27†] cue #12 · C: context · A: context — and code samples it's commonly used to

> [00:27–00:29†] cue #13 · C: context · A: context — build serers side applications like web

> [00:29–00:31†] cue #14 · C: context · A: context — apps with the framework and is the

† End is derived, not a source-supplied speech or promotion boundary.

## But what is a neural network? | Deep learning chapter 1 — aircAruvnKk

[Open video](https://www.youtube.com/watch?v=aircAruvnKk). Caption type: unknown. Observed analysis span: 00:04–18:29 (4–1109 s).

Annotated: **16:50–17:03 (1010–1023 s)**.

**Review interpretation (not a label edit):** User verified Patreon promotion at 1010–1023 s and excluded the ordinary subscribe request.

### Conservative

Predicted: 16:50–17:03 (1010–1023 s).

False skips: None.
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 16:33–17:19 (993–1039 s).

- Matched label 1 / prediction 1: start error 0 s, end error 0 s.

Rule evidence: creator_owned, membership.
### Aggressive

Predicted: 16:48–17:07 (1008–1027 s).

False skips: 16:48–16:50 (1008–1010 s); 17:03–17:07 (1023–1027 s).
Missed: None.

Unmatched predictions: 0; unmatched annotations: 0. Missed within candidate spans (refinement/policy loss): 0 s; missed inside observed transcript but outside candidates: 0 s; missed beyond observed analysis span: 0 s.

Candidate spans before refinement: 16:33–17:19 (993–1039 s).

- Matched label 1 / prediction 1: start error 2 s, end error 4 s.

Rule evidence: creator_owned, membership.

### Transcript context

Context 16:40–17:15 (1000–1035 s):

> [16:38–16:41†] cue #257 · C: context · A: context — Maybe more honestly I should say subscribe so that the neural networks

> [16:41–16:44†] cue #258 · C: context · A: context — that underlie YouTube's recommendation algorithm are primed to believe

> [16:44–16:48†] cue #259 · C: context · A: context — that you want to see content from this channel get recommended to you.

> [16:48–16:50†] cue #260 · C: context · A: false skip — Anyway, stay posted for more.

> [16:50–16:54†] cue #261 · C: context · A: context — Thank you very much to everyone supporting these videos on Patreon.

> [16:54–16:57†] cue #262 · C: context · A: context — I've been a little slow to progress in the probability series this summer,

> [16:57–16:59†] cue #263 · C: context · A: context — but I'm jumping back into it after this project,

> [16:59–17:03†] cue #264 · C: context · A: context — so patrons you can look out for updates there.

> [17:03–17:07†] cue #265 · C: context · A: false skip — To close things off here I have with me Lisha Li who did her PhD work on the

> [17:07–17:10†] cue #266 · C: context · A: context — theoretical side of deep learning and who currently works at a venture capital

> [17:10–17:15†] cue #267 · C: context · A: context — firm called Amplify Partners who kindly provided some of the funding for this video.

† End is derived, not a source-supplied speech or promotion boundary.
