# Batch 7 proposals (c30): tasks 016 063 091 132 170 185 192 238

## NEW names

None. Every stage, tag, hindsight value and error kind comes from taxonomy.md.

| kind | name | definition | example | why no existing name fits |
|---|---|---|---|---|

## Issues

1. **170_T0 has no trace.** trace.jsonl holds only the user request and a termination event (`agent_error`: no response content or tool calls; 0 assistant turns; about 577 s wall clock). Even so, the output folder has a 15 KB response.md, graded 6/9. The log has no events, so there are no stages to record. check.py also crashes on a run with no calls (`min()` of an empty list). I left the run out of `runs` and recorded it under a top-level `missing_runs` field in 170.json, with a matching section in 170.md. The merge needs to decide how to count it.
2. **Protocol "Stage check" notes.** The harness sometimes adds "[Stage protocol] Stage check: this call looks like ..., which does not match the open stage" to a call's result (063_T0 [24], 063_T1 [27], 192_T1 [13]-[14]). The call still runs. The brief does not mention this, and no tag covers it, so I described it in the stage notes only.
3. **Label-check counts (batch 7):** followed 1, ignored 49, none 246. The note appears on almost every stage_start, but it fits only some of them. Recurring "ignored" cases:
   - the opening store-listing stage that also lists folders with `find -maxdepth 2`;
   - "List files in the document store" attempts 2-4 used for folder counts, relabelled List matter folders;
   - "Write the response" attempts 2-3 used for edits, relabelled Check or revise;
   - "Read documents picked from the file listing" used for screening reads led by keyword searches;
   - "Read a chosen matter's documents in depth" used for snippet scripts, relabelled Search within.

   The only "followed" is 238_T2 [14]-[17]: a content-search stage closed with no call, followed by an extraction-script stage. I used `ignored` only when the work matched the stage the note suggested. When I relabelled to a stage the note did not suggest, I used `none`.
4. **Stages with no tool call** besides stage_start/stage_end (238_T2 [14]-[17], 016_T1 [124]-[127]) keep their declared label, and the note says no tool was called.
5. **Generic "surfaced but unopened" review flag.** Nearly every review lists "about 60 surfaced matters never opened". When the error was an unopened or excluded matter that the review did not name, I recorded `flagged-ignored` or `flagged-fixed-partly` with "(generic flag)". Because this flag is so common, these two values say little in surfaced-not-opened runs. A separate value, or a rule that stock flags count as `not-flagged`, may be worth considering.
6. **Seen in scan snippets vs opened.** In 238_T0 and T1 the agent dismissed a needed matter as a "draft markup" from a scan snippet or a file name and never opened it. I classed this as surfaced-not-opened at the reading stage, not under-inclusion at the write stage. In 238_T2 the agent had read one of that matter's documents, so I classed it as under-inclusion on the write stage (convention 1).
7. **Parallel read results returned out of order.** In 132_T1 and T2, results came back in a different order from the calls, and this sits behind misstated-facts errors. As in earlier rounds, no tag records it.
8. **One kind per error on a large rubric.** In 132 (27 needed matters), a single surfaced-not-opened first error and a few later errors summarise many separate omissions. The why fields describe the dominant pattern rather than each matter.
