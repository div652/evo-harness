# Batch 3 proposals (tasks 048 056 058 121 151 194 198 210)

## NEW names

| kind | name | definition | example | why no existing name fits |
|---|---|---|---|---|
| stage | NEW: Tabulate findings across candidate matters | A script writes and prints a hand-made table of findings the agent has already read (e.g. each candidate matter's latest dated document and status). It does not touch the document store and computes nothing. Agent's name: "Cross-matter recency table", which the previous review had suggested. Only occurrence: 056_T0 [97]-[102], a passing run (2/2). | 056_T0 [97]-[102] | "Calculate figures for the answer" computes values and nothing is computed here; "Write the response" writes the deliverable, and this is a scratch table. If the merge prefers to avoid a single-use stage, "Calculate figures for the answer" is the closest fit. |

No other NEW names. 61 stage rows in this batch carry `agent_new` (declared "new" stage attempts, some split) (048_T1/T2, 056_T0/T1, 121_T1/T2, 151_T0-T2, 194_T1, 198_T0-T2, 210_T1/T2). All except the one above map to existing stages. Each has a note starting "declared: new: …". Where they went:
- Scan document text with an extraction script: most of them, including batched or background store-wide scans, rebuilding a candidate pool from saved scan output, and ranking or persisting scan hits per matter.
- Screen candidate matters by reading documents: verifying unresolved candidates, and reading the closing documents of each candidate.
- Check or revise the response: work after writing, i.e. re-verifying cited sources, recomputing statistics, confirming direction or amounts, and recounting totals.
- Calculate figures for the answer: per-client tally reconciliation (210_T1).
- Search file names: classifying matters by practice area, and matching file-name hits to the full listing.
- Split spans: 121_T1, 198_T1 and 210_T2, where one declared span held two intents.

## Issues

- **label_check is one field, but a stage can carry two notes.** A stage can get both a "Check the label" note at its start and a "Label: these calls looked like X" note at its end, and the two can have different outcomes. Examples: 056_T0 [8]-[13], 058_T1 [75]-[80], 048_T2 [8]-[13], 198_T0 [14]-[19], 210_T0 [8]-[13]. In each case the start note was ignored and the end note was followed. Annotators set the field to "ignored" and described the follow in the note text. 048_T2 instead put "followed" on the next stage. The schema needs one convention, or two fields (`label_check_start`, `label_check_end`).
- **End-of-stage label notes with no later work of the named kind fit neither value.** They were coded `none`. This happened mostly on the last check stage before finish: 056_T0 [138], 056_T2 [117], 058_T1 [13] and [135], 121_T0 [99], 121_T1 [146], 151_T0/T1, 194_T0 [109], 198_T1 [19], 198_T2 [101], 210_T0 [92], 210_T1 [109].
- **The end-of-stage classifier is often wrong.**
  - It called re-reading cited sources after writing "Read documents picked from the file listing" (056, 048_T0 [81]-[88], 048_T2 [126]-[137]).
  - It called a file-name regex inventory "Scan" (198_T0 [19]).
  - It called per-prefix folder counts "List matter folders" (210), where round 3 used "Calculate figures for the answer".
  - It called in-matter snippet scripts over the candidate pool "Scan" (194_T0, 194_T2). These were kept as "Search within a candidate matter's files", following the round-2 precedent.
  - Following rule 2, a kept label was still counted `ignored` even when the note was wrong.
- **Suggestions that were neither taken nor declined.** At 121_T1 [101] the agent took neither the label note's suggestion nor its old label; it started a reviewer-suggested new stage instead. This was coded `ignored`.
- **Empty stages.** Some declared stages contain only their own stage_start and stage_end: 121_T0 [14]-[17] and 151_T1 [77]-[80]. They were kept as their own rows and labelled by the stated goal.
- **Reviewer-suggested new steps are often taken up, but never add a new kind of work.** "Reviewer suggests a new step" was taken up in 048_T1, 048_T2, 056_T0, 121_T1/T2 (7 times) and 194_T1, and declined in 058_T1 [121], 194_T0 and 194_T1. Every one it took up turned out to be an existing stage. Most often it was a scan reorganisation or a post-write check.
- **Coverage checks recur as declared steps.** Comparing search or scan hits with the full matter-folder list recurs: 056_T0/T1 "coverage", 198_T2, 210_T2, 048_T2. It was split into or mapped onto existing stages (List matter folders + List files in candidate matters, or Scan). A future round could consider a stage such as "Check search coverage against the matter-folder list".
- **Reviews pushed toward the error in 151.** All three 151 runs are coded `review-endorsed`. The reviews asked for every other candidate to be listed with its date, and each run then wrote earlier executed deals as having the adjustment (over-inclusion on the precision criterion).
- **Unlabelled timestamp listing.** 151_T0/T1 [8]-[13] is a script that prints every file of every matter with per-matter counts (about 550K characters). It is labelled "List files in the document store". T1 had declared it, and the end note named it, "List matter folders".
- **Same failure as round 3.** 058_T0 and T2 overflowed the context on an uncapped store-wide snippet scan (about 149M and 69M characters).
- **Tag precedent.** Path-check scripts that fail because they run outside the output folder are tagged `script error`, as in round 3 (048).
