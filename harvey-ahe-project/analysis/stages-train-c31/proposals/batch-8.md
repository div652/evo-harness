# Batch 8 proposals (round 4; tasks 046 072 132 140 162 173 238 243)

## NEW names

| Kind | Name | Definition | Example | Why no existing name fits | Agent's new-stage name, runs, outcomes |
|---|---|---|---|---|---|
| stage | NEW: Write a working notes file | Writing a scratch file that is not the deliverable (for example an audit table of candidates with include/exclude decisions and sources) with bash/write, before the response exists | 072_T0 [85]-[90] | "Write the response" is defined as writing the deliverable; "Check or revise the response" needs a response; the scan/search stages run searches, and nothing here searches or reads | "Complete per-matter verification table" (072_T0, fail). Only occurrence in the batch |

No NEW tags, hindsight values, error kinds or critic values.

## Agent-defined stages mapped to existing stages (50 declared "new" spans)

All but one map onto taxonomy stages; the note starts `declared: new: <name>`.
- Scan document text with an extraction script (22): post-processing of saved scan output, rescans, coverage checks (046_T0 x2, 046_T2 x2, 072_T0, 072_T1 x2, 132_T1, 132_T2 x2, 140_T0 x2, 140_T2 x2, 173_T0 x2, 238_T0, 238_T1 x2, 238_T2 [42]-[51], 243_T0 [30]-[55], 243_T2 [42]-[47]).
- Screen candidate matters by reading documents (7): 046_T0 [86]-[95], 072_T0 [43]-[75], 072_T1 [32]-[66], 173_T0 [70]-[90], 238_T2 [52]-[80], 243_T0 [56]-[89], 243_T2 [48]-[84].
- Read a chosen matter's documents in depth (3): 072_T0 [76]-[84], 243_T0 x2.
- Search within a candidate matter's files (5): 238_T0 x2, 238_T2 x3 (clause scripts over about ten named agreements).
- Check or revise the response (9): 132_T0 x6, 173_T0 x2, 238_T1 [152]-[157].
- List files in candidate matters (1): 173_T0 [97]-[102]. Search file names (2): 046_T2 [46]-[53] (request keywords), 132_T1 [42]-[51] (document type).
- For coverage audits of an earlier scan I did not need a NEW name: they either re-filtered the saved scan output or rescanned skipped file types, so they were labelled as the scan stage (243_T2 [42]-[47], 238_T2 [42]-[51], 173_T0 [42]-[49]).

## Issues

- **Most agent-defined stages adopt the reviewer's suggested name.** In these 24 runs the reviewer suggested a new step 58 times. The agent's next stage_start used that exact name 27 times, and once in shortened form (132_T0 "Revise response scope and verify facts" became "Revise scope and verify facts"). So about 28 of the 50 "new" stage starts come from the reviewer, not from the agent. Examples: 238_T2 [97] "Per-agreement tax clause read" and 243_T2 [48] "Confirm issued holds in candidate matters". A suggestion that pointed at the failing cause was not adopted: 238_T2 [19] "Identify Tax matters" (the practice-group question behind the precision failure in all three 238 runs). Suggestions made right before writing ("Store-wide ... coverage check", "Widen coverage ...") were never taken.
- **Agent names containing task words fail check.py.** Examples are 072's "...clinical-hit matters" and "HLS and clinical verification". The `declared: new: <name>` notes write those words as `<topic>` / `<practice>`. The exact names are kept in `agent_new`.
- **label_check / label_check_end** follow the coordinator's two-field convention, which I applied to all 8 tasks. Start notes: followed 0, ignored 31. End notes ("Label: these calls looked like 'X'"): followed 14, ignored 7. Most "followed" end notes were folder-listing or scan notes, where the agent's next stage happened to be the named one. Several "followed" cases did different work under the new label. For example, in 162_T0 [14]-[19] the agent declared folder listing and then ran a path search. An end note counted as `none` when the named kind of work did not recur (often because writing followed).
- **Refused protocol calls.** `tool error` is used for stage_starts refused because a stage was still open (several runs) and for calls refused with "No stage is open". The refused calls were put in the next stage (046_T1 [150], 132_T2 [119], 238_T1 [142]). One case is 072_T1 [113]: a second stage_end with an empty result. I put it in the next stage with `tool error`. "Stage check" warnings are not tagged.
- **Several errors in one run (046, 132, 238).** These are multi-matter tasks. I recorded the earliest error as first_error and kept the matter-level consequences as later errors. For example, in 238 a listed closing memo was never opened (listed-document-not-opened at screening). The write stage then gets under-inclusion for excluding that matter and over-inclusion for counting other groups' deals.
- **review-endorsed** is used three times. In 140_T2 and 132_T0 a write review called a terminated deal out of scope, and the agent demoted it. In 072_T2 the scan review called the three-matter set hand-picked, the agent widened, and the answer went from 3 matters to 16.
- **Terminated deals.** In 140 and 132 the rubric counts a terminated deal with a bound policy or negotiated clause, and write-stage reviews in every run pushed against it. This looks like a stock critic heuristic ("a terminated deal is not a precedent") working against these tasks.
- **Hand-picked candidate lists after complete scans** are the dominant failure (046, 132, 140_T2, 243_T0). The specific flags ("hand-picked", "capped at head -120", "screen all 190") were ignored or only partly acted on.
- **Placement of the 162 error.** All three 162 runs fail precision the same way: a later closed offering is described as a qualifying traditional offering in the chronology. I coded this over-inclusion (comparators described as meeting the request, merge note 151_T2), although the agent meant it only as a comparison.
