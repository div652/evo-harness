# Replay results: first_error

Items with every arm judged: 237

| Arm | steps | commits yes | partly | no | mean score | moves: reopen / new / other stage |
|---|---|---|---|---|---|---|
| original | 237 | 15% | 40% | 45% | 0.350 | 21% / 52% / 24% |
| control_nosum | 474 | 23% | 40% | 37% | 0.432 | 16% / 71% / 12% |
| control | 474 | 21% | 39% | 40% | 0.403 | 16% / 70% / 12% |
| wrapped | 474 | 24% | 43% | 33% | 0.454 | 20% / 68% / 10% |

## Paired differences (mean score per item, 95% bootstrap CI over items)

| Comparison | difference | CI |
|---|---|---|
| original − control | -0.053 | [-0.093, -0.014] |
| control_nosum − control | +0.030 | [-0.001, +0.060] |
| wrapped − control | +0.051 | [+0.020, +0.081] |

## By reviewer outcome (annotation)

| Group | items | original | control_nosum | control | wrapped |
|---|---|---|---|---|---|
| flagged-ignored | 179 | 0.26 | 0.37 | 0.34 | 0.39 |
| flagged-fixed-partly | 58 | 0.63 | 0.62 | 0.59 | 0.66 |

## By first error kind

| Group | items | original | control_nosum | control | wrapped |
|---|---|---|---|---|---|
| surfaced-not-opened | 114 | 0.38 | 0.46 | 0.40 | 0.46 |
| over-inclusion | 40 | 0.40 | 0.44 | 0.42 | 0.45 |
| search-miss | 26 | 0.25 | 0.45 | 0.46 | 0.44 |
| over-narrow-filter | 24 | 0.25 | 0.39 | 0.46 | 0.45 |
| under-inclusion | 21 | 0.29 | 0.30 | 0.24 | 0.36 |

## By run outcome

| Group | items | original | control_nosum | control | wrapped |
|---|---|---|---|---|---|
| failed | 237 | 0.35 | 0.43 | 0.40 | 0.45 |

