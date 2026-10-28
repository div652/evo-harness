# Batch 8 proposals (tasks 047 080 102 148 181 184 200 241)

## NEW names

None. Every stage, tag, hindsight value and error kind in this batch is in the frozen taxonomy.

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|

## Issues

- **Context overflow after a deliverable exists (241_T0).** The run wrote response.md at [50] and then ended with `termination_reason: context_overflow` (the earlier 4.1M-character scan output filled the context). I tagged the write stage `run ended: context overflow` but gave it the answer's hindsight value (`answer over-inclusive`), not `context overflow`, because the write itself did not overflow. Its later error has critic `no-review`, since the write review never ran.
- **Overflow without an oversized single call (184_T0 [28]).** The grep had `head -120`, but the matched lines were whole extracted documents, so about 7.7M characters came back anyway. A line cap does not limit characters. `huge output` covers this case, but a future note on "line-capped output still huge" might help.
- **Declared stages that hold two intents.** I split declared spans at tool-call boundaries in 047_T0 (scan, then reads), 102_T0 (listing, then reads), 148_T2 (listing, then reads), 181_T2 (globs, then reads), 184_T1/T2, 200_T2 and 241_T0 (store-wide file-name grep, then reads). The most common mismatch is a declared "Search file contents for request keywords" or "Search within a candidate matter's files" stage whose calls are really a store-wide python extraction script or a store-wide file-name grep.
- **Calls outside any open stage.** When the protocol refused a call (`No stage is open` or `Stage ... is still open`), I put that call in the next declared stage, or in the open stage if the refused call was a stage_start, and tagged it `tool error`. In 148_T1 and 148_T2, the write call sat inside a still-open earlier stage. I labelled it "Write the response" as its own span ([65]-[70] and [69]-[76]).
- **Hindsight for tasks with no rubric matter numbers (148, 181).** For 148 I treated the single qualifying deal (named in the criterion text) as the target. For 181 I treated the associate-bearing matters as targets, and I used `answer misses target` for an omitted associate. There is no hindsight value for "answer omits a person".
- **Critic flags and the first error.** In 148_T0 and 148_T1, the review that named the bad ranking rule (matter number used as recency) came one stage before the error stage, and later reviews repeated it. I counted this as `flagged-ignored`. Most reviews carry the same generic flag ("about 60 surfaced matters never opened"). Following the coordinator's rule, those errors have `critic_note` "(generic flag)".
- **Precision failures from comparison tables (148_T2).** The answer named the right deal but described other matters as qualifying alternatives in a comparison table. I used `over-inclusion`, though the agent presented them as comparators. The merge convention already folds comparators into over-inclusion (151_T2).
