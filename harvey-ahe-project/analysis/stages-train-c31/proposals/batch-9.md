# Batch 9 proposals (tasks 047 092 137 167 170 185 240 247)

## NEW names

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|
| stage | NEW: Rank candidate matters without tool calls | A stage the agent opens and closes with no tool call between stage_start and stage_end. Its summary ranks or tallies candidates it has already read (for example by date), so the choice of answer is made in the summary text alone. | 247_T0 [60]-[63], [64]-[67] (agent's name "Tally matters and rank by recency", which the reviewer suggested; run fails, 0/3) | "Calculate figures for the answer" needs a script. Every other stage needs a store or file call. Labelling the span by the next stage ("Write the response") would hide that the decision was made in this span. It occurs once, in one run; merge it into another stage if no other batch sees it. |

No new tags, hindsight values or error kinds.

## Agent-declared new stages mapped to existing stages

These spans have `agent_new` set, and their notes start with `declared: new: <name>`. Names with task words are masked in notes and md (`<practice area>`, `<deal>` and so on); the JSON keeps the agent's exact text.

- **Scan document text with an extraction script**
  - Re-querying, aggregating or reconciling a saved scan: "Rank all comfort-letter matters from scan file" (047_T0), "Review full scan output" (047_T1), "Aggregate scan hits per matter" (092_T0 attempt 2, 137_T0), "Validate scan recall" (092_T1), "Verify scan coverage and triage all matters" (167_T2), "Build full per-matter candidate pool" (247_T1).
  - New store-wide scans: "Background batched scan…" (167_T0), "Widen coverage…" and "Chunked coverage rerun" (185_T1), "Cross-series client check" (185_T2, run after writing), "Store-wide specific performance sweep" (137_T0), "Widen candidate coverage…" (247_T1).
- **Search file names for request keywords**: "Aggregate scan hits per matter" attempt 1 (092_T0, which builds the set from file names); "Store-wide … coverage check" (092_T0, after writing); "List files in remaining surfaced matters" (092_T1, the first event of the span); "Cross-matter cooperation sweep" (247_T2).
- **Screen candidate matters by reading documents**: "Verify delivery in candidate matters" (047_T1), "Verify candidate Tax matters" (240_T1), "Batched text scan per matter" (247_T2, where no scan was run, only reads), "Complete cooperation comparison" (247_T2).
- **Read a chosen matter's documents in depth**: "Confirm absence of executed letter in <matter>" (047_T2), "Targeted extraction…" attempt 2 and "Direct agreement verification" (167_T0), "Read executed agreements for candidate deals" (167_T2), "Final cooperation verification" and "Verify adjacent newer matter" (247_T2).
- **Search within a candidate matter's files**: "Finalize qualifying matters" (092_T1), "Targeted extraction of consideration and governing law" (167_T0).
- **List files in candidate matters**: "List files in remaining candidate matters" (185_T2), "List files in remaining surfaced matters" (247_T1), "List folders and read proof documents…" (167_T2).
- **Check or revise the response**: "Spot-check response claims against sources" and "Citation and matter-ID consistency check" (047_T2), "Per-matter criteria audit" (092_T0), "Final primary-source verification" (185_T1), "Verify execution evidence…" and "Finalize Harbor Point execution evidence" (240_T0), "Source-to-response fact diff" (247_T0).

Many of these names repeat a "Reviewer suggests a new step: '<name>'" line word for word: 047_T2 ×2, 092_T0, 185_T1 ×2, 185_T2, 247_T0 ×2. The agent adopted all of them except 240_T2's "Store-wide recency cross-check", which was never run.

## Issues

- **label_check / label_check_end** (coordinator convention, applied to all eight tasks):
  - `label_check_end` = `followed` when the agent's next stage doing that kind of work was declared X, including when the next stage was simply declared X right after the note (047 ×3, 092_T0, 137_T0, 137_T1, 170_T2, 247_T1).
  - It is `ignored` when later work of that kind went under a label other than X. That includes labels the agent named itself, which I did not keep apart from keeping the old label (047_T2 [94]-[100], 092_T0 [135]-[146], 240_T1 [14]-[19], 247_T1 [80]-[94]).
  - It is `none` when no later work of that kind happened. This was the usual result for "List matter folders" notes on full per-file inventories.
  - Totals: start-of-stage notes 0 followed / 22 ignored; end-of-stage notes 8 followed / 12 ignored.
  - Several `followed` cases are stages whose label was already right (a path search the classifier called a scan, followed by a real scan). The count shows that the agent declared X next, not that the note changed what it did.
- **Full per-file inventories.** A script that prints every file of every matter, with counts, stays "List files in the document store", even when it was declared "List matter folders" (047_T1 [8]-[13]) or the end note called it folder listing (047_T0, 092_T2, 167, 170_T2, 247_T0). Only count or name listings were relabelled "List matter folders".
- **Harness lists of surfaced but unopened matters** are treated as part of the review when setting `critic`. They give "(specific flag)" when the list names a needed matter (047_T0, 047_T2, 092_T0, 170_T0, 170_T1, 170_T2, 240_T0, 240_T2). The lists are capped at 40 matters, so later-numbered needed matters were often not in them.
- **Wrong-matter answers after surfaced-not-opened** (240 all runs, 247_T0, 247_T2) get no separate over-inclusion error: the matter that should have been named was never opened, so the wrong pick follows from the first error. 240_T0 changed its answer between two later-dated candidates during checking.
- **Splits.** Three spans were split at a call boundary: 240_T0 [108]-[113] / [114]-[119] (a full rewrite inside a declared verification stage), 240_T1 [26]-[31] / [32]-[47] (a scan, then in-depth reads), and 092_T1 [74]-[77] / [78]-[113] (a path regex, then about 25 reads).
- **Empty spans.** 185_T1 [75]-[78] ("Chunked coverage rerun", no tool call) was labelled by its declared intent, the scan stage, because attempt 2 ran the scan. 247_T0 [60]-[67] got the NEW stage above.
- **167_T1 [24]-[36]** was declared screening but relabelled "Read documents picked from the file listing": the agreements were chosen from a full file inventory after every scan had failed, with no search lead.
- **137 proof memo.** The log lines were cut before the file name, so the raw trace was used to confirm that the status memo appeared in T0's and T1's own listings of the matter (listed-document-not-opened). T2 read it inside its snippet stage.
- **092_T1.** The missing proof document (a standstill settlement agreement) never appeared in any of the run's outputs, so it is `search-miss` on the in-matter extraction stage, as in the 080_T1 precedent.
- **Stage-check warnings.** Harness "Stage check: this call looks like …" warnings returned with a result (137_T0 [21], 137_T1 [95], 170_T1 background polls) are not tagged `tool error`.
