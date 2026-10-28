# Batch 3 proposals (tasks 014 034 058 081 111 130 158 209)

## NEW names

None. Every stage, tag, hindsight value and error kind in this batch maps to an existing taxonomy row.

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|

## Issues

- Declared "List files in the document store" (attempt 2) was usually a folder enumeration and is relabelled "List matter folders". When the same parallel event also ran a store-wide path search, it is relabelled "Search file names for request keywords" (convention 3), e.g. 111_T0 [8]-[13], 158_T1 [8]-[16], 209_T0 [9]-[16].
- Declared "Read a chosen matter's documents in depth" was most often a first read of several candidates' main documents, so it is relabelled "Screen candidate matters by reading documents" (014, 058, 111, 158, 209). The agents use "in depth" for any verification read.
- Declared "Search within a candidate matter's files" was used three times for store-wide scripts (111_T0 [40]-[45], 158_T1 [70]-[85], 209_T0 [56]-[63]). These are relabelled "Scan document text with an extraction script".
- 209_T1 [82]-[93] was declared "Search file contents for request keywords", but the search was for a candidate's party name, not request words (it timed out). It is labelled by its reads ("Read a chosen matter's documents in depth"). No stage covers a store-wide search for a candidate's own name.
- Calls between stages refused by the protocol ("No stage is open", "Stage ... is still open") are attached to the next or still-open stage and tagged `tool error` (058_T0, 081_T2, 111_T1, 158_T2, 209_T1, 209_T2). A protocol "Stage check" warning on a call that did run is not tagged.
- Context overflow on the first store-wide scan, which printed uncapped snippets, ended 6 of 24 runs: 034_T1, 058_T1, 111_T2 and all of 130. None of them got a review, so critic = no-review. In passing runs, scans of the same shape stayed within limits (0.7-1.7M chars).
- 209: kept over-inclusion (as in the round-1 note for 209) for naming a matter whose open status was not established. The matter that qualifies surfaced in T0/T2 outputs but was never opened. This is recorded only in failure_point, not as a separate surfaced-not-opened error, because the agent's pick was driven by its date ranking.
- 158_T1 vs 158_T2: same answer outcome (the matter with the executed rider is excluded), but different kinds. T1 read the rider and then excluded it (under-inclusion). T2 never opened it (surfaced-not-opened at the screening stage).
- Critic notes follow the coordinator rule: "(generic flag)" or "(specific flag)" prefix on every flagged-* value. 014_T0's surfaced-not-opened is marked generic, because the reviews named only number ranges of unopened matters.
- Hindsight for "target missed" on 111_T1 [26]-[55] scans and path searches rests on the absence of the log's target marker. The output was grouped or ranked, so the matter may have been left out by the agent's own cap rather than by the pattern.
