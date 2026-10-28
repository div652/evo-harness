# Batch 6 proposals (tasks 092 093 102 114 121 125; all 18 runs failed)

No new stages, tags or hindsight values were needed; every call fit the existing 13 stages.

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|
| error kind | NEW: misjudged-exclusion | The agent opened a needed matter (or saw its evidence in grep or scan lines) but judged that it does not qualify, or left it out of the answer, although it does qualify | 125_T1 [28]-[29] (read the first matter's pleadings and memo, then expressly excluded it); also 092_T0, 114_T1, 121_T1, 121_T2, 125_T2 | surfaced-not-opened requires that the matter was never opened; hedged-answer is about narrowing the overall conclusion; over-inclusion is the opposite direction |
| error kind | NEW: misstated-facts | The answer includes a matter the agent read but misstates a key fact the documents give: which side paid, the amount, or which matter folder a document came from | 121_T1 [32]-[33] (reversed paying side for several read agreements); 125_T2 [57]-[58] (pleadings from one parallel batch of reads attached to the other folders' matter numbers); also 121_T2 | missing-identifier covers an omitted number, not a misstated fact; the other kinds are about which matters are found or asserted. Batch 10's proposed "wrong-detail" looks like the same idea, so the two could be merged |

## Issues

- 125: the documents of one rubric matter (1045-00004) print another firm matter number (1022-00005, itself a rubric matter) in their headers. 125_T0 copied the printed number. This was recorded as missing-identifier (a later error), because the folder number the criterion asks for is missing. A misstated number fits misstated-facts or batch 10's "wrong-detail" just as well.
- 125_T2 [18]-[24]: the results of six parallel reads came back in a different order from the calls. The agent then attached at least two pleadings to the wrong matter folders. This is an agent-observable hazard (results are not labelled by path) that no tag covers.
- Mixed parallel events where reads outnumber a single consequential search (114_T0 [5]-[9], 125_T1 [13]-[17]) were labelled by the dominant intent, which is reading. For 125_T1 the first error was narrowed with `events` [13]-[14] to the grep. That gives a search-miss on a stage named for reading, which reads oddly. One option is to allow splitting parallel calls at the same event number.
- Grep tool hits on the .docx-heavy store are email files only (114_T0 [12]-[13]: every hit is .eml). This matches batch 10's Issue and is the main cause of 114_T0's search-miss. It is noted, not tagged.
- A capped whole-store listing that happens to start with a rubric matter (125, all three runs: 1045-00004 sits at the top of the listing) got "target surfaced", then "target opened" for reading it. "target in folder list only" was defined for folder-name lists, so it does not fit exactly.
- Several runs carry more than one later error at the same write stage (e.g. 121_T1: misstated-facts, misjudged-exclusion and over-inclusion). The schema allows this, but the md marks the row only once.
- Same client, different matter number: 092_T1/T2, 114_T1 and 121_T1 named a sibling matter of the right client in place of the qualifying one. These were filed under over-inclusion or surfaced-not-opened. If this recurs, a dedicated kind (e.g. "sibling-matter") would make it countable.
- 102_T1 (4/5) and 114_T1 (12/17) found the needed matters and failed mainly on precision (draft-only or extra matters). Their first error is over-inclusion at the write stage (102_T1) or a search-miss for the single unreached matter (114_T1).
