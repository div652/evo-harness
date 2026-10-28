# Round 3: analysis of the round-2 stage-harness training runs (campaign 30)

Training runs only: 80 tasks × 3 trials under `harness_stage_r2`. The catalog is `analysis/stages-train-c30/`; `check.py` reports ALL CHECKS PASSED.

- **Outcome:** 74 / 240 all-pass (30.8%). That compares with r1 at 26.7% and C0 at 11.3%.
- **Failing runs:** 166. Of these, 164 are annotated; 170_T0 and 081_T0 have no trace (agent error).
- **New stages:** none. No annotator proposed a new name, and the agent never used `new`.

## First errors across rounds

| Kind | C0 (213) | r1 (176) | r2 (164) |
|---|---|---|---|
| surfaced-not-opened | 39 | 41 | **56** |
| over-inclusion | 18 | 40 | 42 |
| under-inclusion | 5 | 18 | 24 |
| search-miss | 85 | 17 | 14 |
| over-narrow-filter | 1 | 14 | 13 |
| listed-document-not-opened | 2 | 7 | 8 |
| context-overflow | 15 | 34 | **5** |
| partial-listing-as-corpus | 39 | 0 | 0 |

Most common in r2, by kind and stage:

| Kind | Stage | Runs |
|---|---|---|
| surfaced-not-opened | Screen | 41 |
| over-inclusion | Write | 41 |
| under-inclusion | Write | 24 |
| over-narrow-filter | Scan | 12 |
| surfaced-not-opened | List candidate files | 11 |
| search-miss | Scan | 10 |

- **Context overflow nearly gone** (34 → 5), with stage feedback alone. Scan now leads with that warning, and the critic no longer recommends scans that overflow.
- **Remaining failures sit at two stages:**
  - **Screen:** found but not opened, 41;
  - **Write:** over-inclusion 41 and under-inclusion 24.

**Where passing and failing runs split** (17 mixed tasks):

| Stage | Failing runs |
|---|---|
| Write | 11 |
| Screen | 6 |
| List candidate files | 5 |
| Scan | 3 |
| Search within | 1 |
| Check or revise | 1 |

## Critic (first errors)

| | r1 | r2 |
|---|---|---|
| flagged, ignored | 74 | **98** |
| flagged, partly fixed | 48 | 24 |
| not flagged | 21 | 27 |
| review pushed toward the error | 1 | **10** |
| no review | 33 | 5 |
| flags that were specific / generic | 58 / 56 | **75 / 50** |

- **Specific flags rose** (58 → 75) after the "cite the evidence" rule, but the agent now ignores more flags (74 → 98), and fixes even partly fewer (48 → 24).
- **"Review-endorsed" rose to 10.** The batch reports give these examples:
  - a review told the agent to rank candidates by matter number (240_T0);
  - a review told it to present an out-of-practice deal as a precedent (053_T0);
  - reviews swung the answer narrow, then wide, then narrow again (011_T0);
  - reviews kept a draft's over-inclusion (151, 072, 104, 111_T2, 047_T1, 149_T2).
- **The critic still helps sometimes:** in 3 passing runs, acting on a review fixed the answer (093_T0, 198_T0, 198_T2).

## Label check (new in r2)

| | Stages |
|---|---|
| Followed | 9 |
| Ignored | **392** |
| Not applicable | 2,816 |

A note at `stage_start` did not change how the agent labelled its stages. The ignored cases are mostly:
- folder listings declared as "List files in the document store (attempt 2)";
- screening declared as "Read documents picked from the file listing" or "Read in depth".

## What the round suggests for stage feedback (not yet applied)

1. **Advisory feedback reaches its limit at Screen and Write.** The critic names the problem specifically more often, and the agent moves on anyway. The open question for the hypothesis is whether *steering* (requiring the agent to deal with a specific flag before moving on) works where *advice* doesn't.
2. **Wrong labels can't be fixed by a note.** 392 were ignored. Options:
   - classify the stage from the calls (the stage-fit checker already does this) and attach the right stage's patterns automatically;
   - accept the agent's labels and treat confusion as data.
3. **Critic-induced errors (10) need a guard.** A recommendation that changes the answer set (add or drop a matter, rank by number) could be required to cite a document read in the run.
