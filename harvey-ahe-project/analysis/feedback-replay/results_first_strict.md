# Replay results: first_strict

Items with every arm judged: 477

| Arm | steps | commits yes | partly | no | mean score | moves: reopen / new / other stage |
|---|---|---|---|---|---|---|
| original | 477 | 65% | 29% | 6% | 0.797 | 69% / 28% / 3% |
| wrapped | 954 | 64% | 32% | 4% | 0.803 | 63% / 36% / 1% |

## Paired differences (mean score per item, 95% bootstrap CI over items)

| Comparison | difference | CI |
|---|---|---|
| wrapped − original | +0.006 | [-0.015, +0.027] |

## By whether the agent eventually followed it in the recorded run

| Group | items | original | wrapped |
|---|---|---|---|
| yes | 313 | 0.91 | 0.89 |
| partly | 146 | 0.63 | 0.67 |
| no | 18 | 0.14 | 0.43 |

## By stage

| Group | items | original | wrapped |
|---|---|---|---|
| List files in the document store | 248 | 0.91 | 0.89 |
| Search file names for request keywords | 138 | 0.71 | 0.74 |
| Scan document text with an extraction script | 80 | 0.65 | 0.69 |

## By review number in the run

| Group | items | original | wrapped |
|---|---|---|---|
| 1st review | 238 | 0.92 | 0.90 |
| 2nd-3rd | 205 | 0.67 | 0.70 |
| 4th+ | 34 | 0.71 | 0.75 |

## By run outcome

| Group | items | original | wrapped |
|---|---|---|---|
| failed | 332 | 0.79 | 0.80 |
| passed | 145 | 0.81 | 0.81 |

