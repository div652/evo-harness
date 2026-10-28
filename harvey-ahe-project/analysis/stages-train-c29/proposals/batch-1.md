# Proposals: round 2 (campaign 29), batch 1

Tasks: 003 053 092 125 154 195 211 221 (24 runs: 7 pass, 17 fail).

## NEW names

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|
| (none) | | | | Every stage, tag, hindsight value and error kind fit an existing taxonomy row. |

## Issues

- **Span boundaries.** Each declared span runs from its `stage_start` call to the event just before the next `stage_start`, so the `stage_end` call and its review sit inside the stage. Each reopened attempt gets its own row, and adjacent rows with the same name are not merged.
- **Relabelled spans.** Common relabels:
  - An "attempt 2" of "List files in the document store" that only lists matter folder names becomes "List matter folders" (003 T0, T1 and T2).
  - A declared "Scan document text…" span over a few named matters becomes "Search within a candidate matter's files" (003_T0 [26]-[32]).
  - A declared "Search file contents…" span that is in fact a Python extraction script becomes "Scan document text with an extraction script" (221_T1 [8]-[16], [44]-[49]).
  - A declared "Write the response" span that only edits the response becomes "Check or revise the response" (053, 092).
- **Split spans.** Declared spans with two intents were split at tool-call boundaries in 053_T1, 053_T2, 092_T0, 092_T2, 125_T0 (three spans), 195_T0, 211_T0 and 211_T2.
- **Harness-rejected calls.** Calls the stage protocol rejected are tagged `tool error`. These are a `stage_start` sent while a stage was still open, a `finish` sent while a stage was still open, or an edit/call made with no stage open. They are kept in the open stage, or attached to the next stage when no stage was open (003_T2 [82]-[83], 092_T2 [73]-[74]). A tag for protocol rejections may be worth adding.
- **Generic critic flags need one rule.** Almost every review says something like "about 60 surfaced matters never opened" or "possible under-/over-inclusion", and lists example matters that are usually not the ones the agent needed. This batch counted such generic flags as naming the problem (`flagged-ignored` / `flagged-fixed-partly`) and recorded "(generic flag)" in `critic_note`. Other batches may score them `not-flagged`, so the merge should fix one rule.
- **Critic recorded in md.** The `critic` value plus a one-line `critic_note` (which review [n] named or missed the problem) is written as a `**Critic:**` line under each error line in the .md files. `critic_note` is an extra JSON field.
- **Context overflow after an earlier warning.** In 003_T1 the review of the stage before the overflow ([19]) had already told the agent to cap its output. The overflow stage itself got no review, so it is scored `no-review` and the warning is noted in `critic_note`. A value such as "warned-earlier" could tell these cases apart from runs that were never warned.
- **Search miss hidden by the overflow.** In 003_T1 the timed-out scan before the overflow also missed the needed matter. Following the round-1 overflow convention, it was not recorded as an error.
- **Critic advice that caused an error.** In 195_T0 the write-stage review ([83]) suggested dropping a possible duplicate, and the agent then deleted a row it needed. The next review flagged the deletion and the agent ignored it. No critic value covers "the review caused the error".
- **Comparators.** In 154 the only failure is precision, from older deals listed as comparators. These are scored over-inclusion, following the 151_T2 precedent.
