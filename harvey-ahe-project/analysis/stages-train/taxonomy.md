# Stage taxonomy: base harness (C0) on the 80 training tasks

Built bottom-up from the training runs only. See `BRIEF.md` for the rules and
`changelog.md` for how it grew.

## Stage groups

Derived from the 240 annotated runs (27 pass, 213 fail): stage-to-stage
transitions (consecutive stages with different names) were clustered by
affinity (transitions between two stages ÷ √(product of their
occurrences)), then checked against each stage's position in the run (0 =
first, 1 = last) and against where its transitions lead. The strongest pairs
were Write → Finish (0.83), store listing → listing reads (0.67), candidate
listing ↔ screening (0.64) and Write → Check (0.56). Store-wide searches
attach to screening only through search → screen loops, so they form their
own group; "List matter folders" sits there because 52 of its 64
transitions are to or from store-wide searches. The two verification stages
are kept apart from screening because they feed the answer: 114 of their 211
outgoing transitions go to the answer group, against 71 of 399 from
screening. Every stage is in exactly one group; group-level transitions are
in `failure_patterns.md`.

"Runs" counts runs containing at least one stage of the group (pass n/27,
fail n/213). Error counts are where first errors (FE, 213) and later errors
(LE, 121) sit.

| Group | Purpose (agent's view) | Stages | Runs: pass | Runs: fail | FE / LE |
|---|---|---|---|---|---|
| Start from the store listing | Get a first view of the store from a whole-store listing (usually silently capped to a few matters), and, in about half the runs, open documents straight from it | List files in the document store; Read documents picked from the file listing | 20 (74%) | 180 (85%) | 39 / 0 |
| Search the whole store | Find candidate matters across all ~266 matters: content greps, file-name searches (request words or document types), text-extraction scans, and the folder listings that set up scans | Search file contents for request keywords; Search file names for request keywords; Search file names for a document type; Scan document text with an extraction script; List matter folders | 27 (100%) | 175 (82%) | 102 / 1 |
| Choose and screen candidates | Pick which surfaced matters to look at, list their files and read openings to judge which fit the request | List files in candidate matters; Screen candidate matters by reading documents | 25 (93%) | 143 (67%) | 39 / 17 |
| Verify the chosen matters | Dig into the matters it has settled on: in-matter greps/snippet scripts and further reads for details and supporting documents | Search within a candidate matter's files; Read a chosen matter's documents in depth | 12 (44%) | 132 (62%) | 4 / 3 |
| Compose and deliver the answer | Compute figures, write the deliverable, check or edit it, finish | Calculate figures for the answer; Write the response; Check or revise the response; Finish the run | 27 (100%) | 197 (92%) | 29 / 100 |

Per stage (pass / fail runs containing it): List files in the document store
19 / 178; Read documents picked from the file listing 8 / 110; Search file
contents for request keywords 15 / 87; Search file names for request keywords
11 / 68; Search file names for a document type 0 / 7; Scan document text with
an extraction script 16 / 104; List matter folders 6 / 25; List files in
candidate matters 14 / 78; Screen candidate matters by reading documents 23 /
141; Search within a candidate matter's files 2 / 71; Read a chosen matter's
documents in depth 11 / 93; Calculate figures for the answer 0 / 5; Write the
response 27 / 197; Check or revise the response 4 / 32; Finish the run 27 /
193.

Conventions (batch 1): a stage's `start` is its first tool-call event and its
`end` is the event just before the next stage starts (so result events are
covered); the last stage ends at the `finish` call, or at the last logged
event if the run ended without one (then it carries a `run ended: …` tag).

Conventions (merge; applied to all 80 tasks):
1. **Where judgement errors sit.** Errors of kind over-inclusion, under-inclusion,
   misstated-facts, hedged-answer and missing-identifier sit on the writing
   stage ("Write the response", or "Check or revise the response" if an edit
   introduced them) whose text first carries them. The logs hold no agent
   reasoning before the answer, so the answer is the first place a judgement
   is observable; the reading stage behind it is named in `why` ("evidence
   seen at [a]-[b]"). Choice errors (surfaced-not-opened,
   listed-document-not-opened, mistyped-path) stay on the stage where the agent
   chose what to open; search errors on the search; miscount,
   over-narrow-filter and incomplete-population on the stage that built the
   list. first_error is the earliest error by stage (ties keep the
   annotator's order). The merge moved 15 errors to a write stage (four of
   them first errors: 058_T0, 058_T1, 140_T2, 238_T0); no run's first error
   changed to a different error.
2. **Hindsight on store-wide listings.** Judged from the log markers on
   non-error results: "List files in the document store" (and "Search file
   names for a document type") showing files of a rubric matter → `target
   surfaced` (or `target partly surfaced` if already given); "List matter
   folders" showing a rubric folder name → `target in folder list only`
   (also when the matter had surfaced earlier); otherwise `none`. Tasks whose
   rubric names no matter numbers (148, 181, 210) keep the annotators' values.
3. **Mixed parallel events.** When one parallel event mixes a store-wide
   keyword search (content grep, file-name glob/find) with reads, listings or
   in-matter greps, the stage is labelled by the store-wide search, whatever
   the call count; whole-store `**/*` listings and globs for one known file are
   not keyword searches. Relabelling does not merge adjacent stages of the same
   name (precedent 114_T2, 223_T2).
4. **Document-type searches.** "Search file names for a document type" when
   most name patterns are document-type or folder-type words the request does
   not use; if the request uses the word (e.g. it asks for the LPA, the
   pleadings, the purchase agreement), "Search file names for request keywords".
5. **Kinds at the boundaries.** A needed matter dropped after being opened →
   under-inclusion (never hedged-answer); a wrong number or detail stated →
   misstated-facts, an omitted number → missing-identifier; a needed document
   shown in the agent's own listing but never opened →
   listed-document-not-opened, never shown → search-miss.
6. **md layout.** Rows and the error block are regenerated from the JSON:
   one `**Later error:**` line per other_error, a `Narrower events:` line under
   any error whose `events` is set, `|` in notes escaped as `\|`.

## Stages

| Stage | What the agent is doing | Typical tools | Added in | Example |
|---|---|---|---|---|
| List files in the document store | Getting an overview of the whole store: listing all files (often silently capped at ~100 files from a few matters), or `ls`/`find … \| head`; includes a failed read of the store folder | glob `**/*`, bash find/ls, read on `documents` | batch 1 | 032_T0 [2]-[3] |
| List matter folders | Listing matter folder names (or counting files per folder) across the store, without keyword filtering | bash find -maxdepth 1, python os.listdir | batch 1 | 028_T1 [5]-[6] |
| Search file contents for request keywords | Running the grep tool (or bash grep -r) over the store for words from the request; often paired with a whole-store glob in the same parallel call | grep (files_with_matches / content), bash grep -R | batch 1 | 072_T1 [2]-[8] |
| Scan document text with an extraction script | Writing a Python/shell script that unzips documents and regex-searches their text across the store (or a range of matters); prone to 60 s timeouts and very large outputs | bash python zipfile/re | batch 1 | 028_T0 [10]-[18] |
| Search file names for request keywords | Matching request words against file or folder paths | glob `**/*word*`, bash find \| grep -i | batch 1 | 003_T1 [14]-[17] |
| Search file names for a document type | Matching file or folder paths across the store against document-type or folder-type words that the request itself does not use (e.g. engagement-letter files, transaction-document or pleadings folders), as a stand-in for what the request asks about; often a per-matter listing of such files | glob `**/<Folder>/**`, bash find \| grep -i, python os.walk | merge (batch 12; also batches 3, 7, 11) | 210_T0 [7]-[11] |
| List files in candidate matters | Listing every file in one or more specific matter folders the agent is considering, or locating a folder's real path | glob `matters/<m>/**/*`, bash find | batch 1 | 003_T1 [18]-[22] |
| Read documents picked from the file listing | Opening documents chosen from the (partial) store listing with no keyword-search lead behind the choice | read | batch 1 | 032_T0 [4]-[15] |
| Screen candidate matters by reading documents | Reading the opening part of documents (engagement letters, memos, filings) from several candidate matters to judge whether each fits the request | read (parallel batches) | batch 1 | 028_T0 [19]-[30] |
| Read a chosen matter's documents in depth | Reading further sections/documents of the matter(s) the agent has settled on, to extract details and supporting documents | read with offsets | batch 1 | 066_T0 [17]-[33] |
| Search within a candidate matter's files | Grep or snippet extraction restricted to one matter folder or one document | grep with matter path, bash python on one file | batch 1 | 061_T0 [15]-[16] |
| Calculate figures for the answer | A short script that computes values for the deliverable (day counts, averages, rates) from figures already read; it does not touch the document store | bash python | merge (batch 10) | 190_T1 [33]-[34] |
| Write the response | Writing the deliverable file | write | batch 1 | 003_T1 [34]-[35] |
| Check or revise the response | Editing the written response, re-reading it, or re-checking a cited path/detail after writing | edit, read response.md or a source, glob, bash | batch 1 | 003_T1 [36]-[39] |
| Finish the run | Calling the finish tool | finish | batch 1 | 034_T1 [23]-[23] |

## Tags (agent-observable)

| Tag | Meaning | Added in |
|---|---|---|
| listing covers few matters | A store-wide listing returned files from only a handful of matter folders (the glob output is capped with no notice) | batch 1 |
| no matches | A search or listing in the stage returned nothing | batch 1 |
| timed out | A command hit the 60 s limit and returned partial output | batch 1 |
| huge output | A single tool result in the stage exceeded ~200K characters | batch 1 |
| file not found | A read used a path that does not exist (guessed or mistyped) | batch 1 |
| tool error | Another tool error (e.g. read on a directory) | batch 1 |
| script error | A shell/Python script failed to run (syntax / heredoc error) | batch 1 |
| mixed intents | Parallel calls in the stage had different intents; the stage is labelled by the dominant one (see note) | batch 1 |
| run ended: context overflow | The run stopped here without calling finish because the context was full | batch 1 |
| run ended: text reply without finish | The run stopped with a plain text reply (no tool call, no finish call); whether a deliverable exists shows from the presence of a write stage. Merges `run ended: no finish call`, `run ended: answer given as chat text`, `run ended: text reply without finish`. E.g. 080_T2 [31]-[32], 141_T1 [14]-[18] | merge (batches 4, 5, 8, 9) |
| output capped | A search or listing (other than the whole-store listing, see `listing covers few matters`) returned exactly its cap: the tools' silent 100-file limit on glob / files-with-matches, or a `head` / `sed -n` line limit the agent set itself, so later matches were cut. Merges `own line cap reached`. E.g. 053_T2 [5]-[6], 195_T0 [5]-[6] | merge (batches 4, 11) |
| binary output | A content grep over .docx files printed compressed document bytes instead of text: non-empty but unreadable. Merges `binary noise`. E.g. 162_T0 [13]-[15], 194_T1 [2]-[4] | merge (batches 9, 11) |

## Hindsight values

| Value | Meaning |
|---|---|
| none | no rubric-named matter involved in this stage |
| target surfaced | a rubric-named matter appears in this stage's search/scan results |
| target partly surfaced | some rubric-named matters appear in the results, others that the same search could have reached do not |
| target in folder list only | a rubric matter appears only as one folder name in a list of all matter folders (no signal for it) |
| target missed | this search/scan was the agent's route to a rubric matter but its results did not include it |
| target opened | the agent listed or read files of a rubric-named matter in this stage |
| decoy opened | the agent listed or read only non-rubric matters in this stage (task names rubric matters) |
| answer passes | the written answer satisfied all criteria |
| answer misses target | the written answer omits a rubric matter (e.g. says none qualifies) |
| answer wrong matter | the written answer names a non-rubric matter in place of the rubric one |
| answer over-inclusive | the written answer asserts non-rubric matters as qualifying |
| answer hedged | the written answer qualifies or narrows its conclusion so it does not answer the question as asked |
| answer lacks matter number | the written answer discusses the rubric matter's documents but never states the matter number a criterion asks for |
| answer misses document | The written answer names the needed matter but omits (or replaces with another) a specific document a criterion requires. Merges `answer lacks proof document`. Added in merge (batches 5, 7); e.g. 137_T0 [51]-[52], 080_T1 [36]-[37] |
| answer misdescribes matter | The written answer names a needed matter but describes it wrongly (client, role, provision), so its criterion fails. Added in merge (batch 4); e.g. 058_T1 [32]-[33] |
| context overflow | this stage's output filled the context and ended the run |

## Error kinds (hindsight)

| Kind | Meaning | Added in |
|---|---|---|
| search-miss | The searches the agent ran could not reach a needed matter (wrong file type, content grep only, timed-out scan) and it neither broadened nor retried another way. Merge: also used when retries all timed out (131_T1, 137_T1) and for a needed document inside an opened matter that no search reached and that never appeared in a listing (080_T1) | batch 1 |
| partial-listing-as-corpus | The agent chose what to read from a capped store listing without any keyword search, treating the few visible matters as the whole store | batch 1 |
| context-overflow | A tool call returned so much text that the context filled and the run ended without a deliverable | batch 1 |
| over-inclusion | The answer asserts matters as qualifying that do not meet the request, typically on keyword hits or skims alone. Merge: also covers a loose reading of a request qualifier after in-depth reads (082_T1, 091, 209) and comparators described as meeting the request (151_T2, was comparators-listed-as-qualifying) | batch 1 |
| hedged-answer | The agent had the evidence but scoped or qualified the conclusion so it does not answer the question as asked. Merge: a matter dropped from the answer is under-inclusion, not hedged-answer (063_T1 remapped) | batch 1 |
| surfaced-not-opened | A needed matter appeared in the agent's own search or scan output, but when choosing what to list or read next it left that matter out and never opened it (e.g. 104_T0 [7]-[13], 167_T2 [28]-[34]) | batch 2 |
| missing-identifier | The agent found and read the right matter and documents, but the written answer omits the matter number (or other identifier) a criterion requires (e.g. 221_T2 [12]-[13]). Merge: when a different number is stated instead, the kind is misstated-facts (125_T0 remapped) | batch 2 |
| under-inclusion | The agent opened a needed matter (listed or read its files, or grepped inside it) or saw its evidence, but the answer leaves it out or counts it as not qualifying: a narrow reading of a qualifier, a judgement from part of the matter's documents (draft, early memo, first lines, email-only greps), or no stated reason. Mirror of over-inclusion. Merges over-exclusion, misjudged-exclusion, opened-but-excluded, opened-then-excluded, dismissed-after-shallow-read and the exclusion uses of misread-matter | merge (batches 3, 4, 6, 7, 8, 12, 13); e.g. 241_T2 [34]-[35] |
| misstated-facts | The answer includes a needed matter or its documents but states something its documents do not support: a detail (date, amount, paying side), its category or bucket, its client or role, or which matter number or folder a document belongs to (e.g. a number printed inside the documents, or results of parallel reads paired with the wrong paths). Merges wrong-detail, misattributed-matter, misattributed-document, misclassification and the misdescription uses of misread-matter | merge (batches 3, 4, 6, 8, 10); e.g. 035_T0 [44]-[45] |
| listed-document-not-opened | Document-level analogue of surfaced-not-opened: a document a criterion requires appeared in the agent's own listing of a matter it was working on, but when choosing what to read it left that document out and never opened or cited it | merge (batch 7; also 199_T1 from batch 11); e.g. 137_T0 [42]-[48] |
| incomplete-population | A count or rate answer rests on a set the agent fixed early that leaves out members of the population the request covers (e.g. the denominator), although every rubric-named matter is present | merge (batch 3); e.g. 017_T0 [20]-[27] |
| miscount | A count or ranking taken from the agent's own listing is wrong: the listing was filtered so it dropped items, or the tally left out groups the listing showed | merge (batch 12); e.g. 210_T0 [19]-[20] |
| over-narrow-filter | A broad search or scan reached every needed matter, but a follow-up filter the agent wrote (exact folder name, file-name pattern) silently dropped one, and the answer was built from the filtered list | merge (batch 11); e.g. 192_T0 [15]-[18] |
| mistyped-path | The agent tried to open a matter that surfaced in its own results but typed the matter number or path wrong, got file-not-found, and dropped the matter | merge (batch 11); e.g. 199_T2 [16]-[22] |
| answer-not-written | The run ended with the answer as a chat message and no deliverable file (context not full), so the judge saw no output. Kept although used once as a later error: no existing kind describes a missing deliverable without overflow | merge (batch 8); e.g. 141_T1 [14]-[18] |

## Issues

- "Screen candidate matters by reading documents" vs "Read a chosen matter's documents in depth" is a judgement call when only one candidate is in play; batch 1 used "in depth" only for reads at offsets or for supporting documents of a matter already settled on.
- `mixed intents` is common because many runs open with a parallel whole-store glob + content grep; batch 1 labels that opener "Search file contents for request keywords".
- "target in folder list only" exists because a full folder-name listing triggers the log's FIRST TIME marker without giving the agent any signal; later batches may prefer "none".
- (batch 2) over-inclusion was also used for 082_T1, where the agent had read the matter in depth and the over-inclusion came from a loose reading of a qualifier in the request, not from keyword hits or skims; a separate kind may be warranted if this recurs.
- (batch 2) An answer that both omits a rubric matter and asserts extra ones (206_T1) gets one hindsight value at the write stage ("answer over-inclusive"); the omission is carried by first_error and the extra matters by other_errors.
- (batch 2) For surfaced-not-opened, the first-error stage is the listing/reading stage right after the surfacing search; its hindsight value describes what was opened ("target opened" when other rubric matters were opened), not what was left out (167_T1 [15]-[20]).
- (batch 2) "Search within a candidate matter's files" was used for snippet-extraction scripts over a named list of agreements from several candidate matters (167); "Scan document text with an extraction script" for a script over one numbered series of matter folders (176_T1 [19]-[20]).
- (batch 2) A provisional answer written before further searching (056_T0 [14]-[15]) is labelled "Write the response" with its own hindsight value, and the later overwrite is a second "Write the response"; the following search is labelled as a search, not "Check or revise the response".
- (batch 2) Recurring agent-observable pattern: grep-tool calls whose glob lacks `**/` (e.g. `*.docx`, `*`) returned "No matches" (104_T1, 206_T2, 221_T1, 201_T1), while `**/*` globs returned hits; these empty greps account for several search-miss first errors. Tagged only as `no matches`.
- (batch 2) "target in folder list only" was kept for full folder-name listings (167_T0 [12]-[13], 056_T2 [14]-[15]); a folder listing after the matter had already surfaced got "none" (104_T2 [5]-[6]).
- (merge) `answer-not-written` was kept although it is used once and only as a later error (141_T1): the closest existing kind, context-overflow, would state a false cause. Its run also carries `run ended: text reply without finish` and has no write stage.
- (merge) `dismissed-after-shallow-read` was merged into under-inclusion rather than kept: opened-but-excluded and opened-then-excluded already described exclusions after partial reads, and depth of reading cannot be told apart reliably from the logs. How much was read is kept in `why`.
- (merge) `binary output` is likely under-tagged in batches 1-2, and the recurring pattern "store-wide grep hits are .eml lines only" (batches 3-13 Issues) has no tag; both are visible only by reading results.
- (merge) Parallel results that come back in a different order from the calls (035_T0, 125_T2, 149_T1, 151_T0) underlie several misstated-facts errors; no tag records it.
- (merge) The doc-type relabel rule (convention 4) was applied by comparing pattern words with the request text and then reviewing borderline stages by hand (154_T0, 141_T2, 149_T1, 125_T2, 162_T1 kept as request keywords); a few remaining "request keywords" stages may still lean on derived document-type words.
