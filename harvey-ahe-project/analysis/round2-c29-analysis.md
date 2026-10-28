# Round 2: analysis of the stage-harness training runs (campaign 29) and the proposed harness `harness_stage_r2`

**Scope.** Training runs only: 80 tasks × 3 trials, under `harness_stage` (round 1). Annotation follows `docs/stage-protocol-harness.md` (sections A2, A8 and A9) plus `analysis/stages-train-c29/BRIEF.md`. The goal is to test the hypothesis that stage-level grouping, per-stage error statistics, and stage feedback and steering improve the harness. Only stage-level changes are made.

## 1. Outcome

| | Base C0 (campaign 23) | Stage harness r1 (campaign 29) |
|---|---|---|
| All-pass | 27 / 240 (11.3%) | **64 / 240 (26.7%)**: +15.4 points, 95% CI [+8.3, +22.5] |
| Criterion pass rate | 0.394 | **0.631** |
| Tasks with at least one passing run | 16 | **31** |

Of the 80 tasks, 21 have mixed outcomes, 10 pass in all three runs, and 49 fail in all three.

## 2. Where failing runs first went wrong: round 1 vs round 2

| First-error kind | C0 (213 failing runs) | Stage r1 (176 failing runs) |
|---|---|---|
| search-miss | 85 | **17** |
| partial-listing-as-corpus | 39 | **0** |
| surfaced-not-opened | 39 | 41 |
| over-inclusion | 18 | **40** |
| context-overflow | 15 | **34** |
| under-inclusion | 5 | 18 |
| over-narrow-filter | 1 | 14 |
| listed-document-not-opened | 2 | 7 |

- **Fixed by the stage harness:**
  - treating the capped listing as the whole store (39 → 0);
  - most search misses (85 → 17).
- **Where failures moved:**
  - judgement at **Write the response**: over-inclusion 39 and under-inclusion 18 as first errors;
  - **context overflow at Scan document text** (33), always before any review (`no-review`);
  - over-narrow scan filters (14).

Most common first error by stage (round 2):

| Stage | First error | Runs |
|---|---|---|
| Write | over-inclusion | 39 |
| Scan | context-overflow | 33 |
| Screen | surfaced-not-opened | 24 |
| Write | under-inclusion | 18 |
| List candidate files | surfaced-not-opened | 12 |
| Scan | search-miss | 12 |
| Scan | over-narrow-filter | 8 |

## 3. Where passing and failing runs split (21 mixed tasks, 29 failing runs)

| Split stage | Runs |
|---|---|
| Write the response | 14 |
| Scan document text | 6 |
| Search within a candidate matter's files | 3 |
| List files in candidate matters | 2 |
| Screen | 2 |
| other | 2 |

By kind:
- over-inclusion 9
- context-overflow 7
- surfaced-not-opened 5
- under-inclusion 3

Clean contrasts: in **056** and **082**, two runs got the same *specific* critic flag at Write. The run that acted on it passed; the run that ignored it failed.

Stages present more often in passing runs:

| Stage | Passing runs | Failing runs |
|---|---|---|
| List files in candidate matters | 70% | 44% |
| Read a chosen matter's documents in depth | 53% | 42% |
| Search within a candidate matter's files | 30% | 23% |

## 4. Did the stage feedback work? (critic field on the 176 first errors)

| Critic outcome | First errors |
|---|---|
| flagged, agent moved on (`flagged-ignored`) | 74 |
| flagged, partly fixed | 48 |
| run ended before any review (`no-review`, all context overflows) | 33 |
| not flagged | 21 |
| review pushed toward the error (`review-endorsed`) | 1 coded (230_T0) |

- **Half of the flags were generic stock warnings.** Of the 114 flagged first errors, 56 were flagged only generically (e.g. "~60 surfaced matters unopened") and 58 specifically. Annotators reported that almost every write-stage review carries the same stock flags.
- **Critic verdicts barely separate outcomes:**
  - "partly" is given in 83% of reviews, in both passing and failing runs;
  - the verdict on the last stage before finish is "partly" for 59 of 64 passing and 142 of 176 failing runs.
- **The critic sometimes steered into errors.** The batch notes list:
  - 7 overflows on store-wide scans that the previous review had recommended (batch 5);
  - 223_T0, where reviews pushed a broader population;
  - 195_T0, where the critic's advice led the agent to delete a needed row;
  - 230_T0.
- **The agent said "goal not reached" in only 83 of 2,128 stage ends.**

## 5. Stage labels

**523 of 2,533 declared stage spans (21%) were mislabelled** by the agent. When the label is wrong, the stage feedback and the critic's checklist are for the wrong stage. The most common confusions:

| Declared | Actually | Spans |
|---|---|---|
| List files in the document store (reopened) | List matter folders | 144 |
| Read a chosen matter's documents in depth | Screen candidate matters by reading documents | 89 |
| Search file contents for request keywords | Scan document text with an extraction script | 35 |
| List files in the document store | Search file names for request keywords | 31 |
| Search within a candidate matter's files | Scan document text with an extraction script | 23 |

The 89 "Read in depth" spans that were really screening matter most. Screening is where "surfaced-not-opened", the top error, lives, but those runs saw the in-depth stage's warnings instead.

**New stages:** none. No annotator proposed a new stage, and the agent never used `new` in 240 runs. New vocabulary: one error kind (`missing-detail`) and one critic value (`review-endorsed`).

## 6. Proposed harness: `harness_stage_r2` (stage-level changes only)

| # | Change | Evidence (round 2) |
|---|---|---|
| 1 | **Stage reference regenerated** by `build_stage_reference.py` from both rounds' training catalogs (top ≤4 error kinds per stage, each in ≥2 runs). | Errors moved from search to Write and Scan (section 2). The reference now leads Scan with context-overflow (48 runs over both rounds) and Write with over- and under-inclusion. |
| 2 | **Stage-confusion check.** Each stage lists the stages it is most often mistaken for (≥5 relabels): in the prompt as "Not for: … That is **X**", and in the `stage_start` result as "Check the label: … close this stage and start that one". Generated from the annotated relabels. | 21% of declared spans mislabelled (section 5). |
| 3 | **Critic must cite evidence.** A failure pattern may be flagged only with the specific call, result, matter or document that shows it; no generic warnings. The hand-written list of specific failure types in the critic's system prompt was removed: the checklist now comes only from the stage reference. | 56 of 114 flagged first errors were stock flags; 74 flags were ignored. |
| 4 | **Critic's recommendation must not lead into another stage's known failures.** The critic now also receives every other stage's failure patterns. | Reviews recommended the scans that then overflowed (7 runs), and pushed the decisions behind 223_T0 and 230_T0. |

Considered and **not** applied:
- **A general output cap on bash/grep:** a general harness change, outside the hypothesis.
- **Forcing a reopen when the critic says "no":** the critic's verdicts barely separate passing from failing runs (section 4), so forcing on them is not supported yet.

Unchanged from round 1: the 14 declarable stages and `new`; the guard rules; failure patterns shown at start and end; the surfaced-not-opened list, now shown at 4 stages.

## Files

| Path (under `harvey-ahe-project/`) | What |
|---|---|
| `analysis/stages-train-c29/` | Round-2 catalog: logs, 80 annotated tasks, taxonomy with critic values, proposals, `check.py` (ALL CHECKS PASSED) |
| `harness_stage_r2/` | Proposed harness |
| `scripts/stage/build_stage_reference.py` | Now takes several catalogs, and writes confusion notes and the stage enum |
| `scripts/stage/stage_stats.py` | Run-level stage and critic statistics |
