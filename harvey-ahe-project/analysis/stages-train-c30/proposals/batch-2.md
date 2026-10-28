# Batch 2 proposals (tasks 035 052 056 114 137 154 195 206)

## NEW names

None. Every stage, tag, hindsight value and error kind is from taxonomy.md.

| kind | name | definition | example | why no existing name fits |
|---|---|---|---|---|

## Issues

- label_check counts over 8 tasks: followed 0, ignored 35. No agent closed a stage because of a "Check the label" note. The only stage_start → stage_end pairs with no work in between are refused stage_starts ("still open"), not switches.
- What the `ignored` cases were:
  - "List files in the document store (attempt 2)" spans that list or count matter folders; the note had named "List matter folders" (035_T0, 052_T1, 052_T2, 056_T0, 137_T0, 154_T1, 154_T2).
  - Declared "Read documents picked from the file listing" spans holding first reads of candidates from searches; the note had suggested "Screen candidate matters by reading documents" (052_T1, 114_T1, 114_T2, 137_T0, 137_T2, 154_T0, 154_T1, 154_T2, 195_T2, 206_T0, 206_T2).
  - Declared read or search-within spans that ran scans the note had named (052_T2 [48]-[59], 056_T0 [89]-[96], 137_T2 [81]-[86], 206_T1 [91]-[98]).
- `none` was kept where the declared label fit the main work even if the note's suggestion matched a minor part. Examples: 056_T0 [56]-[77], a deep read with a few comparison reads of other candidates, and 137_T1 [91]-[113]. `ignored` on a split span is put on the part where the suggested work was done (035_T0 [54]-[61], 154_T1 [82]-[92], 195_T2 [91]-[102]). Other splits: 137_T0 none; 206_T0 [24]-[27] / [28]-[31] (path search, then a timed-out text scan in the same declared span).
- Path-check scripts that open `response.md` from the wrong folder (Python FileNotFoundError traceback) are tagged `script error` in this batch. Batch 1 tagged the same pattern `file not found`, so the merge should pick one.
- Where the critic pushed the wrong way:
  - 035_T1 is coded `review-endorsed`. The write review suggested that a secondary-offering matter's earlier offering "may be wrongly dropped". The agent added it, removed it after the next review, then re-added it after a further review called the removal "narrowing".
  - 154_T0 and 154_T2 show the same push but are coded differently. In both, the write review questioned whether the correct (de-SPAC) deal counts, and the check stage then added an earlier conventional deal as an alternative. The first error predates that review, so it is coded `flagged-fixed-partly` (T0) and `not-flagged` (T2), with the push described in `critic_note`.
- Generic unopened-matter warnings ("about 60 surfaced matters were never opened", with examples that do not include the needed matter) are coded `flagged-ignored` + "(generic flag)" for surfaced-not-opened errors (052, 114, 195_T1). 052_T2 is `not-flagged` because its screening review discussed only how deeply opened matters were read.
- 195: the same missed matter has a different first-error kind in different runs. In T0 and T2 a narrower agreement-name pattern written after a broad search dropped it, so the kind is over-narrow-filter. In T1 the agent widened again and saw its agreement listed, so the first error is surfaced-not-opened at screening, with the later filtered scan described in `why`.
- 154: all three runs name the correct deal but list earlier closed earnout deals as cross-checks or alternatives. These are coded over-inclusion, following the merge note for comparators described as meeting the request (151_T2). The judge counted them, but the agent may have meant them only as context.
- Harness "Stage check" notices (052_T2 [53], [55]; 137_T0 [86]; 206_T0 [29]; 206_T1 [94], [96]) are warnings, not refusals, so they get no tag; they are mentioned in notes.
