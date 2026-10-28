# Batch 6 proposals (tasks 035 063 072 140 167 170 192 238)

No NEW names were needed: every stage, tag, hindsight value and error kind comes from taxonomy.md.

| kind | name | definition | example | why no existing name fits |
|---|---|---|---|---|
| (none) | | | | |

## Issues

- Splitting declared stages: agents often packed several intents into one declared stage (scan, then reads, then snippet scripts, e.g. 035_T0 [34]-[65], 167_T1 [31]-[95], 170_T1 [46]-[75]). I split these at tool-call boundaries and marked each part `declared: <name>, continued`. Batches that do not split will show fewer, longer stages for the same behaviour.
- "Read a chosen matter's documents in depth" is the declared name for many first opening reads of candidate matters. I relabelled those to "Screen candidate matters by reading documents" and kept the declared name only for re-reads or later sections of matters already being weighed. This is the round-1 judgement call, made more often here.
- Content-extraction scripts declared as "Search file contents for request keywords" (140_T2, 238_T1, 238_T2) were relabelled to "Scan document text with an extraction script". Scripts over a hand-picked list of matters went to "Search within a candidate matter's files" (063_T0, 170_T2, 238_T2), as in round 1.
- Calls refused by the stage protocol (a stage_start while a stage is open, or a call with no open stage) get `tool error` and stay in the stage around them. A refused call made between stages goes into the next stage (072_T0 [89], 140_T0 [103], 170_T1 [121]). The non-blocking "Stage check" notices that come back with results are not tagged.
- Critic field: nearly every write-stage review in these tasks carries the same stock flags ("~60 surfaced matters never opened", "possible under-inclusion", "possible over-inclusion"). Under the coordinator's rule these count as `flagged-*` with "(generic flag)", so almost no failing run is `not-flagged`. Telling stock flags apart from targeted ones depends on `critic_note`, not on the `critic` value.
- When the agent responded to a generic flag by opening other matters, but never the one behind the error, I used `flagged-fixed-partly` (140_T2, 167_T1, 170_T0/T1/T2). When it changed nothing relevant (path checks only), I used `flagged-ignored`. This line is a judgement call.
- Several first errors are search-miss for one never-surfaced matter, while most of the run's failed criteria come from surfaced-not-opened errors at a later stage (170_T0, 170_T1). The earliest-stage rule puts the search miss first; the other matters are in other_errors.
- Precision failures after the qualifying matters were all found (035, 072, 238_T0) are over-inclusion at the write stage. In 035 and 072 the extra matters were non-closed offerings or matters that only mention the terms in passing.
- 140: the rubric matter whose evidence sits in closing and financing documents is the hard case in all runs. 140_T1 scanned inside it (contents extracted) without ever reading it; I used under-inclusion (convention 5, "opened" includes grepping inside), not surfaced-not-opened.
- 063_T2: the missing proof document appeared only as a line in the agent's own scan output, never in a folder listing. I used listed-document-not-opened, reading "listing" to include the per-file scan output.
