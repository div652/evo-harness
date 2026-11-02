# Batch 1 proposals (tasks 028 032 053 104 148 176 184 200)

## NEW names

None. Every stage, tag, hindsight value and error kind comes from taxonomy.md. The 69 agent-defined stages (declared "new") were all mapped to existing stages, with `agent_new` set and the note starting `declared: new: <name>`.

| kind | name | definition | example | why no existing name fits |
|---|---|---|---|---|

## Issues

- **Agent-defined stages, by function.** Most of them fall into three groups:
  - Re-tabulating, filtering or reconciling a saved scan output without new store reads. These were mapped to "Scan document text with an extraction script": 032_T0 [54]-[71], 028_T1 [32]-[45], 176_T0 [40]-[53], 184_T0 [33]-[42], 104_T2 [54]-[71]. The same function also occurs under declared labels (053_T1 [114]-[119], 200_T2 [47]-[54]). The taxonomy defines the scan stage as unzipping store documents. If this pattern keeps growing, a stage such as "Tabulate saved search output" may be warranted. It was not proposed here because it is part of building the scan's candidate pool.
  - Extra screening of "remaining" candidates, mapped to Screen (028_T0, 028_T1, 148_T0, 176_T0, 184_T0).
  - Post-write verification passes ("final consistency check", "exclusion spot-check", "recency cross-check", "date-ranking cross-check"), mapped to "Check or revise the response" (032_T2, 104_T1, 104_T2 five, 148_T0 five).
  - One "Unsupported-format coverage check" (200_T2 [61]-[66]) was a file-type census plus a file-name search for the entity name. It was labelled "Search file names for request keywords" under convention 3.
- **Redacted agent names.** Agent stage names containing task content (practice-area words, matter numbers, client names) are redacted in the note (`<topic>`, `<matter>`, `<client>`) so that check.py passes. `agent_new` keeps the exact name. Examples: 032_T0 "List and read <topic> matter files", 032_T2 "<matter> full-folder verification", 028_T1 "Resolve <client> scope".
- **Split spans.** Spans with two clear intents were split at a tool-call boundary:
  - 032_T0 [72]-[75]/[76]-[88] (path search, then reads) and [89]-[92]/[93]-[102] (scan, then screening);
  - 104_T2 [103]-[106]/[107]-[119] (in-matter script, then in-depth reads);
  - 176_T1 [32]-[35]/[36]-[54] (listing, then screening reads);
  - 184_T2 [54]-[57]/[58]-[99] (listing of five matters, then screening reads of nine others).
  The `agent_new` field and the label notes stay on the piece where they apply. The end note sits on the last piece.
- **`label_check_end` scoring.**
  - `followed`: the next stage doing the noted kind of work was declared X.
  - `ignored`: the agent kept the old label, or declared another stage (including a "new" one) for that work. Both cases are counted as not following.
  - `none`: no later work of that kind. Source re-reads after the write were not treated as the same kind of work as screening before the write, so screening notes followed only by checks are `none`.
  - Totals over 24 runs: `label_check` followed 0 / ignored 28; `label_check_end` followed 8 / ignored 19.
- **The classifier's X is sometimes wrong.** Examples: "Calculate figures" for tabulating scan output (028_T0 [47]-[54], 053_T1 [114]-[119], 200_T2 [47]-[54]); "Scan document text" for a path regex (032_T1 [14]-[19], 028_T2 [14]-[19]); "Check or revise" for post-write in-depth reads (184_T1). The followed/ignored counts measure whether the agent complied, not whether the note was right.
- **Context overflow in 148_T2.** The error was placed on the first scan stage ([8]-[13], about 3.3M characters, flagged by the review), following the c29 precedent 179_T0. The run then continued for 90 events and ended at a later read batch; the large listing (166K) and read (87K) stages are the alternative placement.
- **148 hindsight.** The log header names no matters, so hindsight values were judged against the matter that the criteria require.
- **Answers naming the wrong "latest" matter** were scored by what the named matter is:
  - 104_T1: over-inclusion. The named litigation matter does not qualify; its terms are known only from an affidavit.
  - 148_T1: under-inclusion. The named deal qualifies on everything except recency, and the error is dropping the most recent deal, which the agent had opened (a letter read, its folder listed).
- **Errors in the check stages.**
  - 028_T2: both errors (first and later) are under-inclusion edits made in check stages. Both are `review-endorsed`: the reviews called the standby matter a weak-grounds inclusion and then called its restoration a reinstatement.
  - 148_T0: the over-inclusion is `review-endorsed` because reviews asked the agent to name and date the comparison deals.
- **`listed-document-not-opened` in 053_T1.** The kind was applied where the "listing" was the agent's own scan output, which printed file names per matter ([28]). The definition names a listing of a matter the agent was working on.
- **One identifier lookup.** 176_T2 [99]-[106] (declared new "Resolve surfaced identifier") was labelled "Search file contents for request keywords": a store-wide path and content grep for a policy number the review had raised. No stage fits a store-wide lookup of a non-request string.
- **Repeated pattern in 184.** Store-wide scans showed most or all qualifying matters, and every run then read a hand-picked handful (surfaced-not-opened). The reviews flagged hand-picking only in generic terms, except in T1, where the guessed number range was named.
- **Check-stage path scripts.** Many check stages opened `response.md` from the working folder instead of `output/` (FileNotFoundError). Following round-3 precedent these are tagged `file not found`.
