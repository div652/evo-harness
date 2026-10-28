# Batch 5 proposals (tasks 011 058 081 126 161 167 173 223)

## NEW names

None. Every stage, tag, hindsight value, error kind and critic value comes from taxonomy.md.

| kind | name | definition | example | why no existing name fits |
|---|---|---|---|---|

## Issues

- **081_T0 has no trace.** Its trace holds only the request and `agent_error: No response content or tool calls` (0 assistant turns, finish never called), so the log has no events. A 4.4 KB `response.md` from an untraced attempt sits in the output folder, and the judge graded that file 0/3. A run with no calls cannot be segmented, and `check.py` would crash on it (`min()` of an empty call list). To avoid that, I kept T0 out of `runs` and recorded it under a top-level `runs_without_trace` field in 081.json, with a "T0: FAIL (0/3), no trace" section in 081.md. 081 therefore has no first_error for T0. A merge script that expects three runs per task needs to handle this field.
- **Sources outside the logs.** To understand 081_T0 I opened its `result.json` and output `response.md`. For 126_T0 I opened `scores_judge-1.json` to read the untruncated judge reasoning for four criteria. These files sit next to the named traces in the same run folders, but they are not the traces themselves.
- **label_check conventions.**
  - When the agent opened a stage, made no call, closed it after the label note and opened the suggested stage, I merged the empty span into the next stage and marked it `followed` (058_T0 [16]-[25], 173_T1 [14]-[23]). These are the only two `followed` cases. Both came from a declared content-search stage whose note pointed to the scan stage.
  - `none` covers notes that did not apply: the declared label was right, such as a real whole-store glob under "List files in the document store", or the suggested stages did not describe the work either.
  - When a span was split or relabelled to the suggested stage, `ignored` sits on the relabelled piece only.
- **Where notes were ignored.** Two cases recur across all tasks:
  - "List files in the document store (attempt 2/3)" used for folder counts, where the note named "List matter folders".
  - "Read documents picked from the file listing" (and sometimes the scan label) used for screening reads, where the note named "Screen candidate matters by reading documents".

  The notes did not change behaviour once the agent had work queued.
- **Critic oscillation (011_T0).**
  1. The write review asked to drop draft-stage matters.
  2. The agent's edit cut 21 matters to 11 and dropped a qualifying matter.
  3. The next review flagged the narrowing and named that matter.
  4. The agent widened again.
  5. The following review called that widening and pushed back to 11, which the agent kept.

  I labelled this `review-endorsed`. 161_T1 is also `review-endorsed`: the last review told the agent not to remove a ranked-out comparison matter. In 161_T0 the last review said to keep that matter "only as a comparison". This did not name the qualifying wording, so I labelled it `not-flagged`.
- **Harness-appended matter lists.** Every review ends with a harness-appended "Matters that appeared in your search results but none of whose documents you have opened" list. I did not count a matter's presence in that list as a specific flag. Only reviewer flags or recommendations that named a matter, document or mechanism count as `(specific flag)`.
- **Several errors on one stage.**
  - 011_T0, 011_T1 and 126_T0 have a document-choice error and a search-miss on the same screening stage.
  - 223_T1 and 058_T2 have two errors on the write stage.

  Within a stage, the error behind more failed criteria comes first. A proof document that never appeared in any output was labelled `search-miss` and placed on the reading stage that worked on that matter (011_T0, 011_T1). No search stage targeted it.
- **Late reclassification (223_T1).** In a check stage, a wider search of one counted matter flipped it to qualifying (12 of 13 became 13 of 13). I recorded this as a later over-inclusion on that check stage with `flagged-fixed-partly`: the review questioned the flip, and the agent only quoted the clause.
- **Narrowing filters over saved scan output (126_T1, 126_T2).** These are `over-narrow-filter`. The broad scan output (relevant-hits file, court-document-file scan) listed the dropped qualifying matters before the phrase filter cut them. In 011_T1 the path filter was rerun without the filter after a review, but the next shortlist still left three matters out. There I placed the first error on the screening choice (`surfaced-not-opened`) and mentioned the earlier filter in `why`.
- **Protocol notices.** "Stage check: this call looks like …" notices in results (173_T0 [44], [87]) are warnings, not refusals, and were not tagged. Refused calls ("No stage is open", "still open") are tagged `tool error` per the brief.
- **Task words in notes.** I replaced topical request words in notes, failure points and divergences with generic phrasing ("request words", "the requested clause", "loan-side matters", "court-document words"). I kept document-type words (complaint, lease, agreement, memo) as the round-2 models do.
