# Batch 9 proposals (tasks 048 082 114 149 185 190 201 243)

## NEW names

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|
| error kind | missing-detail | The agent found, read and named the right matter (number, date and the like correct), but the answer leaves out a descriptive qualifier of the matter that a criterion requires, although the documents it read state it. | 185_T2 [102]-[107] | missing-identifier is defined for an omitted matter number or other identifier (and convention 5 limits it to omitted numbers). misstated-facts needs a statement the documents do not support, and hedged-answer needs a qualified conclusion. Here nothing wrong is stated: a required descriptive element is left out. |

## Issues

- **Critic field.** I applied the coordinator's rule to every run in this batch. A review that names the problem only in generic terms ("~60 surfaced matters unopened", "possible over-inclusion") still gets a `flagged-*` value, with `critic_note` "(generic flag) …". A review that names the matter, document or mechanism gets "(specific flag) …". `not-flagged` and `no-review` have an empty `critic_note`. The md shows the note on a `**Critic (first error):**` / `**Critic (later error):**` line under each error line. Almost every screening and write review carries the generic "~60 surfaced matters unopened" warning, so flagged-*/generic covers many errors the critic never singled out (114_T1, 190_T0, 190_T1).
- **Calls refused by the stage protocol.** Calls rejected because no stage was open, which sit between one stage_end and the next stage_start, are put in the following stage, where the agent repeats them, and that stage gets the tag `tool error`: 114_T0 [67]-[69], 114_T1 [104]-[105], 149_T1 [110]-[111], 190_T2 [166]-[167], 201_T0 [81]-[82] and [114]-[115], 243_T0 [91]-[95]. A refused stage_start while a stage is still open stays in that open stage (201_T1 [84], 201_T2 [105]).
- **Stages declared with no work.** Twice the agent opened a new stage, made no tool call and closed it with a summary of the previous stage's work, because it had never closed that stage (048_T1 [104]-[107] for check-after-write, 082_T2 [38]-[41] for in-depth-after-snippet-script). I merged each one into the preceding stage, which is what the review actually assessed, and said so in the note.
- **Relabelled declared stages.** These were the most common relabels:
  - "List files in the document store" attempt 2, when the agent actually enumerated folders → List matter folders.
  - "Read a chosen matter's documents in depth", when the agent was reading several candidates to decide which qualify → Screen candidate matters by reading documents.
  - "Search file contents for request keywords", when the work was a Python extraction script → Scan document text with an extraction script.
  - "Calculate figures for the answer" attempt 3, when the agent opened source documents (190_T2 [186]-[194]) → Read a chosen matter's documents in depth.
- **Splitting declared spans.** Some declared spans held a search followed by reads, or a scan followed by a file-name fallback. I split these at the tool-call boundary: 082_T1 [14]-[23], 114_T1 [35]-[80], 114_T2 [14]-[23] and [54]-[72], 149_T0 [52]-[81], 149_T1 [2]-[13], 185_T2 [22]-[51].
- **Hindsight when an answer is incomplete.** "answer misdescribes matter" was used for 185_T2, where a required qualifier is omitted rather than stated wrongly. No value covers "right matter, incomplete description".
- **Judgement call: document-type vs request keywords.** 190_T1 [14]-[19] was kept as "request keywords" (declared). The patterns mix document-type words (merger, purchase, business combination) with request words (signing, closing), so convention 4 is borderline there.
- **Where the first error goes.** 243 has three runs that miss the same matter for three different reasons (timed-out scan not rerun, .docx-only scan, exclusion after an opened engagement letter). 114_T0's first error is an over-narrow display filter: the full file-name list was saved to a file, but only lines for already-named matters were printed. I used over-narrow-filter for this even though the list on disk held the matters.
