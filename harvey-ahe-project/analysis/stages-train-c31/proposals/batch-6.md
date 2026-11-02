# Batch 6 proposals (c31 round 4; tasks 016 066 082 093 129 158 211 223)

## NEW names

None. Every agent-defined stage, every tag, hindsight value and error kind fit an existing taxonomy name.

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|

## Agent-defined stages and their labels

Agents declared 66 distinct new stages (68 annotated spans counting splits) in 19 of the 24 runs; all map to existing stages. Most are reviewer-suggested ("Reviewer suggests a new step") rescans, inventories or verification reads. The table lists agent names as written; the annotation notes mask task words.

| Agent's name | Labelled as | Runs (outcome) |
|---|---|---|
| Contextual verification of the qualifying term | Check or revise the response | 093_T0 [122]-[129] (pass) |
| Final direct verification of DPA execution | Check or revise the response | 158_T0 [138]-[153] (fail) |
| Finalize recency proof | Check or revise the response | 066_T1 [157]-[165] (fail) |
| Verify execution status of unread DPA-like files | Check or revise the response | 158_T0 [129]-[137] (fail) |
| Verify execution via signature blocks | Check or revise the response | 158_T1 [101]-[106] (fail) |
| Verify recency ranking | Check or revise the response | 066_T1 [145]-[156] (fail) |
| List files in remaining surfaced matters | List files in candidate matters | 211_T2 [64]-[71] (fail) |
| List folders for all scanned matters | List files in candidate matters | 158_T0 [35]-[40] (fail) |
| List folders of all DPA-hit matters | List files in candidate matters | 158_T2 [20]-[25] (fail) |
| Read candidate matters | List files in candidate matters | 082_T1 [42]-[49] (pass) |
| Verify non-compete clauses per matter | List files in candidate matters | 093_T0 [26]-[29] (pass) |
| Widen candidate coverage and verify proof documents | List files in candidate matters | 211_T1 [91]-[99] (fail) |
| Compact per-matter inventory | List matter folders | 223_T2 [14]-[19] (fail) |
| Confirm signature evidence | Read a chosen matter's documents in depth | 158_T2 [67]-[75] (fail) |
| Direct evidence for recency conclusion | Read a chosen matter's documents in depth | 066_T1 [90]-[101] (fail) |
| Finalize shortest qualifying signed term | Read a chosen matter's documents in depth | 093_T0 [43]-[55] (pass) |
| Read candidate matters | Read a chosen matter's documents in depth | 082_T1 [76]-[84] (pass) |
| Single-matter DPA execution check | Read a chosen matter's documents in depth | 158_T2 [56]-[66] (fail) |
| Verify LPAC text in remaining candidates | Read a chosen matter's documents in depth | 066_T1 [72]-[83] (fail) |
| Verify execution on remaining borderline DPAs | Read a chosen matter's documents in depth | 158_T0 [79]-[87] (fail) |
| Verify shortest durations across all scan-hit matters | Read a chosen matter's documents in depth | 093_T1 [77]-[86] (fail) |
| Aggregate specific-term hits per matter | Scan document text with an extraction script | 066_T1 [32]-[37] (fail) |
| Background extraction scan with incremental output | Scan document text with an extraction script | 082_T2 [44]-[59] (pass) |
| Batched full-store rescan | Scan document text with an extraction script | 082_T1 [33]-[41] (pass) |
| Batched full-text scan for environmental indemnity (rerun) | Scan document text with an extraction script | 223_T1 [26]-[31] (fail) |
| Batched text scan of all matters | Scan document text with an extraction script | 211_T0 [36]-[41] (pass) |
| Broad duration rescan and per-matter confirmation | Scan document text with an extraction script | 093_T1 [87]-[92] (fail) |
| Broader rescan and candidate reconciliation | Scan document text with an extraction script | 223_T2 [32]-[39] (fail) |
| Build complete per-matter candidate table | Scan document text with an extraction script | 223_T0 [34]-[39] (fail) |
| Chunked per-range scan | Scan document text with an extraction script | 082_T0 [45]-[50] (pass) |
| Compact per-matter rescan | Scan document text with an extraction script | 093_T0 [20]-[25] (pass) |
| Complete LPAC candidate reconciliation | Scan document text with an extraction script | 066_T1 [38]-[41] (fail) |
| Complete prefix verification | Scan document text with an extraction script | 082_T0 [51]-[62] (pass) |
| Coverage reconciliation | Scan document text with an extraction script | 211_T1 [71]-[76] (fail) |
| Final store-wide financing cross-check | Scan document text with an extraction script | 211_T2 [145]-[154] (fail); 211_T2 [155]-[164] (fail) |
| Full-coverage covenant extraction | Scan document text with an extraction script | 016_T2 [110]-[115] (fail) |
| Full-store LPAC text scan | Scan document text with an extraction script | 066_T2 [60]-[65] (fail) |
| Full-text scan for environmental indemnity | Scan document text with an extraction script | 223_T1 [20]-[25] (fail) |
| Independent injunction cross-check | Scan document text with an extraction script | 082_T1 [85]-[91] (pass) |
| Per-matter document inventory | Scan document text with an extraction script | 016_T2 [52]-[57] (fail) |
| Restrict hits to Litigation (General) matters | Scan document text with an extraction script | 129_T0 [30]-[35] (fail) |
| Tightened store-wide co-occurrence rescan | Scan document text with an extraction script | 082_T1 [27]-[32] (pass) |
| Unfiltered batched extraction scan (attempt 2) | Scan document text with an extraction script | 211_T2 [46]-[57] (fail) |
| Variant-format financing check | Scan document text with an extraction script | 211_T2 [165]-[170] (fail) |
| Verify shortest durations across all scan-hit matters | Scan document text with an extraction script | 093_T1 [73]-[76] (fail) |
| Complete LPAC candidate reconciliation | Screen candidate matters by reading documents | 066_T1 [42]-[59] (fail) |
| Extract financing amounts from closing documents | Screen candidate matters by reading documents | 211_T2 [72]-[94] (fail) |
| Finish candidate reading and verify signatures | Screen candidate matters by reading documents | 158_T0 [59]-[78] (fail) |
| Identify Litigation (General) matters | Screen candidate matters by reading documents | 129_T2 [42]-[53] (fail) |
| Read candidate agreements for execution evidence | Screen candidate matters by reading documents | 158_T0 [41]-[58] (fail) |
| Read candidate matters | Screen candidate matters by reading documents | 082_T1 [50]-[75] (pass) |
| Resolve financing ranking gaps | Screen candidate matters by reading documents | 211_T2 [95]-[109] (fail) |
| Screen unopened candidate matters for executed DPAs | Screen candidate matters by reading documents | 158_T0 [119]-[128] (fail) |
| Verify LPAC text in remaining candidates | Screen candidate matters by reading documents | 066_T1 [60]-[71] (fail) |
| Verify non-compete clauses per matter | Screen candidate matters by reading documents | 093_T0 [30]-[42] (pass) |
| Verify practice group for all punitive-hit matters | Screen candidate matters by reading documents | 129_T0 [36]-[47] (fail); 129_T0 [48]-[77] (fail) |
| Widen candidate coverage and verify proof documents | Screen candidate matters by reading documents | 211_T1 [100]-[115] (fail) |
| Widen search for other semiconductor IP injunction matters | Screen candidate matters by reading documents | 082_T0 [85]-[99] (pass) |
| Enumerate real-estate matter population | Search file names for request keywords | 223_T0 [40]-[47] (fail) |
| Full per-matter file inventory | Search file names for request keywords | 016_T2 [86]-[93] (fail) |
| List remaining candidate matter folders | Search file names for request keywords | 016_T2 [80]-[85] (fail) |
| Rebuild complete candidate list from file | Search file names for request keywords | 223_T2 [20]-[25] (fail) |
| Search file names for request keywords (attempt 2) | Search file names for request keywords | 082_T2 [72]-[77] (pass) |
| Finalize shortest qualifying signed term | Search within a candidate matter's files | 093_T0 [56]-[69] (pass) |
| Read Ridgeline-Clarion LPA Article IX | Search within a candidate matter's files | 066_T2 [104]-[109] (fail) |
| Resolve formation date and recency | Search within a candidate matter's files | 066_T1 [84]-[89] (fail) |

## Issues

- **End-of-stage label notes: how they were scored.** Each stage has two fields, following the coordinator's update. `label_check` holds the start note and `label_check_end` holds the end note.
  - An end note is `followed` when the next stage doing that kind of work was declared X.
  - It is `ignored` when that stage kept the old label.
  - It is `none` when there was no later work of that kind, or when the next such work was declared under a third label (often a new stage).
  - Totals for the batch: start notes 0 followed, 23 ignored; end notes 7 followed, 6 ignored.
  - No run closed a stage to start the suggested one after a start note.
- **The end-note classifier often disagrees with the taxonomy.** Two cases recur:
  - Whole-store listings that print every file per matter (530-810K characters) were judged "List matter folders" or "List files in candidate matters". They are kept as "List files in the document store" (016_T1, 093_T1, 129_T1, 158_T0, 223_T1).
  - Post-write source re-reads were judged "Read a chosen matter's documents in depth" or "Read documents picked from the file listing". They are kept as "Check or revise the response".

  When the agent kept such a label for later work of the same kind, the note was still scored `ignored` (093_T0 [89]-[97], 066_T1 [121]-[130]).
- **Agent stage names that contain task words.** Examples: "Read Ridgeline-Clarion LPA Article IX" and "Verify LPAC text in remaining candidates" (066). The `declared: new: <name>` note prefix would break check.py's task-content rule. Those notes use placeholders (`<committee>`, `<vehicle> <agreement>`), and the raw name is kept only in `agent_new`. The merge should decide whether `agent_new` is exempt from the task-content rule.
- **A required proof document was read but not cited (066, all three runs).** Each run opened the chosen matter's key-terms memo (T0 [54], T1 [42], T2 [88]) and left it out of the cited documents, and no review mentioned it. It is coded `missing-detail` at the write stage with hindsight `answer misses document`. No kind names "opened a required document but did not cite it". listed-document-not-opened needs the document to be unopened, and under-inclusion is for matters. A kind such as `read-document-not-cited` may be worth adding if other batches see this.
- **Verification after writing under agent-defined stages.** Re-reads or signature extractions that check claims already in the answer are labelled "Check or revise the response" with `declared: new:` (066_T1 [145]-[165], 158_T0 [129]-[153], 158_T1 [101]-[106], 093_T0 [122]-[129]). Post-write store-wide scans and screening of new candidates keep their search or screening labels, following the batch-2 precedent (211_T2 [145]-[170], 158_T0 [119]-[128]).
- **Rubric inconsistency in 211.** The precision criterion allows two matters as "highest", but the main criterion requires one of them. T2 named the other, larger allowed facility and failed only the main criterion. Its over-narrow-filter first error is real (it never opened the expected matter), but the outcome partly reflects the rubric.
- **129: document number versus folder number.** The documents in one qualifying folder carry a different internal matter number. T2 named the matter by the document number and failed precision. T0 named it by its folder and passed. Coded `misstated-facts`, with hindsight `answer misdescribes matter`.
- **Critic values that cite the appended unopened-matters list.** In 093_T2 the matter was named only in the system-appended "Matters that appeared ... not opened" list (at [43], [58] and [70]), not in the review text. It is marked flagged-ignored "(specific flag)", as in c30 batch 6. In the raw traces this list is capped at about 40 matters, so it often cannot name a missed matter (129_T0, 211_T1/T2).
- **016: when a matter counts as surfaced-not-opened.** Missed matters appeared only in the agent's summary tables of saved scans or file-name searches, never read or grepped inside. These were coded surfaced-not-opened at the first screening stage. Matters the answer classified (for example as bridge or mezzanine) from scan snippets were coded under-inclusion at the write stage, because the agent had seen their evidence.
- **Mixed stages split at a call boundary.** Examples: listing then reading inside one agent-defined stage, and a scan then reading. The `label_check` went on the part that did the suggested work (129_T2 [58]-[67], 093_T1 [58]-[61], 093_T2 [65]-[70]) and `agent_new` on both parts.
