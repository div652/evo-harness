# Failure patterns by stage group: base harness (C0), 80 training tasks

Source: `annotations/*.json` after the merge (240 runs: 27 pass, 213 fail;
213 first errors, 121 later errors). Groups and stages as in `taxonomy.md`
("Stage groups"). Error kinds are hindsight labels (see taxonomy.md, Error
kinds); where an error sits follows merge convention 1 (judgement errors on
the writing stage, choice errors where the agent chose what to open, search
errors on the search). "FE" = count as first error, "LE" = count as a later
error (other_errors). Examples are `<task>_T<k> [a]-[b]` (the error's
narrower events where given). "Passing runs" draws only on the `divergence`
fields of the 16 tasks with at least one passing run (003 028 032 034 056 061
066 072 082 104 111 167 176 201 206 221).

## First errors: kind × stage

| Stage (group) | search-miss | partial-listing-as-corpus | surfaced-not-opened | over-inclusion | context-overflow | under-inclusion | misstated-facts | other | total |
|---|---|---|---|---|---|---|---|---|---|
| Scan document text with an extraction script (Search) | 34 | | 1 | | 15 | | | over-narrow-filter 1 | 51 |
| Read documents picked from the file listing (Start) | | 39 | | | | | | | 39 |
| Search file contents for request keywords (Search) | 37 | | | | | | | | 37 |
| Screen candidate matters by reading documents (Choose) | | | 29 | | | | | listed-document-not-opened 2, mistyped-path 1, miscount 1 | 33 |
| Write the response (Compose) | | | 1 | 18 | | 5 | 3 | hedged-answer 1, missing-identifier 1 | 29 |
| Search file names for request keywords (Search) | 13 | | | | | | | | 13 |
| List files in candidate matters (Choose) | | | 6 | | | | | | 6 |
| Search within a candidate matter's files (Verify) | 1 | | 2 | | | | | incomplete-population 1 | 4 |
| Search file names for a document type (Search) | | | | | | | | miscount 1 | 1 |
| **total** | **85** | **39** | **39** | **18** | **15** | **5** | **3** | **9** | **213** |

By group, first errors: Search the whole store 102, Start from the store
listing 39, Choose and screen candidates 39, Compose and deliver the answer
29, Verify the chosen matters 4. Later errors: Compose 100, Choose 17,
Verify 3, Search 1.

Top first-error patterns (stage, kind): listing reads taken as the whole
store 39; content-grep search-miss 37; extraction-scan search-miss 34;
surfaced-not-opened at screening 29; over-inclusion at write 18;
context-overflow from a scan 15; file-name search-miss 13;
surfaced-not-opened at candidate listing 6; under-inclusion at write 5.

Group-level transitions (consecutive stages with different names; row = from):

| from \ to | Start | Search | Choose | Verify | Compose |
|---|---|---|---|---|---|
| Start from the store listing | 103 | 162 | 2 | 26 | 26 |
| Search the whole store | 17 | 119 | 238 | 26 | 16 |
| Choose and screen candidates | 0 | 84 | 117 | 127 | 71 |
| Verify the chosen matters | 1 | 21 | 42 | 33 | 114 |
| Compose and deliver the answer | 1 | 1 | 0 | 1 | 259 |

Run-level contrasts: every passing run (27/27) has at least one store-wide
search stage; 38 failing runs have none. 14 of 27 passing runs (52%) used two
or more different store-wide search stages, against 73 of 213 failing runs
(34%). All 8 passing runs that read documents from the store listing searched
the store afterwards; 38 of the 110 failing runs with listing reads never
searched at all.

---

## 1. Start from the store listing

Passing 20/27 runs, failing 180/213. First errors 39, later 0.

### List files in the document store (pass 19, fail 178)
No errors are placed here. It is the first stage of 197 runs and is followed
directly by "Read documents picked from the file listing" in 103 of them. The
whole-store glob is silently capped (tag `listing covers few matters` in 193
runs), so the agent sees only a few matters; what it does next decides
whether the cap matters.

### Read documents picked from the file listing (pass 8, fail 110)

| Pattern | FE | LE | Examples |
|---|---|---|---|
| partial-listing-as-corpus | 39 | 0 | 047_T0 [5]-[16]: read the two listing-top matters, never searched, named one of them · 129_T1 [4]-[10]: read the one matter whose file names matched, concluded nothing else qualifies · 247_T2 [4]-[10]: took the one visible matter of the requested kind as the answer |

- Variants: the reads cover the 1-6 matters at the top of the capped listing
  and no store-wide search stage follows (38 runs; in 046_T0 the one script
  is confined to those matters), or the only later search looks for a figure
  taken from them (211_T1).
  Three tasks failed this way in all three runs (129, 211, 247).
- Passing runs: 8 passing runs also read from the listing first (056 all
  three, 082_T0, 167_T0, 176_T1/T2, 201_T1), and every one then searched the
  store; in 056 each run searched document text store-wide (extraction script
  or grep -Ril, narrowed after an error or timeout), which listed the
  candidate matters. 032_T2 searched and retried where 032_T0 judged the
  store from the listing.

## 2. Search the whole store

Passing 27/27, failing 175/213. First errors 102, later 1.

### Search file contents for request keywords (pass 15, fail 87)

| Pattern | FE | LE | Examples |
|---|---|---|---|
| search-miss | 37 | 0 | 200_T1 [2]-[4]: grep hits were email lines only; accepted those matters as complete · 104_T1 [5]-[7]: greps with single-extension globs returned nothing; fell back to listing-top matters · 162_T2 [13]-[14]: grep printed compressed document bytes; no usable lead |

- Variants (all 37 counted): hits come from email (.eml) text only, so
  matters whose evidence sits in .docx files never surface (16, e.g. 081_T1,
  194_T1, 243_T2); a glob that matches nothing (`*.docx`, `*`, brace or
  non-recursive globs) returns "No matches" and no other search follows (11,
  e.g. 003_T0, 192_T1, 230_T2); the hit list is broad or partial and is not
  followed by another search (7, e.g. 053_T1, 125_T1, 132_T0); `binary
  output` (3: 162_T0, 162_T2, 194_T2).
- Passing runs: followed an empty or misleading grep with file-name globs
  (003_T1/T2, 066_T0, 206_T0); used a content-mode grep and then listed the
  candidates' files (104_T2); ran an extraction script that unzips document
  text instead of the grep tool (176_T1/T2); used a recursive glob, a shell
  loop or grep -Ril on raw files (201, all runs).

### Scan document text with an extraction script (pass 16, fail 104)

| Pattern | FE | LE | Examples |
|---|---|---|---|
| search-miss | 34 | 1 | 126_T2 [11]-[12]: store-wide scan timed out with one needed matter in its output; worked from the partial list · 114_T2 [15]-[16]: retry restricted to folders with matching names, missing matters filed elsewhere · 184_T1 [5]-[6]: scan restricted to email files |
| context-overflow | 15 | 0 | 034_T2 [4]-[5]: broad terms, no output cap, ~4.5M chars, run ended · 131_T0 [13]-[14]: printed every matching file, ~63M chars · 059_T1 [6]-[7]: ~4M-char scan, then another uncapped script filled the context |
| surfaced-not-opened | 1 | 0 | 016_T0 [17]-[20]: follow-up scripts kept only files named as executed agreements, so one listed matter was never examined |
| over-narrow-filter | 1 | 0 | 192_T0 [17]-[18]: second script kept one exact folder name and dropped a matter the first scan had shown |

- search-miss variants (35): timed out (60 s) and was not narrowed, paged or
  rerun (27, e.g. 032_T1, 130_T1, 240_T2); restricted by folder, file name,
  file type or exact phrase so a needed matter fell outside (7, e.g. 011_T2,
  149_T1, 155_T2); cut by the agent's own line cap (209_T1).
- context-overflow: all 15 are store-wide scans that print every match of
  broad terms with no cap (1.1M-63M chars); two runs survived one large
  output and overflowed on the next (059_T1, 068_T0).
- Passing runs: kept retrying the scan until its partial output reached the
  matter (032_T2); narrowed a timed-out scan to agreement-type file names
  (111_T0) or to transaction-document folders (167_T0, whose scan listed all
  four needed agreements); narrowed after a syntax error or timeout (056
  T1/T2). Where a sibling run overflowed, the passing runs searched file and
  folder names instead (034_T0/T1, 111_T2).

### Search file names for request keywords (pass 11, fail 68)

| Pattern | FE | LE | Examples |
|---|---|---|---|
| search-miss | 13 | 0 | 195_T0 [5]-[6]: find \| grep cut at 240 lines, about 31 matters reached · 198_T0 [6]-[9]: glob stopped at 100 files · 169_T1 [4]-[7]: path pattern anchored on a leading word missed prefixed file names |

- Variants (13): output capped by the tool's 100-file limit or the agent's
  own `head`/`sed -n` (9, e.g. 053_T2, 148_T0, 230_T1); patterns too narrow
  for how files are named (3: 016_T1, 169_T1, 170_T0); worked from name hits
  after content greps failed (047_T1).
- Passing runs: file-name searches are the step that found the matter in
  003_T1/T2, 034_T0/T1, 066_T0, 111_T2 and 206_T0.

### Search file names for a document type (pass 0, fail 7)

| Pattern | FE | LE | Examples |
|---|---|---|---|
| miscount | 1 | 0 | 210_T0 [19]-[20]: counted matters per client from a listing limited to folders holding one document type, one short |

- Used in 7 failing runs only (017_T1, 130_T0, 167_T2, 194_T2, 195_T1, 210_T0,
  210_T2); no passing run uses it, and no passing-run comparison exists.

### List matter folders (pass 6, fail 25)
No errors are placed here. Its hindsight is `target in folder list only`
when a needed matter's folder name is in the list (27 stages). 52 of its 64
transitions are to or from store-wide searches (26 with extraction scans).

## 3. Choose and screen candidates

Passing 25/27, failing 143/213. First errors 39, later 17.

### Screen candidate matters by reading documents (pass 23, fail 141)

| Pattern | FE | LE | Examples |
|---|---|---|---|
| surfaced-not-opened | 29 | 12 | 167_T2 [28]-[34]: scan listed all needed agreements; the six it opened left one out · 104_T0 [7]-[13]: opened only matters whose file names matched, skipping one shown by grep · 179_T0 [22]-[28]: scan listed about twenty related matters; opened two |
| listed-document-not-opened | 2 | 0 | 137_T0 [42]-[48], 137_T2 [20]-[26]: the needed memo was in the matter's own listing; read other memos instead |
| miscount | 1 | 1 | 210_T2 [19]-[32]: verified only some number series from a complete listing; ranking left four out |
| mistyped-path | 1 | 0 | 199_T2 [16]-[22]: requested a surfaced matter's files under a mistyped number, got file-not-found, dropped it |

- surfaced-not-opened variants: the agent opened a subset of a list that
  showed many needed matters (census tasks, e.g. 011_T0, 121_T1, 125_T2,
  140_T0); or the needed matter showed only through email lines, drafts,
  redlines or a loose name match while the reads went to matters whose file
  names fit (e.g. 014_T0, 140_T1, 151_T0, 154_T0, 206_T1).
- Passing runs: opened every candidate the scan listed (167_T0); listed the
  files of all candidates, including the needed one, before comparing their
  closing documents (104_T2, 206_T0); opened documents of each candidate
  before writing (028_T0/T1, 072_T1).

### List files in candidate matters (pass 14, fail 78)

| Pattern | FE | LE | Examples |
|---|---|---|---|
| surfaced-not-opened | 6 | 4 | 167_T1 [15]-[20]: scan listed all four needed agreements; the five matters it listed left one out · 080_T2 [27]-[30]: listed only matters already read, not the new one the scan had printed · 053_T0 [23]-[24]: full file-name list showed two more needed matters; listed five others |

- Passing runs: in 167 the passing run opened all four matters the same scan
  showed, while T1 (here) and T2 (at screening) each left a different one out.

## 4. Verify the chosen matters

Passing 12/27, failing 132/213. First errors 4, later 3.

### Search within a candidate matter's files (pass 2, fail 71)

| Pattern | FE | LE | Examples |
|---|---|---|---|
| surfaced-not-opened | 2 | 1 | 057_T0 [9]-[14]: file-path search showed a needed matter; the five matters it grepped left it out · 063_T2 [14]-[15]: follow-up script restricted to four named matters |
| search-miss | 1 | 0 | 080_T1 [26]-[27]: in-matter grep did not read document text; never listed the matter's files, so the needed memo was not found |
| incomplete-population | 1 | 0 | 017_T0 [20]-[27]: fixed the deal set early from a timed-out scan; the rate's denominator lacks deals |

- In-matter greps hit email text only in several runs (Issues, batches 3-13);
  the judgement drawn from them is recorded at the write stage (243_T2).
- Passing runs: no divergence field names this stage; only 2 passing runs use it.

### Read a chosen matter's documents in depth (pass 11, fail 93)

| Pattern | FE | LE | Examples |
|---|---|---|---|
| listed-document-not-opened | 0 | 1 | 199_T1 [42]-[48]: read four of five listed files of the matter; the fifth was needed |
| answer-not-written | 0 | 1 | 141_T1 [14]-[18]: ended with the answer as chat text, no response file |

- Passing runs: read the picked matter's status reports and filings to date
  its latest work (056, all runs); confirmed candidates from emails and
  agreements (201, all runs); compared dates of executed agreements (066_T0).

## 5. Compose and deliver the answer

Passing 27/27, failing 197/213 (16 failing runs never wrote: 15 context
overflows and 141_T1). First errors 29, later 100.

### Write the response (pass 27, fail 197)

| Pattern | FE | LE | Examples |
|---|---|---|---|
| over-inclusion | 18 | 63 | 091_T0 [27]-[28]: asserted matters whose term was only a draft or negotiating position · 072_T2 [30]-[31]: counted every keyword-hit matter after 30-50-line skims · 223_T2 [46]-[47]: counted deals outside the request's scope (other deal types) |
| under-inclusion | 5 | 23 | 241_T2 [34]-[35]: read all needed matters, excluded two on a narrow reading of the request's qualifiers · 238_T0 [75]-[76]: read only a draft in the matter and excluded it · 016_T0 [35]-[36]: applied the request's exclusions to two qualifying items |
| misstated-facts | 3 | 11 | 035_T0 [44]-[45]: cited a read document under another matter's number from the same parallel batch · 058_T1 [32]-[33]: described a read matter's client and role wrongly · 190_T1 [37]-[38]: took a related filing date for the requested date |
| surfaced-not-opened | 1 | 1 | 185_T1 [13]-[14]: wrote from scan output without opening the matter it showed first |
| hedged-answer | 1 | 1 | 061_T0 [37]-[38]: scoped the conclusion to one client instead of the firm-wide statement asked for |
| missing-identifier | 1 | 0 | 221_T2 [12]-[13]: named the agreement but never the matter number |

- over-inclusion variants: drafts, unsigned or still-negotiated items counted
  as executed or closed (e.g. 058_T0, 102_T1, 170_T1, 195_T0); items outside
  the request's scope (other practice area, deal type or sibling matter of
  the same client, e.g. 016_T2, 126_T0, 209_T0, 241_T0); matters asserted
  from keyword hits, snippets or short skims without reading (e.g. 011_T2,
  028_T2, 184_T2); ranked-out comparators described as meeting the request
  (151_T2).
- under-inclusion variants: a qualifier or the request's exclusions read
  narrowly (016, 169_T1, 241); judged from part of the matter's documents
  (draft, pre-closing memo, first lines, email-only greps: 047_T1, 053_T1,
  238_T0, 243_T2); dropped without a stated reason (011_T0, 121_T2, 243_T0).
- misstated-facts variants: wrong matter number attached to documents read
  (printed engagement numbers or parallel results paired with the wrong path:
  014_T2, 035_T0, 125_T0, 125_T2, 149_T1); wrong category or bucket (017_T1,
  052_T0, 052_T2); wrong client or role (058, all runs); wrong detail
  (121_T1, 121_T2, 190_T1).
- Passing runs: opened each candidate and listed borderline matters as
  excluded rather than qualifying (028_T0/T1); checked and dropped keyword
  hits (072_T1); treated an unfiled motion as not meeting the request
  (082_T0/T2, where the runs split only at this judgement); stated the
  firm-wide conclusion flatly (061_T2); cited the matter number (221_T0/T1).

### Check or revise the response (pass 4, fail 32)

| Pattern | FE | LE | Examples |
|---|---|---|---|
| over-inclusion | 0 | 1 | 028_T2 [8]-[9]: a later edit added another non-qualifying matter |

### Calculate figures for the answer (pass 0, fail 5)
No errors are placed here (184_T0, 184_T1, 190_T0, 190_T1, 190_T2); no
passing run uses it.

### Finish the run (pass 27, fail 193)
No errors are placed here. 20 runs end without it: 16 with `run ended:
context overflow` (one, 014_T1, after its write) and 4 with `run ended: text
reply without finish` (058_T0, 080_T2, 158_T1 after writing; 141_T1 without
a response file).
