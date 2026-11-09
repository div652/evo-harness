# Reviewer swap on the first-error items

Items with every arm judged: 237

Scores: yes = 1, partly = 0.5, no = 0, averaged over an item's samples.

| Arm | steps | review raises the problem: yes / partly / no | score | next step commits to fixing it: yes / partly / no | score |
|---|---|---|---|---|---|
| original | 237 | 62% / 38% / 0% | 0.808 | 14% / 41% / 45% | 0.344 |
| control_nosum | 474 | 62% / 38% / 1% | 0.805 | 21% / 42% / 37% | 0.419 |
| reviewer_sonnet | 474 | 57% / 42% / 1% | 0.777 | 22% / 44% / 34% | 0.439 |
| reviewer_luna | 474 | 38% / 57% / 5% | 0.664 | 12% / 42% / 46% | 0.334 |

## Paired differences (95% bootstrap CI over items)

| Comparison | review score | step score |
|---|---|---|
| reviewer_luna − reviewer_sonnet | -0.114 [-0.145, -0.084] | -0.104 [-0.143, -0.066] |
| reviewer_sonnet − control_nosum | -0.027 [-0.049, -0.006] | +0.020 [-0.017, +0.057] |
| reviewer_luna − control_nosum | -0.141 [-0.174, -0.110] | -0.084 [-0.130, -0.040] |

## Next-step commitment when the review did / did not raise the problem

| Arm | review raised it (yes) | steps | commit score | review did not (no) | steps | commit score |
|---|---|---|---|---|---|---|
| original | | 146 | 0.39 | | 0 | – |
| control_nosum | | 292 | 0.50 | | 3 | 0.00 |
| reviewer_sonnet | | 269 | 0.55 | | 6 | 0.00 |
| reviewer_luna | | 179 | 0.48 | | 24 | 0.04 |
