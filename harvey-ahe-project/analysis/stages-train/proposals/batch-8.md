# Batch 8 proposals (tasks 140 141 148 149 151 154, all runs failed)

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|
| error kind | dismissed-after-shallow-read | The agent opened a needed matter but read too little of it (one memo, or only its file names) to find the qualifying evidence, and excluded it from the answer | 140_T2 [25]-[30] | surfaced-not-opened requires the matter never to be opened; over-inclusion/hedged-answer describe other answer faults; the matter here was opened and then judged out on thin reading |
| error kind | answer-not-written | The run ended with the answer as a chat message (termination: no tool calls) and no deliverable file, so the judge saw no output | 141_T1 [14]-[18] | No kind covers a missing deliverable other than context-overflow, and the context was not full here |
| error kind | misattributed-document | The answer attaches a document's content (parties, terms) to the wrong matter; here the agent paired a batch of parallel reads with the wrong matters | 149_T1 [34]-[42] | missing-identifier is about an omitted number; answer wrong matter is about choosing the wrong matter, not mislabelling a right one |
| error kind | comparators-listed-as-qualifying | The answer names the right matter but also describes ranked-out comparator matters as meeting the request's conditions, and the precision check counts them as asserted answers | 151_T2 [23]-[24] | over-inclusion means asserting non-qualifying matters as answers on loose evidence; here the agent explicitly ranked them out and its facts were right |
| tag | run ended: answer given as chat text | The run stopped without a finish call because the agent replied in chat instead of calling a tool | 141_T1 [14]-[18] | The only run-ended tag is context overflow; check.py also needs a tag starting with "run ended", which this NEW-prefixed name cannot satisfy |

## Issues

- 141_T1 makes check.py report "no finish and no run-ended tag" in addition to the unknown NEW tag; both come from the NEW tag above (its prefix "NEW: " stops it from starting with "run ended").
- Parallel result order: in several logs the results of a parallel batch appear in a different order from the calls (e.g. 149_T1 [34]-[42], 151_T0 [8]-[12]). In 149_T1 the answer's mislabels match a positional pairing of calls and results. Annotators should read result content, not position, when deciding which matter a result belongs to.
- Loose surfacing: in 140_T1 [9]-[10] and 154_T0 [2]-[4] the matter appears only through a very loose match (an "r.?w" pattern hitting "escrow" file names; a grep mixing the request term with generic deal words, about 250 hits). By the brief's rule these were labelled surfaced-not-opened at the next opening stage, but the agent had almost no signal; a "weakly surfaced" hindsight value may be warranted.
- Task 148: rubric titles carry no matter numbers, so the log header says "none named" and there are no surfacing markers; surfacing was checked in the raw traces (the matter appears in 148_T2 [5]-[10] only).
- Store-wide file listings that happen to include rubric matters (141_T2 [2]-[6], several globs by file type) were given hindsight "none", like other capped listings; "target in folder list only" is defined for folder-name lists.
- For a single-answer task, naming the wrong matter also fails the precision criterion; that failure was not recorded as a separate over-inclusion error (148, 151_T0/T1, 154). Over-inclusion was recorded only where the answer listed extra matters beyond those needed (141_T2, 149_T0, 149_T2).
- 141_T0/T2 answers narrowed the rate's denominator to the signed agreements they read; this was treated as a result of the search miss rather than as hedged-answer.
