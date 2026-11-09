# Feedback uptake: tables

Training runs r2+r3: 478; failing: 333; reviews parsed: 6046.

## A. First-error cases where the reviewer flagged the error (LLM-labelled)

Cases labelled: 237.

### Was the reviewer right? (`flag_correct`)

| Value | Cases |
|---|---|
| yes | 168/237 (71%) |
| partly | 69/237 (29%) |

### Did the flag name the needed item? (`names_needed_item`)

| Value | Cases |
|---|---|
| False | 161/237 (68%) |
| True | 76/237 (32%) |

### Where in the review (`flag_part`)

| Value | Cases |
|---|---|
| several | 110/237 (46%) |
| flags | 105/237 (44%) |
| recommendation | 11/237 (5%) |
| unopened_list | 7/237 (3%) |
| concerns | 4/237 (2%) |

### Shape of the ask (`advice_shape`)

| Value | Cases |
|---|---|
| several_actions | 210/237 (89%) |
| one_action | 16/237 (7%) |
| vague | 11/237 (5%) |

### Timing vs the agent's decision (`timing`)

| Value | Cases |
|---|---|
| before_decision | 149/237 (63%) |
| after_decision | 88/237 (37%) |

### Agent's next step (`agent_next`)

| Value | Cases |
|---|---|
| started_suggested_stage | 119/237 (50%) |
| moved_on | 64/237 (27%) |
| reopened_same_stage | 52/237 (22%) |
| finished | 2/237 (1%) |

### Next goal addresses the flag (`next_goal_addresses_flag`)

| Value | Cases |
|---|---|
| partly | 142/237 (60%) |
| no | 83/237 (35%) |
| yes | 12/237 (5%) |

### Ever acted on it (`eventual_action`)

| Value | Cases |
|---|---|
| partial | 120/237 (51%) |
| none | 116/237 (49%) |
| full | 1/237 (0%) |

### Agent argued against it (`agent_disputed`)

| Value | Cases |
|---|---|
| False | 227/237 (96%) |
| True | 10/237 (4%) |

### Agent's summary overclaimed (`summary_overclaims`)

| Value | Cases |
|---|---|
| True | 228/237 (96%) |
| False | 9/237 (4%) |

### Why not followed (`why_not_followed`)

| Value | Cases |
|---|---|
| own_plan_continued | 99/237 (42%) |
| acted_superficially | 51/237 (22%) |
| buried_among_other_asks | 47/237 (20%) |
| advice_too_vague | 22/237 (9%) |
| reviewer_wrong_or_misleading | 11/237 (5%) |
| agent_judged_flag_wrong | 5/237 (2%) |
| advice_arrived_after_decision | 2/237 (1%) |

### Would following it fix the first error (`would_fix_if_followed`)

| Value | Cases |
|---|---|
| partly | 148/237 (62%) |
| yes | 88/237 (37%) |
| no | 1/237 (0%) |

### Would the run then pass (`would_pass_if_followed`)

| Value | Cases |
|---|---|
| unlikely | 173/237 (73%) |
| likely | 64/237 (27%) |

### Splits

| Group | n | flag right | named item | acted fully | acted partly | never acted | would pass if followed |
|---|---|---|---|---|---|---|---|
| all | 237 | 71% | 32% | 0% | 51% | 49% | 27% |
| annotation: specific flag | 139 | 80% | 49% | 1% | 42% | 57% | 33% |
| annotation: generic flag | 98 | 58% | 8% | 0% | 62% | 38% | 18% |
| annotation: flagged-ignored | 179 | 71% | 30% | 0% | 35% | 65% | 27% |
| annotation: flagged-fixed-partly | 58 | 71% | 40% | 2% | 98% | 0% | 28% |
| error family: not opened | 122 | 72% | 30% | 0% | 52% | 48% | 22% |
| error family: judgement | 64 | 58% | 59% | 0% | 55% | 45% | 34% |
| error family: search/scan | 51 | 84% | 4% | 2% | 43% | 55% | 29% |
| timing: before_decision | 149 | 74% | 38% | 1% | 50% | 49% | 30% |
| timing: after_decision | 88 | 65% | 22% | 0% | 51% | 49% | 23% |
| ask: one_action | 16 | 100% | 19% | 0% | 50% | 50% | 25% |
| ask: several_actions | 210 | 68% | 34% | 0% | 52% | 47% | 28% |
| ask: vague | 11 | 82% | 18% | 0% | 18% | 82% | 18% |
| round r2 | 122 | 68% | 32% | 0% | 48% | 52% | 22% |
| round r3 | 115 | 74% | 32% | 1% | 54% | 45% | 32% |

### Headroom

Cases where the flag was right, following it would fix the first error, and the run would likely pass: **38** of 237 labelled cases (16%); 7.9% of all 478 r2+r3 runs (all-pass was 30.3%).

| Why not followed (headroom cases) | n |
|---|---|
| own_plan_continued | 24 |
| acted_superficially | 6 |
| buried_among_other_asks | 6 |
| reviewer_wrong_or_misleading | 1 |
| agent_judged_flag_wrong | 1 |

## B. Flag-level uptake in a random sample of reviews (LLM-labelled; half from passing, half from failing runs)

Reviews: 150; flags: 446.

| Group | flags | acted yes | partly | no | already planned |
|---|---|---|---|---|---|
| all | 446 | 29% | 35% | 35% | 13% |
| specific=True | 391 | 31% | 35% | 34% | 13% |
| specific=False | 55 | 15% | 40% | 45% | 15% |
| concrete action=True | 373 | 34% | 33% | 33% | 13% |
| concrete action=False | 73 | 7% | 45% | 48% | 15% |
| specific + concrete, not already planned | 303 | 35% | 29% | 37% | 0% |
| position 1 in the flag list | 150 | 35% | 26% | 39% | 8% |
| position 2 in the flag list | 137 | 25% | 41% | 34% | 13% |
| position 3 in the flag list | 94 | 33% | 39% | 28% | 19% |
| position 4+ | 65 | 22% | 38% | 40% | 18% |
| review has 1-1 flags | 13 | 46% | 31% | 23% | 23% |
| review has 2-3 flags | 245 | 26% | 37% | 37% | 12% |
| review has 4-98 flags | 188 | 32% | 34% | 34% | 14% |
| reviewer verdict partly | 393 | 29% | 35% | 36% | 14% |
| reviewer verdict no | 53 | 32% | 34% | 34% | 9% |
| run passed=True | 222 | 28% | 37% | 35% | 14% |
| run passed=False | 224 | 30% | 33% | 36% | 13% |
| agent's next move: reopen | 168 | 48% | 32% | 20% | 8% |
| agent's next move: new | 49 | 39% | 45% | 16% | 6% |
| agent's next move: other | 229 | 14% | 36% | 51% | 19% |
| stage: Scan document text with an extraction script | 172 | 27% | 41% | 31% | 14% |
| stage: agent-defined (new) stages | 47 | 28% | 45% | 28% | 4% |
| stage: Screen candidate matters by reading documents | 43 | 23% | 28% | 49% | 7% |
| stage: Search file names for request keywords | 40 | 52% | 32% | 15% | 25% |
| stage: List files in candidate matters | 36 | 19% | 31% | 50% | 8% |
| stage: Search within a candidate matter's files | 28 | 29% | 29% | 43% | 29% |
| stage: Read documents picked from the file listing | 24 | 42% | 8% | 50% | 4% |
| stage: Write the response | 23 | 39% | 52% | 9% | 30% |
| stage: Read a chosen matter's documents in depth | 21 | 10% | 14% | 76% | 0% |

| How acted-on flags were acted on | n |
|---|---|
| next_stage | 174 |
| second_stage | 64 |
| reopened_same_stage | 50 |

| Recommendation followed (review level) | reviews |
|---|---|
| yes | 13/150 (9%) |
| partly | 115/150 (77%) |
| no | 22/150 (15%) |

| Next goal driven by the review | reviews |
|---|---|
| yes | 87/150 (58%) |
| partly | 41/150 (27%) |
| no | 22/150 (15%) |

## C. Script measures over all reviews

Reviews naming at least one matter the agent had not opened or listed: 2783; one of them opened in the next stage: 537/2783 (19%); at any later point: 1376/2783 (49%).

Needed matters named by a review while unopened: 642. Never opened afterwards: 55.

| Reviews naming it before the agent opened it in the following stage | needed matters |
|---|---|
| 1 | 203 |
| 2 | 84 |
| 3 | 31 |
| 4 | 13 |
| 5 | 5 |
| 6 | 1 |
| opened without a prompt in the next stage | 250 |

