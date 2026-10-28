# Task 056 under the stage harness (campaign 29, training task): one pass, one fail

**Request:** "We're pitching a prospective client on our energy regulatory experience and I want to lead with our freshest work. What's the matter with our most recent FERC work?" The answer goes in `response.md`.

**Rubric:**
- C-001 requires matter **1016-00005**, a FERC gas-tariff/rate proceeding whose latest filing was a status report on 13 Dec 2024.
- C-002 (precision) accepts only 1016-00005 or 1016-00004.

**Runs and traces:**
- `campaign-artifacts/harvey-lab-campaign-29-cao-stage-train80/evaluations/C0-train/units/a2fa0d24d0d150b4b11ec988db572cfb/attempt-1/trace.jsonl` (trial 0)
- `…/units/bec846d9ff945537b14f36ad15464951/attempt-1/trace.jsonl` (trial 1)

Readable view: `scripts/stage/view_trace.py <trace.jsonl>`.

`[n]` is the event number. "Critic" means the independent reviewer at `stage_end`.

## Trial 0: PASS (2/2), 108 events, 15 stages

| # | Stage (events) | What happened |
|---|---|---|
| 1 | List files in the document store [2–7] | Goal: learn the store layout. Ran one whole-store `glob`, which was capped and showed only a few matters. The agent itself noted that the listing is capped and has no FERC file names. **Critic: partly.** It flagged the cap and the risk of treating the visible matters as the whole store. |
| 2 | List files in the document store, reopened [8–16] | Goal: list every matter folder and search file names. In parallel: listed all 266 folders, and ran globs for `*ferc*`, `*tariff*` and `*interconnection*`. These surfaced 1016-00005, 1016-00004 and 1023-00001. **Critic: partly.** Searching file names alone misses FERC documents not named "ferc", and no candidate had been opened. |
| 3 | Scan document text with an extraction script [17–26] | Goal: extract text from every document and find FERC references. The first script failed on a heredoc syntax error; the second ran. It found 920 hit lines, then counted per matter: 1016-00005 (73 documents), 1023-00001 (61), 1016-00004 (33). **Critic: partly.** It scanned only .docx, was truncated at 920 lines, and found no dates or dockets. |
| 4 | Scan, reopened [27–32] | Goal: rerun over every file type, with dates and dockets. **Timed out at 60 s.** The agent reported `goal_reached=false` and decided to establish recency by reading. **Critic: no.** |
| 5 | List files in candidate matters [33–41] | Listed every file of 1016-00005, 1023-00001, 1016-00004, 1015-00001 and 1022-00001, and characterised each: 1016-00005 is a dedicated FERC rate case, 1016-00004 an enforcement matter, and 1022-00001 is FCC, not FERC. **Critic: partly.** About 39 matters from the scan were never listed. |
| 6 | List files in candidate matters, reopened [42–47] | Listed 8 more candidates with few hits, and judged their FERC mentions incidental. **Critic: partly.** It still left matters unlisted and judged from listings, not documents. |
| 7 | Read a chosen matter's documents in depth [48–64] | Read 10 dated documents across the 3 leading matters, then read more of 1016-00005's third quarterly status report. Findings: **1016-00005, status report filed 13 Dec 2024**; 1023-00001, status letter of 15 Nov 2024 about a FERC approval that had lapsed; 1016-00004, closed Feb 2024. **Critic: partly.** It still flagged unopened matters. |
| 8 | Search within a candidate matter's files [65–74] | Spot-checked about 20 unopened matters for FERC text. Both scripts printed nothing. **Critic: no.** Empty output may mean a silent failure. |
| 9 | Search within…, reopened [75–80] | Reran with a sanity check on a known FERC document. The extractor works: 1016-00005 has 73 FERC hits, and the matters flagged earlier have 0 (their hits came from an unrelated "Section 203"). It confirmed no 1016-00005 filing is later than 13 Dec 2024. **Critic: partly.** |
| 10 | Write the response [81–86] | Wrote `response.md`: 1016-00005 is the most recent substantive FERC work, with the reasoning and why 1023-00001 and 1016-00004 were excluded. |
| 11–13 | Check or revise the response, 3 attempts [87–106] | Attempt 1: a `grep` used the wrong path, so the critic said the verification proved nothing. Attempt 2: confirmed every cited file exists. Attempt 3: printed the bottom line and pulled the key dates from the sources. Each time the critic said "partly", and the agent reopened the stage. |
| 14 | Call finish [107] | |

**Why it passed:**
- Its reading stage compared the three dedicated FERC matters by the date of their *FERC filings*.
- Its spot-check confirmed that no later matter had real FERC work.
- The answer named 1016-00005 and only it.

## Trial 1: FAIL (0/2), 74 events, 12 stages

| # | Stage (events) | What happened |
|---|---|---|
| 1 | List files in the document store [2–7] | The same capped `glob`, and the same note from the agent. **Critic: partly.** |
| 2 | List matter folders [8–13] | `find` listed 266 folders. **Critic: yes.** It warned not to infer recency from folder numbers. |
| 3 | Scan document text with an extraction script [14–19] | Ran a store-wide scan with broad terms (FERC, tariff, interconnection, docket…) and **no output cap: about 460K characters**. From it, the agent named 1016-00005, 1016-00004 and 1023-00001. **Critic: partly.** Output too large, terms too broad. |
| 4 | Scan, reopened [20–25] | Ran a focused scan for exact FERC terms that **ranked matters by the latest year mentioned in any file that mentions FERC**. 2025 dates came up in incidental matters (an SEC letter, an engagement letter). **Critic: partly.** It explicitly flagged ranking by "latest year mentioned" rather than by the date of the FERC work itself. |
| 5 | Read a chosen matter's documents in depth [26–38] | Read 7 documents from the 3 leading matters. Correct finding: 1016-00005's filing of 13 Dec 2024 is the freshest dedicated FERC work, ahead of 1023-00001 (15 Nov 2024) and 1016-00004 (Feb 2024). **Here it had the right answer.** **Critic: partly.** It had not checked whether other matters had later FERC work. |
| 6 | Search within a candidate matter's files [39–54] | Following the critic, it looked further. Globs for `*FERC*` file names returned nothing, so it read documents of 1016-00003 (a **bond offering**) and 1015-00002. It found a diligence memo of **27 Apr 2025** in 1016-00003 that *discusses* FERC licensing. It concluded: "this changed the conclusion; the freshest FERC-related work overall is 1016-00003." **Critic: partly.** It warned: "Treated a diligence memo mentioning FERC as FERC work." |
| 7 | Scan, reopened again [55–60] | Ran a whole-store scan with document dates. It confirmed the dates, and **kept 1016-00003 as the lead**, with 1016-00005 as "the newest dedicated FERC proceeding". **Critic: partly.** |
| 8 | Write the response [61–66] | Wrote `response.md` leading with **1016-00003**, with 1016-00005 as a comparison. **Critic: partly.** It said picking a financing diligence matter over a dedicated FERC proceeding "may not match what the user asked for." |
| 9 | Check or revise the response [67–72] | Re-read the response and accepted it unchanged. **Critic: partly.** It again flagged the choice of headline. |
| 10 | Call finish [73] | |

**The judge:**
- C-001 fails because the answer leads with 1016-00003.
- C-002 fails because 1016-00003 is not an accepted answer.

**Why it failed:**
- The run had the right answer at stage 5.
- At stage 6, it **broadened "FERC work" to "a document that mentions FERC"**, the over-inclusion pattern of reading a request too broadly, and switched to a newer non-FERC matter.
- The critic flagged exactly this three times, at stages 6, 8 and 9. The agent acknowledged it only by adding a caveat, and kept the wrong headline.

## Comparison

| | Trial 0 (pass) | Trial 1 (fail) |
|---|---|---|
| Path to candidates | File-name globs + docx scan (capped by a line limit) | Uncapped broad scan (460K characters), then a scan ranked by year mentioned |
| Read stage | Correct: 1016-00005 freshest | Correct: 1016-00005 freshest |
| After reading | Spot-check confirmed other hits were incidental ("Section 203" in unrelated law) | Spot-check found a 2025 memo that **mentions** FERC, and switched to it |
| Critic's warning about the decisive error | — | Given 3 times; not acted on |
| Reopens | 7 | 3 |

**What this shows about the harness:**
- The reviews pushed both runs to look wider, which is what trial 0 needed.
- In trial 1 the same push exposed a misleading candidate. The critic caught the misjudgement, but **its warnings are advisory**, and the agent kept its answer.
- A possible improvement: when the critic says the answer may not match the request, require an explicit yes/no decision against the request's wording before `finish`.
