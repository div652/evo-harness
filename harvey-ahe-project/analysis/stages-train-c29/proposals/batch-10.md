# Batch 10 proposals (tasks 052 091 121 151 194 206 210 247)

## NEW names

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|
| (none) | | | | All stages, tags, hindsight values and error kinds fit existing names. |

## Issues

- Stage-protocol rejections. A `stage_start` rejected with "Stage '…' is still open" did not open a stage; its events stay in the open stage until that stage's `stage_end` (052_T2 [111], 121_T1 [95] [113], 151_T2 [54] [89], 194_T2 [77]). A call rejected with "No stage is open" is folded into the following stage, and the note says so (052_T0 [105], 052_T2 [135], 091_T1 [73], 121_T0 [62] [70], 210_T1 [72]). A second `stage_end` after the review (151_T2 [76]) returned an empty result and stays in the write stage.
- Declared stages were often mislabelled, so `declared:` notes are common. The most frequent cases:
  - "List files in the document store" (attempt 2) was really a matter-folder enumeration and is labelled "List matter folders".
  - "Read a chosen matter's documents in depth" was a one-document-per-matter pass over 20-37 candidates and is labelled "Screen candidate matters by reading documents".
  - "Scan …" was a listing of a named candidate set and is labelled "List files in candidate matters".
  - Declared spans were split at tool-call boundaries when a scan, a listing and reads followed one another.
- Critic field. Almost every review flags "~60 surfaced matters never opened or listed", which is generic. We counted it as a flag only when the error was an unopened surfaced matter (flagged-ignored, or flagged-fixed-partly when the agent reopened the stage and screened again). A raw-trace-only harness list of unopened matters sometimes names the matter (194_T0); in 121_T0 it does not. Precision (over-inclusion) errors were usually flagged by the write review as "possible over-inclusion" and left unchanged (flagged-ignored). Under-inclusion of an opened matter was never flagged (052_T1, 194_T1, 194_T2). 210 passed in all three runs although every review flagged its prefix-as-client counting.
- 247_T0 uses listed-document-not-opened for a matter whose files appeared in the agent's eight-matter listing but which it never read. By the under-inclusion definition, listing a matter's files counts as opening it, so under-inclusion on the write stage was the alternative. The choice stage was kept per convention 5 (a document shown in its own listing).
- 052 has three errors in one write stage (an omission, over-inclusion and misclassification). Following the 206_T1 precedent, first_error is the omission when it sits on the write stage, and the extras go in other_errors.
- 210's rubric names no matter numbers, so every search stage has hindsight "none".
- Coordinator rule applied to all eight tasks. Every error carries a `critic_note`. On flagged-* values it starts with "(generic flag)" or "(specific flag)": a flag is specific only when the review named the matter, document or exact cause.
  - Generic: 052 (all flagged errors), 121_T0 first error, 121_T1 over-inclusion, 151_T2, 194_T2 over-inclusion, 247_T2.
  - Specific: 091_T1, 121_T0 over-inclusion, 121_T1 misstated-facts, 194_T0 (both), 194_T1 over-inclusion, 206_T0, 206_T1, 247_T0, 247_T1 (the review named the line cap that cut the output).
  - Calls refused by the stage protocol, including rejected stage_starts, give their stage the tag `tool error`.
