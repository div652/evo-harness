# Round 4: analysis of the round-3 stage-harness training runs (campaign 31), and the proposed `harness_stage_r4`

Training runs only: 80 tasks × 3 trials under `harness_stage_r3`. The catalog is `analysis/stages-train-c31/`; `check.py` reports ALL CHECKS PASSED.

## Outcome

| | All-pass | Criterion pass rate | Tasks passing 0/1/2/3 of 3 runs |
|---|---|---|---|
| C0 | 11.3% | 0.394 | |
| r1 | 26.7% | 0.631 | |
| r2 | 30.8% | 0.679 | |
| **r3** | **29.6%** (71/240) | 0.674 | 47 / 9 / 10 / 14 |

r3 vs r2: −1.3 points, 95% CI [−5.8, +3.3]. The round-3 changes (policy layer, review against the classified stage, critic suggesting new stages) left the score unchanged.

## First errors (169 failing runs)

| Kind | r1 | r2 | r3 |
|---|---|---|---|
| surfaced-not-opened | 41 | 56 | **64** |
| over-inclusion | 40 | 42 | 36 |
| under-inclusion | 18 | 24 | 15 |
| search-miss | 17 | 14 | 14 |
| listed-document-not-opened | 7 | 8 | **13** |
| over-narrow-filter | 14 | 13 | 11 |
| context-overflow | 34 | 5 | 9 |

Most common by kind and stage:

| Kind | Stage | Runs |
|---|---|---|
| surfaced-not-opened | Screen | 50 |
| over-inclusion | Write | 36 |
| under-inclusion | Write | 14 |
| search-miss | Scan | 12 |
| listed-document-not-opened | Screen | 11 |
| surfaced-not-opened | List candidate files | 9 |

The build reported three regressions (kinds that had become rare and came back):
- context overflow at Scan;
- over-narrow-filter at Search file names;
- under-inclusion at Check or revise.

## Critic on first errors

| Outcome | Runs |
|---|---|
| flagged, ignored | 81 |
| flagged, partly fixed | 34 |
| not flagged | 34 |
| review-endorsed | 12 |
| no review | 8 |

Specific flags that were ignored, against reviews that pushed toward the error, in the latest round (first and later errors):

| Stage | Specific flags ignored | Review-endorsed |
|---|---|---|
| Write | 32 | 10 |
| Screen | 21 | 3 |
| Scan | 15 (13 after the merge relabel) | 0 |

## Exploration: agent-defined stages

- **Use:** 645 spans in 155 runs. Most copy the critic's "suggested new step" name word for word, so exploration is driven by the critic.
- **Mapping:** almost all map to existing stages, mostly Scan, Screen, Check and Read in depth.
- **Promoted under the round-4 rule** (grouped by what the calls do, ≥2 different runs, ≥1 passing, no existing stage fits): **"Tabulate candidate matters from saved results"**. It works only on saved hit files (per-matter counts, rankings, tables, coverage checks), with no extraction, reading or listing. It occurs in 142 spans in 100 runs, 26 of them passing. Earlier rounds had labelled this work as Scan.
- **Not promoted (single run):** "Rank candidate matters without tool calls" and "Write a working notes file", both mapped to the new stage.

## Label notes

| Note | Followed | Ignored |
|---|---|---|
| "Check the label" at stage start | 4 | 263 |
| "Label: looked like X" at stage end | 85 | 140 |

The end note works better than the start note. But "followed" often just means the agent declared the suggested stage next.

## Changes in `harness_stage_r4` (stage-level only)

| # | Change | Evidence |
|---|---|---|
| 1 | Reference rebuilt from rounds 1–4. Policy eligibility counts pooled earlier rounds (decision #28). The new stage "Tabulate candidate matters from saved results" is in the stage list, the `stage_start` enum and the prompt (#29) | Merge above |
| 2 | **Steering gate at Scan and Screen.** If the review at a gated stage gives specific flags and a verdict of "partly" or "no", the next `stage_start` to a *different* stage is refused, unless it passes `override_reason` explaining, flag by flag, why each does not apply. Reopening the same stage clears the gate. Overrides and refusals are logged. Gated stages are chosen by the build script from the latest round: ≥5 specific flags ignored, and review-endorsed ≤25% of that | Screen: 21 ignored vs 3 endorsed. Scan: 13 vs 0. **Write is not gated**: 32 ignored vs 10 endorsed, so the critic misleads too often there to enforce it |

Unchanged from r3: policy layer, review against the classified stage, the critic suggesting new stages, and all guard rules.

The Write split stays out (decision #27): it was not re-checked this round because the decision step did not appear as an agent-defined stage.
