# Batch 7 proposals (tasks 046 066 093 141 173 179 199 240)

## NEW names

None. All stages, tags, hindsight values and error kinds use the frozen taxonomy.

## Issues

- **Missing document after reading it (066_T2).** The answer names the right matter and five of its documents but leaves out one the agent had read. I labelled it `missing-identifier` ("or other identifier") with hindsight `answer misses document`. No kind says "document read but not cited". If this recurs, a document-level mirror of under-inclusion may be worth adding.
- **Overflow after a survived huge output (179_T0).** A 3.6M-char scan at [10]-[11] did not end the run; the run ended later, after an 11-read batch (~175K chars) at [28]-[39]. I put first_error (context-overflow) on the scan stage, as the main oversized output, and tagged the run-ended stage. Others may place it on the read batch. Similar survived outputs that did not end the run: 141_T1 [53] (1.38M chars), 240_T0 [27] (2.25M). The harness seems to truncate some huge results before the model sees them.
- **Stage-check warnings vs refusals.** I tagged `tool error` only on calls the protocol refused: a stage_start while a stage was open, or an edit with no stage open (066_T2, 141_T0, 141_T1, 173_T2, 240_T0). Calls that ran but came back with a "[Stage protocol] Stage check: this call looks like…" note are not tagged (141_T0 [37]-[45], 173_T2 [39]-[43], 240_T0 [25]). The agent sometimes treated these warnings as blocking (173_T2 attempt 3).
- **Declared names.** Common relabels:
  - Declared "List files in the document store" (attempt 2) when the work was a folder-name listing → List matter folders.
  - Declared the same when it was a file-name filter → Search file names for request keywords.
  - Declared "Read a chosen matter's documents in depth" for first reads across many candidates → Screen candidate matters by reading documents.
  - Declared "Search within a candidate matter's files" or "List files in candidate matters" for store-wide or range-wide scripts → Scan document text / file-name search.
  - Declared "Search file names for a document type" when the words were request words (diligence, tax/indemnity, agreement) → request keywords (convention 4).
- **Critic.** Most reviews flag "~60 surfaced matters unopened" and name example matters. I marked these `(generic flag)` unless the named examples included the needed matter or the filter or exclusion behind the error. Specific flags: 141_T0 (named qualifying matters), 141_T1/T2 (named the filter), 046_T2 (named the not-closed exclusion), 240_T2 (named the low-numbered range). Even specific flags were rarely acted on.
- **Recurring pattern: recency by matter number** (240, all runs; 066 partly). Agents treat higher matter numbers as more recent and restrict checks to them. The taxonomy has no tag for this; the cases fall under surfaced-not-opened.
