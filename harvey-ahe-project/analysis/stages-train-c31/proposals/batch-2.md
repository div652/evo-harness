# Batch 2 proposals (round 4, campaign 31)

Tasks: 034 035 057 114 149 179 190 206 (24 runs: 8 pass, 16 fail, all 16 with first_error).

## NEW names

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|
| stage | NEW: Tally saved search output per matter | Post-processing a saved scratch file of scan or search hits (per-matter counts, rankings, compact tables, coverage checks, unions or filters of the hit list) without extracting document text again and without listing the store | 034_T1 [28]-[33], 035_T0 [22]-[27], 057_T1 [48]-[53], 149_T2 [40]-[47] | "Scan document text with an extraction script" says the script unzips and searches documents; these calls only read a scratch file. "Calculate figures for the answer" is for deliverable figures, not candidate selection. "List files in candidate matters" lists the store. |

Occurrences (15 spans in 10 runs). Agent-declared ("new") spans:

| Run | Events | Agent's new_stage_name | Run outcome |
|---|---|---|---|
| 034_T1 | [28]-[33] | Strong-term per-matter tally from scan file | pass |
| 035_T0 | [22]-[27] | Aggregate scan report per matter | fail |
| 035_T1 | [26]-[31] | Persist scan pool and identify Capital Markets candidates | fail |
| 057_T1 | [48]-[53] | List files in remaining surfaced matters | fail |
| 057_T1 | [54]-[59] | List all key-person hit files | fail |
| 149_T2 | [40]-[47], [48]-[53] | Compact M&A candidate table | fail |
| 179_T0 | [36]-[41] | Capped per-matter Pinnacle scan (attempt 2) | fail |

Relabelled from existing declared stages (same function, no agent_new): 034_T2 [26]-[31] (pass), 057_T0 [48]-[51], 057_T1 [30]-[35], 057_T2 [38]-[43] and [44]-[49], 114_T0 [32]-[37] and [85]-[94], 206_T1 [57]-[62] (pass). The reviewer also suggested such a step by name ("Roll up key-person hits by matter", "Tally and list all surfaced matters", "Rank scan hits by term-specific counts").

No NEW tags, hindsight values or error kinds.

## Agent-declared stages mapped to existing stages

Most "new" declarations fit the taxonomy and are labelled with it (note starts `declared: new: <name>`):
- Scans: "Compact per-matter scan rerun", "Read full table and broaden scan", "Tighten per-matter lock-up scan", "Background chunked text scan", "Background full-text term count", "Rank scan hits by term-specific counts" (all reran extraction), "Store-wide search for confirmed plans", "Enumerate all later restructuring matters", "Enumerate complete M&A practice set", "Broad Pinnacle fund-family scan", "Rank scan hits per matter", "Verify remaining M&A matters' agreements".
- Listings: "Build per-matter index" and "Compact matter inventory" (List matter folders); "List later matters' folders…", "Full folder listing of later-numbered…", "List full folders of all surfaced matters" (List files in candidate matters; the last two also held reads and were split); "Batched full-store matter enumeration" (Search file names for a document type).
- Reads: "Read later matters' key documents", "Open plan-related files…", "Read unopened surfaced matters", "Verify unopened (and weakly-evidenced) candidate matters", "Enumerate and read all candidate matters" (Screen; one span was a snippet script, Search within…), "Date-compare confirmed-plan matters" (scan, screen and in-depth across three attempts), "Verify coverage and read confirmation orders" and "Verify 1014-00004 currency…" (Read in depth).
- Response checks: "Verify flagged facts against sources", "Source-grounded spot audit", "Final response consistency check", "Reconcile response counts", "Reconcile matter count" (Check or revise the response).

## Issues

- **End-of-stage label notes, fourth case.** Rule 2 defines followed (next stage for that work declared X) and ignored (old label kept). Often the agent declared a *new* stage name for the same work instead. These are counted `ignored` (034_T0 [46]-[62], [97]-[108], [109]-[120]; 035_T0 [38]-[67]; 057_T1 [30]-[35]; 149_T2 [8]-[13]; 190_T0 [8]-[13], [36]-[41]). A separate value may be wanted.
- **label_check counts (two fields, per the coordinator's convention).** Start notes: followed 2, ignored 29. Both followed cases are empty spans closed at once in favour of the suggested stage (035_T0 [8]-[11], 035_T1 [40]-[43]). End notes: followed 7 (034_T1 [8]-[13], 034_T2 [38]-[45], 035_T1 [83]-[92], 114_T0 [48]-[53], 114_T1 [8]-[13], 149_T1 [32]-[37], 179_T1 [57]-[64]), ignored 10. End notes that had no later work of that kind are `none` (most of them, e.g. the List matter folders note after the second store listing).
- **Full file dumps under a folder-listing label.** Second store listings that print every file path (206_T0, 114_T0, 114_T1, 149_T0, 149_T2, 179_T1, 190_T1; 0.5-0.8M chars) stay "List files in the document store" with `huge output`, even when declared "List matter folders" or when the end note said List matter folders.
- **Precedent conflict for the NEW stage.** Round 3 (011_T0 [72]-[77], batch 5) labelled a path filter over saved scan output "Scan document text with an extraction script". This batch uses the NEW name for the same kind of span. The name says "search output" because two spans process saved path-search hits or saved snippets rather than a text scan (114_T0 [32]-[37], [85]-[94]).
- **Kind boundary in 190.** In T0 and T2 a store-wide file-name pattern written after non-discriminating text scans missed a matter whose executed agreement has an unusual file name; coded `over-narrow-filter` (the scans had reached it). Round 3 coded the same task's misses `surfaced-not-opened`. 057_T0's `search-miss` rests on the result markers: the key-term scan printed per-matter hits for 140 matters, none of them two of the qualifying ones.
- **Reviews pushing the wrong way.** 057_T1 (a screening review called a qualifying matter's document an amendment of an existing vehicle), 114_T0 (a review called a retention memo no proof of engagement) and 149_T2 (a write review told the agent to demote drafts; the check edit then moved a qualifying draft-only matter out) are `review-endorsed`. 149_T1 kept the same draft-only matter in a draft tier and passed that criterion, so the 149_T2 error partly reflects judge variance.
- **Response-check loops.** Agent-declared check stages (179_T0: five spans; 190_T1: five; 114_T1: two) re-verified matters already in the answer and never changed the matter set; reviews kept asking for one more check.
