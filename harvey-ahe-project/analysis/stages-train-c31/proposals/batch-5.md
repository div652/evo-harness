# Batch 5 proposals (tasks 014 063 081 091 126 155 201 209)

## NEW names

None. Every stage, tag, hindsight value, error kind and critic value comes from taxonomy.md. Every agent-declared stage (stage "new") fits an existing stage, so each carries `agent_new` and a note that starts `declared: new: <name>`.

| kind | name | definition | example | why no existing name fits |
|---|---|---|---|---|

Agent-declared stages and the labels they were given (runs and outcomes):
- **Scan document text with an extraction script.** These scan, re-filter or tabulate saved scan output, or survey the store by script.
  - 014 (all fail): Targeted store-wide scan with saved results; Derive candidate set from saved scan; Store-wide covenant scan of executed credit agreements (its scan part); Verify TLB matters via executed agreements; Verify scan completeness and aggregate per-matter hits; Verify final covenant-lite count (its scan part); Aggregate scan hits per matter.
  - 063 (all fail): Scan XLSX and PPTX text; Rescan with verified coverage (first part); Rerun the matter-wide scan (scan part); Per-document governing-term intersection scan (scan part).
  - 081 (pass): Extract complaint dates per candidate.
  - 091: Batched L&E non-compete scan (T0, pass); Background chunked text scan (T1, pass); Broad sweep for long non-competes (T0, pass).
  - 155: Build complete per-matter hit index (T0, fail); Full-store operative-covenant verification (T2, fail).
  - 201: Rescan with broader coverage and reconcile (T0, pass).
  - 209 (all fail): Store-wide opening-date and status scan (T0); Store-wide matter age and status survey (T1); Verify older matters' open status (T2, its grep part).
- **List files in candidate matters.**
  - 014: List files in the unlisted matters (T0 attempt 1); Re-list unlisted and empty matter folders; List files in all surfaced matters.
  - 063 T0 (fail): List files in all surfaced candidates.
  - 209 T2 (fail): Read remaining candidate matters' opening and status documents (its listing part).
- **Search within a candidate matter's files.**
  - 014: List files in the unlisted matters (T0 attempt 2); Direct covenant-article verification.
  - 081 (pass): Verify complaints per matter; Verify recency across willful-infringement matters (attempt 1).
  - 155: Verify unopened matters and signature evidence (T1, fail); Per-matter executed-agreement verification (T2, fail).
  - 209 T1 (fail): Resolve 1002-00001 closing status.
- **Screen candidate matters by reading documents.**
  - 014: Verify candidate coverage and proof documents.
  - 063: Verify all governing-document intersection matters; Verify executed LPAs in surfaced matters.
  - 209 (all fail): Screen older unopened matters for open status; Screen 1001/1002 older matters; Read unread matters' status documents; Read status docs for all earlier-opened matters.
  - The read parts of split spans in 063, 091, 209 and 014.
- **Read a chosen matter's documents in depth.**
  - 081 (pass): Verify recency across willful-infringement matters (attempts 2-3).
  - 063 (fail): Close remaining verification gaps.
  - 209: Verify oldest open candidates (T1, fail); Verify status of all pre-Feb-2023 and undated matters (T0, fail).
- **Check or revise the response.**
  - 014 (fail): Final consistency read; Reconcile inclusion and exclusion tables; Read covenant clauses for included facilities.
  - 063 (fail): Full-file citation and exclusion audit.
  - 081 (pass): Verify cited sources and recency claim.
  - 091 (pass): Claim-to-source reconciliation; Final included-matter spot check; Final settlement outcome check.
  - 201: Check Dunmore 1016-00009 folder (T0, pass); Cross-check response against listings (T1, pass); Final evidence and output check (T1, pass); Path and set consistency check (T2, fail).

## Issues

- **Label-check fields.** Following the coordinator's update, each stage has two fields:
  - `label_check` scores the "Check the label" note shown at that stage's stage_start.
  - `label_check_end` scores the "Label: these calls looked like 'X'" note in that stage's stage_end.

  Totals over 8 tasks:
  - Start notes: followed 0, ignored 40.
  - End notes: followed 9, ignored 36.

  When a declared span was split, the start-note verdict sits on the piece that did the suggested work and the end-note verdict on the piece that holds the stage_end (126_T1, 201_T1, 209, 063).
- **Truncated Label notes.** Several end-of-stage Label notes are cut in the logs ("Label:…(+NNN)"). Stage X was taken from the raw trace in these cases: 014_T2 [98] and [113], 063_T2 [163], 081_T1 [111], 126_T1 [119], 126_T2 [59], 209_T1 [42], 155_T2 [46] and [80].
- **How end notes were scored.** End notes were scored mechanically, and this inflates `ignored` in several ways:
  - Declaring a new stage counts as ignored even when its name nearly matches X (209_T1 [122] → "Screen older unopened matters…"; 209_T2 [78]).
  - Keeping "Check or revise the response" for post-answer source re-reads that the classifier called in-depth reading counts as ignored (209_T2 [175]; many in 201).
  - Notes naming work that never recurs were scored none: 155_T0 [43] ('Calculate figures for the answer' on a re-filter of saved scan output) and 209_T0 [126] ('Search file contents for request keywords' on an in-matter status script).
- **Matter numbers in agent names.** Some agent-declared names contain matter numbers or client names (209_T1 "Resolve 1002-00001 closing status", 201_T0 "Check Dunmore 1016-00009 folder"). The notes elide them; `agent_new` keeps the literal name.
- **Split declared spans.** Declared new stages often mixed a store-wide script with reads or edits, and were split at call boundaries:
  - 209_T0 [140]-[153]
  - 209_T1 [65]-[77] and [135]-[153]
  - 209_T2 [79]-[126] and [140]-[149]
  - 014_T0 [87]-[98] and 014_T1 [87]-[99]
  - several spans in 063 and 091

  Both pieces of a split carry `agent_new`.
- **Critic edge cases.**
  - Review-endorsed:
    - 014_T0: the review said to keep all four facilities. Round 3 scored similar "keep the set" reviews not-flagged.
    - 155_T0: a review called one matter's executed-agreement hits employee non-solicits, and the answer then excluded that matter.
    - 155_T1: reviews asked to label unsigned exclusivity agreements, which led to a wrong "unsigned" label.
    - 063_T0 and 063_T1: reviews called the carry documents irrelevant or entity papers.
  - 201_T2: one review called two matters likely noise, and a later review named both. Scored flagged-ignored.
- **155_T1 search-miss.** The executed purchase agreements of two surfaced matters never appeared in any output; scans hit only their drafts. This follows convention 5 (never shown → search-miss), although the matters themselves were screened.
- **209_T2 later error.** The run opened the qualifying matter (one litigation outcome report) and did not weigh it. This is recorded as a later under-inclusion. Round 3's 209 runs never opened it.
- **126_T1 stage 5** was relabelled "Search file names for a document type" because 12 of its 18 path patterns are document or folder types. This is borderline under convention 4.
