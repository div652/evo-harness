# Batch 4 proposals (tasks 016 056 059 129 131 132 161 223)

## NEW names

None. Every stage, tag, hindsight value and error kind is from taxonomy.md.

| kind | name | definition | example | why no existing name fits |
|---|---|---|---|---|

## Issues

- Critic field: applied the coordinator rule. A generic review flag (e.g. "~60 surfaced matters unopened", "possible over-/under-inclusion", "population may be incomplete") still counts as flagged-*, with `critic_note` "(generic flag) ...". A flag that names the matter, document or mechanism (a filename filter, a hand-picked list, a restricted scan) gets "(specific flag) ...". Generic "unopened" flags appear in nearly every review, so with this rule few errors stay not-flagged. The ones that do are over-inclusion of extra matters (161_T1, 223_T0, 223_T2), where reviews pushed for a broader population.
- Critic-induced expansion: in 223_T0 the reviews kept asking for a broader population, and the agent added one more matter from outside the set (the later over-inclusion at stage 11). No field records an error that the critic's advice caused.
- Same flag, different outcome: in 056 the write review flagged the headline matter in both T1 and T2. T2 fixed it at the check stage and passed; T1 only re-read the file. For that mixed task, the check stage after writing is where the runs split.
- Declared "List files in the document store (attempt 2)" almost always lists matter folders, sometimes alongside a file-name grep. These spans were relabelled "List matter folders" or, under convention 3, "Search file names for request keywords" / "...for a document type".
- Declared "Read a chosen matter's documents in depth" was often used for first reads across many candidates. Following the round-1 issue, these were relabelled "Screen candidate matters by reading documents". The declared label was kept when the reads targeted already-chosen lead matters or used offsets.
- Declared spans with two intents were split at a tool-call boundary: 016_T1 [37] (listing chosen matters inside a scan span), 016_T2 [99] (edits after the write), 129_T2 [32] (reads after a file-name search), 223_T0 [124] (edits inside a reading span), 223_T1 [84] (reading scan output inside a reading span).
- Calls refused by the protocol (stage_start while a stage is open, or an edit with no stage open) are tagged `tool error`. They stay in the open span, or go to the next span when no stage was open (131_T2 [76], 223_T1 [112]). The [13] protocol notice in 131_T1 is a warning, not a refusal, and is not tagged.
- 129_T0: asserting a second folder number that holds the same dispute's documents was labelled over-inclusion. misstated-facts ("which matter number or folder a document belongs to") is a possible alternative.
- 016_T0: the matter was dropped by a filename filter (over-narrow-filter), then surfaced again in a later batch scan and still was not opened. surfaced-not-opened at stage 7 would also fit; the earlier filter was kept as the first error.
- 223_T1: the first error was labelled over-narrow-filter for a narrower re-search that dropped a matter, not for a filter over saved output. It sits at the boundary of that kind's definition.
- `huge output` was tagged on 131_T2 [25]-[30] (about 1.8M chars) even though that run did not overflow. The same applies to 129_T2 (about 1.5M chars). Context overflow depends on more than result size.
