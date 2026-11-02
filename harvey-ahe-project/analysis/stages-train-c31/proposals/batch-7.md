# Batch 7 proposals (tasks 017 068 111 130 131 161 221 230)

## NEW names

None. Every stage, tag, hindsight value and error kind comes from taxonomy.md. 81 stage rows carry `agent_new`. They come from 71 stage starts declared "new"; nine spans were split, which accounts for the extra ten rows. All of them map to existing stages, and each note starts `declared: new: <name>`.

| kind | name | definition | example | why no existing name fits |
|---|---|---|---|---|

## Issues

- **Where the agent-defined stages went.** Counts are per row after splitting.
  - Scan document text with an extraction script: 25 rows. These are rescans and batched or background reruns that reviewers suggested. Examples: 131_T0 "Tighter per-document MAC dispute scan" and 017_T2 "Background batched scan to full coverage".
  - Screen candidate matters by reading documents: 18 rows. Examples: 111_T0 "Resolve unopened large-amount settlement candidates" and 130_T1 "Screen candidate matters by reading documents". The agent gave that second span the taxonomy name, but declared it as "new".
  - Check or revise the response: 12 rows (post-write verification passes).
  - Read a chosen matter's documents in depth: 10 rows.
  - List files in candidate matters: 6 rows.
  - Search file names for request keywords: 6 rows.
  - Search within a candidate matter's files: 4 rows.
- **Tally of saved output (precedent conflict).** Another batch's proposals add `NEW: Tally saved search output per matter`; batch 1 and round 3 (011_T0) kept "Scan document text with an extraction script". I kept the scan label for consistency with round 3. If the merge adopts the NEW stage, these spans only re-read scratch files of earlier scans, with no new reads of the store:
  - 068_T1 [71]-[78];
  - 068_T2 [50]-[55] (agent: "Consolidate candidate pool");
  - 111_T0 [22]-[29] ("Summarize scan output per matter") and [183]-[188] ("Cross-store max-amount sanity check");
  - 111_T1 [36]-[41] and [42]-[47];
  - 130_T1 [30]-[35] (declared "Read documents picked from the file listing");
  - 131_T0 [51]-[56] ("Verify MAC scan coverage and later candidates");
  - 161_T0 [44]-[49] and [50]-[55] ("Review full strong-hit summary").
- **Redacted agent names.** Names that contain a matter number or client name are redacted in the note (`<matter>`, `<client>`). `agent_new` keeps the exact name. The affected rows are 130_T0 [179]-[186], 131_T1 [90]-[97], 221_T0 [27]-[34] and 221_T2 [38]-[43].
- **Scoring `label_check` and `label_check_end`.** I used the coordinator's two-field rule.
  - `ignored` covers keeping the old label and also declaring some other stage, including a "new" one, for the same kind of work. Examples are 017_T1 [32]-[50] and 017_T2 [68]-[86]: the agent took the reviewer's suggested new step instead of the label X.
  - Notes whose X does not describe the work are scored by whether later work of that kind existed. Examples are "Calculate figures for the answer" on scan or listing work (017_T1 [26]-[31], 068_T1 [71]-[78], 068_T2 [62]-[67], [108]-[115]) and "Check or revise the response" on a scan (161_T2 [28]-[33]). So 017_T1 and 068_T1 count as `ignored`, and the other three as `none`.
  - Post-write source re-reads were not counted as the same kind of work as screening, so screening notes followed only by checks are `none` (as in batch 1).
  - On split spans, the start note's outcome sits on the piece where the suggested work was done (068_T2 [91]-[107]).
  - Totals over 24 runs: `label_check` followed 1, ignored 20. `label_check_end` followed 3, ignored 14.
  - Where notes were followed:
    - 230_T2 [85]-[88]: the agent closed the stage at once with no work, and the next stage was screening.
    - 130_T0 and 230_T0: the next stage was declared "List matter folders".
    - 111_T0 [201]-[210]: the next edits were declared as a check.
- **An empty declared stage.** 230_T2 [85]-[88] has only stage_start and stage_end. It keeps its declared label ("Read documents picked from the file listing") with hindsight `none`, so that no work is relabelled.
- **Whole-store file listings.** These are "List files in the document store (attempt 2)" spans that print every file of every folder (500K to 800K characters, shown truncated). The classifier's end note called them "List matter folders". I kept the declared label because they list files, not just folders or counts, and tagged them `huge output` (017_T0, 017_T1, 111_T0, 111_T1, 130_T2, 131_T0, 221_T2, 230_T0). Spans that only counted files per folder were relabelled "List matter folders", with `label_check` ignored.
- **Placing context-overflow errors.**
  - 111_T2, 130_T2 and 221_T1 overflowed on one scan result of 4M to 5.6M characters, and the error is placed there.
  - 161_T0 is the exception. Its earlier scan printed about 1.9M characters, but the reviewer said the output was shown truncated, and the run went on for 40 more events. The run ended after fourteen whole-document reads (about 500K characters), so the error sits on that reading stage. The unopened needed matter is a later error on the same stage.
  - 221_T0 survived a 675K-character scan result.
- **Ordering forced 130_T1's first error onto a minor criterion.** By stage order, the first error is a search-miss on one matter's proof document (an in-matter snippet stage, [51]-[56]). The run's main loss comes later: two needed matters whose clauses were in that snippet output never reached the answer, coded as under-inclusion on the write.
- **017_T1's first error is incomplete-population, on the screening stage.** That is where the agent dropped a bridge loan without an EBITDA definition from the set, and the review there named it. The over-inclusion follows on the write.
- **Reviews and stock lists.** The stock "Common failures" lists in write and check reviews were not counted as flags. Errors with only those lists in reach are `not-flagged`, following round 3 (048_T0). "(generic flag)" is used only when the reviewer's own text raised the issue.
- **Recurring pattern: reviewers' suggested new steps.** These drove most agent-defined stages. The agent sometimes took a suggested step under a taxonomy label instead. For example, 161_T0 got "List matter folders completely" and declared "List matter folders", and 230_T1 ignored "Rerun missing scan ranges", which led to its first error.
- **Post-write candidate reads.** 111_T0 [189]-[200] and 131_T1 [159]-[196] read new candidates after writing. They were labelled as screening or scans, not as checks, following the batch-2 (round 1) note on searches that follow a write.
