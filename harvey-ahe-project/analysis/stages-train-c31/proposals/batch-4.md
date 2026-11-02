# Batch 4 proposals (tasks 011 059 061 080 125 154 195 199)

## NEW names

None. No stage, tag, hindsight value or error kind in this batch needed a `NEW:` name.

33 stage rows carry `agent_new` (stages declared "new"). Every one maps to an existing stage, and each note starts with "declared: new: …":

| Existing stage | Agent's new-stage names (runs, outcome) |
|---|---|
| Scan document text with an extraction script | "Full-text scan for waterfall terms", "Batched full-store waterfall scan" (061_T0, pass); "Search document text for patent and expert terms", "Sharded background text scan", "Finish and verify shard scan", "Aggregate shard hit index", "Patent-specific term scan across all matters" (080_T2, pass); "Rerun extraction scan in background with coverage check" (199_T1, pass); "Rerun full-store fee scan" (059_T0, fail); "Scan all 219 matters' text for damages pleadings" x2 (125_T0, fail); "Aggregate scan results into full candidate pool" x2 (154_T1, fail) |
| Search file names for request keywords | "Broad path and text search for fund waterfall matters (attempt 2)" (061_T2, pass); "List files in remaining surfaced matters" (080_T1, 080_T2, pass); "List files for remaining surfaced matters" (199_T1, pass); "Classify all 219 matters by metadata" (125_T0, fail) |
| List files in candidate matters | "List files in remaining surfaced matters" (059_T0, fail) |
| Screen candidate matters by reading documents | "Read governing documents of waterfall hit matters" (061_T2, pass) |
| Read a chosen matter's documents in depth | "Verify waterfall clauses in operative fund documents" (061_T2, pass) |
| Check or revise the response | "Targeted section verification" (061_T2, pass); "Fact-check response claims against source text" (059_T0, fail); six post-write steps in 059_T1 (fail): "Spot-check key assertions against sources", "Finalize source-check edits", "Final consistency read", "Clarify operative versus non-operative precedents", "Separate confirmed and status-qualified references", "Final tiered-response verification"; "Row-by-row reconciliation" x3 and "Folder-wide damages and client check on near-misses" (125_T2, fail) |

Most of these were steps the reviewer had suggested ("Reviewer suggests a new step"). Every suggested step the agent took up was an existing kind of work, mostly a scan reorganisation, a file-name sweep over "remaining" matters, or a post-write check.

## Issues

- **Label-check counts.**
  - Start-of-stage "Check the label" notes: followed 0, ignored 16, none 331.
  - End-of-stage "Label: these calls looked like X" notes (`label_check_end`): followed 12, ignored 15, none 320.
  - Following the coordinator's update, both fields are set on every stage.
  - As in batch 3, an end note is coded `none` when that kind of work never recurs. It is coded `ignored` when the next stage doing that work was declared under the old label or a third label (e.g. 061_T2 [143], 195_T2 [148]).
- **Agent stage names containing task words.** Some new-stage names contain words that check.py rejects as task content ("fund", "waterfall"; 061_T0, 061_T2). Their notes write those words as "…" (e.g. "declared: new: Full-text scan for … terms"). `agent_new` keeps the exact name.
- **Same agent name, different function.** "List files in remaining surfaced matters" covers two kinds of work:
  - a store-wide file-name filter: 080_T1, 080_T2 and 199_T1, labelled Search file names for request keywords;
  - printing saved hit paths for a few chosen matters: 059_T0, labelled List files in candidate matters.
  The labels follow the function, as rule 3 requires, so one agent name maps to two stages.
- **The harness note "Matters that appeared in your search results but none … opened".**
  - The note usually lists about 60 matters. When a needed matter was only somewhere in that list, the critic value is `(generic flag)`.
  - `(specific flag)` is used only when a reviewer flag named the matter, or its number range or series: 080_T0 cites the series at [93], 125_T0 the range at [134], 195_T0 the series at [56], and 011_T1 names the matter at [49]/[72].
  - This is a judgement call. A future round may want an explicit rule.
- **review-endorsed.** Used twice:
  - 154_T1: the review listed only later-numbered unopened matters, and the agent screened those instead of the needed lower-numbered deal.
  - 125_T2: the review advised counting only matters where the client pleads damages, and the agent then removed a needed matter in a post-write reconciliation.
- **Matter number used as a proxy for recency (154, all runs).** All three runs chose which earnout deals to read by highest matter number and never opened the most recently closed deal. Reviews reinforced the heuristic (154_T0 [64] called higher-numbered series "newer"). No tag records this.
- **An edit that removed a correct citation (125_T0 [164]).** The removed document was a needed proof pleading the agent had never opened. It is coded `listed-document-not-opened` on the check stage, because the edit introduced the error. No kind describes "edit removed a correct item".
- **Same dominant failure across tasks.**
  - In 011, 059, 080_T0, 125, 154 and 195, the store-wide scans surfaced every needed matter, but the agent read a hand-picked or number-ranked subset.
  - The first error is `surfaced-not-opened` at the first reading or selection stage after the scan.
  - Reviews flagged "dozens of unopened matters" in nearly every stage, and the agents answered by re-scanning or re-listing rather than opening.
- **Splits and empty stages.**
  - Split spans: 059_T1 [14]-[23] (scan timeouts, then a path grep) and 061_T1 [78]-[89] (a scan, then screening reads).
  - Empty declared stage: 080_T0 [100]-[103], kept as its own row.
- **Stage-protocol "Stage check" notes.** Some tool results carry the text "[Stage protocol] Stage check: this call looks like …" (080_T1 [33]/[41], 154_T2 [38]/[52]/[70]/[72]). The briefs do not mention these notes. They are not tagged and are named in the notes only where relevant.
- **Listings declared "List matter folders" that print every file path.** These are labelled List files in the document store (154_T1 [8]-[13], 199_T2 [8]-[13]), following batch 3's 151 precedent.
- **Hindsight for the first glob.** Per merge convention 2, a first whole-store glob that shows a rubric matter's files gets `target surfaced` (125, 195).
