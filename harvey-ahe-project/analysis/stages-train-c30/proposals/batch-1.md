# Batch 1 proposals (tasks 028 034 048 102 129 151 194 201)

## NEW names

None. Every stage, tag, hindsight value and error kind is from taxonomy.md.

| kind | name | definition | example | why no existing name fits |
|---|---|---|---|---|

## Issues

- label_check scoring. `ignored` means the agent did the work a "Check the label" note described, under the declared label; the stage was then relabelled. `none` means the declared label fit the main work, even when a small parallel call matched the note (048_T2 [30]-[38]), or when the relabel was to a stage the note did not suggest (034_T1 [61]-[66], 201_T1 [68]-[78]). `followed` occurs once (102_T1 [14]-[17]): an empty span, kept as its own row, where the agent switched to the suggested scan stage without a call. Counts over 8 tasks: followed 1, ignored 38.
- The most common `ignored` case: a declared "List files in the document store (attempt 2)" that lists or counts matter folders, even though the note names "List matter folders" (028, 034, 194).
- Convention 3 and the note can disagree. When a declared listing span also runs one store-wide file-name grep, convention 3 relabels the span "Search file names for request keywords" (129_T0 [52]-[58], 034_T2 [9]-[14]), and that is counted as `ignored`. This can inflate the ignored counts.
- Declared "Read documents picked from the file listing" was used for first reads of candidates surfaced by searches (034_T2, 048_T0, 048_T1, 102_T1, 201). These spans were relabelled "Screen candidate matters by reading documents" and counted `ignored`.
- Two-intent spans were split at a tool-call boundary:
  - 034_T1 [73]-[76] / [77]-[82]: a store-wide path regex, then reads.
  - 201_T2 [67]-[72] / [73]: the write sits inside a span declared as a check.
- "Check or revise the response" spans in which a path-check script opened `response.md` from the wrong folder (FileNotFoundError) are tagged `file not found` (028, 034_T2).
- Harness "Stage check" notices returned with a glob result (034_T2 [72], [114]; 102_T0 [82]) are warnings, not refusals, so they are not tagged `tool error`. Reads refused with "No stage is open" are tagged `tool error` on the next stage (028_T0 [83]).
- The critic values have edge cases:
  - 151 (all runs): the over-inclusion was already in the first draft. The write and check reviews then asked to keep the comparison rows, so the value is `review-endorsed`, although the reviews kept the error rather than caused it.
  - 028_T0 and 028_T2: the review questioned the extra matter and the agent re-read its documents but kept it, giving `flagged-fixed-partly`. Later check reviews said "do not add or drop matters", which is close to `review-endorsed`.
  - 194_T0: an in-matter review called a clause a parity term, and the answer then excluded that matter, giving `review-endorsed`.
- Kind boundaries:
  - 129_T2: `over-narrow-filter` was used for a retry scan whose hits were hidden by the agent's own `grep -v` and line caps. Its definition names folder or file-name filters; `search-miss` is the alternative.
  - 194_T2: a matter was dropped by a hand-picked "core list" after its snippets were seen. Under convention 1 this is `under-inclusion` at the write stage; `over-narrow-filter` is the alternative.
- 194_T1: parallel reads came back in a different order from the calls, which caused a misstated-facts error. This is the known pattern from the merge Issues, and still no tag records it.
- 048: the rubric allows matter 1014-00001, but the log header does not list it among the target matters. Hindsight values follow the header only.
