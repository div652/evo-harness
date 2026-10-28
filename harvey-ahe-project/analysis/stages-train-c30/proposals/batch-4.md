# Batch 4 proposals (round 3, campaign 30)

Tasks: 057 080 125 131 158 162 211 221.

## NEW names

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|
| (none) | | | | |

## Issues

- label_check reading used throughout: `ignored` when the span (or part of it after a relabel or split) did the work the "Check the label" note described for a suggested stage; `followed` when the agent closed the stage and opened the suggested one before that work; `none` when the work matched the declared label. Openers that pair the whole-store glob with a capped folder sample (131, 162_T0) stay "List files in the document store" with `none`.
- Most notes are not applicable: the notes shown at "List files in candidate matters", "Screen candidate matters" and "Read a chosen matter's documents in depth" rarely describe what the agent then did. Ignored notes cluster on the second store-listing attempt, where the agent lists all matter folders or runs a store-wide file-name filter under the store-listing label (221_T0/T1/T2, 162_T1).
- 221_T2 [20]-[23]: the only `followed` in 131/162/221. The agent opened a content-search stage, closed it at once with no tool call ("needs text extraction") and opened the extraction stage the note suggested. The span holds only stage_start/stage_end calls and keeps its declared label.
- 162_T2 vs 162_T0: both answers describe the same later candidate as "a completed traditional offering, but later" in the comparison section. The judge passed T0 and failed T2 on precision, so the T2 first error (over-inclusion) rests partly on judge variance.
- Check-stage reviews in several tasks say "do not add or drop matters". This was coded as not-flagged (or generic), never review-endorsed, because the reviews did not push toward the specific mistaken decision.
- check.py's task-word list catches common words in notes (e.g. "fund", "reorganization"), so 057 notes use paraphrases.
- 080_T1: the needed matter appeared only in a keyword-filtered listing that showed two of its files, and the proof memo was not one of them. Following convention 5, this run uses under-inclusion on the write stage. Round 1 coded the same pattern on this task (080_T1) as search-miss.
- 057_T2 [88]-[99]: a declared scan stage is split at [94] into a scan span and a screening span. The `ignored` label_check sits on the span that carried the stage_start.
- 211 (all runs): the answers lead with a larger acquisition loan raised in a merger matter and rank the required matter's loan as a smaller comparison after reading it. Coded under-inclusion on the write stage; no existing kind covers misjudging which deal counts as the firm's own financing. 211_T2's critic is review-endorsed: the last reading review told the agent to lead with the acquisition package.
- 125_T1 and 211_T1: parallel read results were paired with the wrong paths, giving misstated-facts. In 125_T1 a later check edit also added an extra matter that carried the moved content, coded as a separate over-inclusion on the check stage.
- 125_T2: an extraction script over 55 listed pleadings is labelled "Search within a candidate matter's files" (round-1 rule for named lists). Its label_check is `ignored` because the note pointed to the extraction-scan stage.
- 158_T2: a matter was excluded on the strength of scan snippets alone and never opened. Coded surfaced-not-opened per convention 5, not under-inclusion.
- 125_T0 and 158_T0: the review named the doubtful document, the agent re-read it and kept the matter. Coded flagged-fixed-partly.
