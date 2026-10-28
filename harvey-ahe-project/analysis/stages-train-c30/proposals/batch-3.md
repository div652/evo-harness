# Batch 3 proposals (tasks 053 061 066 121 140 155 209 210)

## NEW names

None. Every stage, tag, hindsight value and error kind in this batch maps to an existing taxonomy row.

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|

## Issues

- **label_check counts.** 1 followed, 38 ignored over 24 runs. The one "followed" is 061_T0 [20]-[49]: an empty "Search file contents" span closed on the label note is merged into the scan row that follows, and that row is marked followed. Most "ignored" rows come from four patterns:
  - "List files in the document store (attempt 2/3)" used for a folder enumeration (now "List matter folders");
  - "Read documents picked from the file listing" used for screening reads chosen from search or scan output (now "Screen candidate matters by reading documents");
  - "Write the response (attempt 2/3)" used for edits (now "Check or revise the response", 121_T2 [136]-[167]);
  - declared Screen or Search-within stages that ran store-wide scripts (155_T0 [80]-[85], 155_T1 [62]-[65]).
- **When "Read documents picked from the file listing" stays.** Kept only in 210_T0 [20]-[29], where representative letters were picked before any search. Elsewhere it is relabelled, because the reads had a search or scan lead (210_T1/T2, 209, 140, 121_T1, 061_T2). In 053_T0 [83]-[94] it became "Read a chosen matter's documents in depth".
- **Split declared spans.** Spans were split at a tool-call boundary in two situations:
  - a declared scan that held both a timed-out store-wide scan and a snippet script over a named list (053_T0 [32]/[36], 140_T2 [26]/[30]);
  - a declared scan or screen that held a reconcile or scan step followed by reads (121_T2 [60]/[64], 155_T0 [80]/[86]).
- **Counting task (210).** "Calculate figures for the answer" is used for per-prefix matter counts from a saved folder list (210_T0 [30]-[35], 210_T2 [69]-[78]). The script reads only a scratch file, not the store.
- **Document-level search-miss on a listing or screening stage.** In two runs the chosen matter's folder was never fully listed, so a required document never appeared:
  - 066_T0 [38]-[43]: a filtered listing, events [40]-[41];
  - 053_T1 [62]-[107]: no listing at all.

  Both use search-miss, following the 080_T1 precedent. The error sits on the stage where the agent worked on the matter, which is a judgement call.
- **"target partly surfaced" on a file-name-gated scan.** 140_T0 [55]-[60] and 140_T2 [80]-[85] use it for a scan that could not reach the missing matter because of its own file-name gate. The definition assumes the search could have reached it. No closer value exists.
- **review-endorsed in 053_T0 [94].** The screening review told the agent to write a structured-finance deal as a closed precedent. No review in any 053 run questioned whether a deal belongs to the requested practice group.
- **Generic vs specific flags.**
  - Generic: reviews that named only number ranges, or other matters, among the unopened ones (121_T0 [95], 155_T0 [79]).
  - Specific: reviews that named the exact cause of a filter-driven miss without naming the matter (140_T0 [60], 140_T2 [85], 155_T2 [57]).
- **Several later errors on one write stage.** 121_T1 has three `other_errors` on the same write stage (under-inclusion, misstated-facts, over-inclusion). Each has its own critic value. In 121, the aggregate spread figures (count, range, mean, total, split) get no error rows of their own: they follow from the errors in the matter set.
- **209 kept as over-inclusion.** This follows the round-2 batch-3 precedent. The matter that qualifies appeared only in folder lists and in the file-name listings of status-type documents (209_T0 [17]-[18], 209_T2 [16]-[17]), and was never opened. That is recorded in failure_point, not as a separate surfaced-not-opened error. Reviews flagged the chosen matter's open status in all three runs, and the agents only edited wording (flagged-ignored).
- **Protocol refusals.** Tagged `tool error`:
  - "No stage is open": 155_T0 [80], 053_T1 [153], 210_T2 [69], 209_T2 [68];
  - "still open": 121_T2 [118], 066_T1 [94], 061_T2 [88].
- **Untagged pattern: silent zero output from a script bug.** A path or matter-number bug made range scans print zero hits (121_T0 [30]-[33], 121_T1 [39]-[48]). These are tagged `no matches`, although the cause is a bug rather than an empty result. No tag covers this.
- **Shared judgement in 155.** T0 and T2 both excluded a standalone executed exclusivity agreement because its deal was a preferred-stock financing. No review mentioned it. This may be worth a precedent note.
