# Why the agent fails on Harvey LAB firm-knowledge tasks: the error catalog from the stage experiments

This report lists every kind of error we found when we annotated our agent's failing runs on Harvey LAB firm-knowledge tasks. They are ranked by how often each one was the cause of a failure.

It uses **training runs only**: no validation or test run was used for any count, description or example. It is written to be read top to bottom by someone who has not seen the project.

---

## 1. The setting, in brief

### 1.1 The tasks

**Harvey LAB** is a benchmark of legal work. We used its **firm-knowledge** tasks, which are questions about a law firm's own past work, for example:

> "How many of the merger reviews we've run in our antitrust practice have actually drawn a second request, and which were they?"

The agent answers by searching the firm's **document store** and writing its answer to a file, usually `response.md`.

### 1.2 Matters: the word used throughout this report

The firm's work is organised into **matters**. A matter is one engagement for one client, such as a merger review, a financing or a lawsuit. In the document store each matter is a folder, `documents/matters/<matter number>/`, holding that engagement's documents: engagement letters, memos, agreements, filings and emails. The store has **266 matters and 9,288 files**, mostly Word documents.

Almost every question asks *which matters* meet some condition, sometimes with details about them (a date, an amount, a key document). So the answer is mainly a list of matters, each identified by its matter number and justified from its documents.

### 1.3 How an answer is graded

Each task comes with a hidden **rubric**: a list of criteria an independent judge model checks against the answer file. Most criteria name a specific matter that must appear in the answer as qualifying, for example "Identifies matter 1003-00001 (Harrowgate PE) as a qualifying matter". Others require a particular document or detail to be stated, or a matter that does not qualify to be left out.

In this report:
- a **needed matter** is one the rubric requires the answer to name;
- a **needed document** or **needed detail** is a document or fact the rubric requires the answer to state.

A run **all-passes** only if every criterion passes. Missing one needed matter, or wrongly adding one, fails the whole task. That is why most of the errors below are about matters that were found but not opened, left out, or wrongly included.

### 1.4 How the agent works

The agent is a language model (`gpt-5.6-luna`) in a sandbox. It has the store mounted read-only and seven tools:
- `bash`: run shell commands;
- `read`: open a file as text, including Word, Excel, PowerPoint and PDF;
- `write` and `edit`: create or change files;
- `glob`: find files by name pattern (returns at most 100 paths, without saying so);
- `grep`: search file contents with a regular expression. It reads raw bytes, so it **cannot see text inside Word files**;
- `finish`: end the run.

Two tool limits matter for the errors below. `glob` silently stops at 100 files, and `grep` can't search Word documents. So to search document text across the store, the agent has to write its own extraction script.

---

## 2. Where the errors come from

### 2.1 The runs

We ran the agent on the **80 training tasks, 3 times each** (240 runs per round), in four rounds:

| Round | Harness | Failing runs (of 240) |
|---|---|---|
| C0 | the base harness, LAB's reference agent | 213 |
| r1 | stage harness, version 1 | 176 |
| r2 | stage harness, version 2 | 164 |
| r3 | stage harness, version 3 | 169 |
| **Total** | | **722** |

The **stage harness** makes the agent work in declared stages, such as "search the store", "screen candidates" or "write the response". Each stage gets feedback built from the errors in this catalog, and an independent reviewer model checks each stage when it ends. The method is in `docs/stage-protocol-harness.md`; this report covers only the errors.

### 2.2 The annotation

Every run was annotated by hand-instructed LLM annotators who had the run's full log and the judge's verdict on each criterion:

1. **Stages.** The run is split into stages, named after what the agent was doing. The names are generic, never specific to a task.
2. **The first error.** For a failing run, this is the **earliest point where the run went wrong**: the step after which the failure could no longer be avoided without going back. It gets a stage, an *error kind* and a one-sentence explanation.
3. **Other errors.** Later mistakes in the same run are recorded too.

The error kinds were grown from the runs, not fixed in advance. Annotators proposed new kinds when none fit, and similar proposals were merged.

### 2.3 How the errors are ranked

Kinds are ranked by **how many failing runs they were the first error in**, pooled over all four rounds. That's the closest measure of how many failures the error causes: fix the first error, and the run has a chance to pass. Total occurrences (first plus later errors) are shown too, because some kinds are often present but rarely the first cause.

---

## 3. Summary

| # | Error kind | In one line | First error in (of 722) | All occurrences | Usually at stage |
|---|---|---|---|---|---|
| 1 | surfaced-not-opened | A needed matter appeared in the agent's own search results, but it never opened it | **200** | 243 | Screen candidate matters |
| 2 | over-inclusion | The answer names matters that do not meet the request | **136** | **423** | Write the response |
| 3 | search-miss | No search the agent ran could reach a needed matter | **130** | 135 | Scan document text |
| 4 | context-overflow | One tool call returned so much text that the run ran out of context | 63 | 63 | Scan document text |
| 5 | under-inclusion | The agent saw a needed matter's evidence but left it out of the answer | 62 | 212 | Write the response |
| 6 | partial-listing-as-corpus | Treated a capped 100-file listing as the whole store | 39 | 39 | Read documents from the listing |
| 7 | over-narrow-filter | A broad search found everything, then the agent's own filter dropped a needed matter | 39 | 40 | Scan document text |
| 8 | listed-document-not-opened | A needed document appeared in a matter's file list, but was never opened | 30 | 49 | Screen candidate matters |
| 9 | misstated-facts | The right matter, but a wrong date, amount, role or category | 8 | 56 | Write the response |
| 10 | missing-detail | The right matter, but a requested detail is left out | 4 | 6 | Write the response |
| 11 | mistyped-path | A needed matter was dropped after a typo in its path | 3 | 4 | Screen candidate matters |
| 12 | incomplete-population | A count or rate built on a set that misses part of the population | 3 | 6 | varies |
| 13 | miscount | A count or ranking from the agent's own listing is wrong | 2 | 3 | Search file names |
| 14 | missing-identifier | The right matter, but the answer omits its matter number | 2 | 4 | Write the response |
| 15 | hedged-answer | Had the evidence, but did not answer the question as asked | 1 | 2 | Write the response |
| 16 | answer-not-written | Answer given only in chat, no answer file | 0 | 1 | Read in depth |

The first eight kinds cause **97% of failures** (699 of 722).

---

## 4. The errors in detail

Each entry gives what the error is, how it typically happens (paraphrased from the training annotations), where in the work it happens, and how often it was the first error in each round (C0 → r1 → r2 → r3).

### 1. surfaced-not-opened: found it, never looked at it

**What it is.** A needed matter appears in the agent's own search or scan output: its number shows up in a list of hits. But when the agent picks which candidates to open next, it leaves that matter out and never opens any of its documents. The matter never makes it into the answer, so its rubric criterion fails.

**How it happens.** Searches typically return dozens of candidate matters, and the agent can read only a few. It picks by surface cues, such as file names or which hits came first, and the needed matter is among the ones it skips. For example, a scan listed all four qualifying deals, but of the six agreements the agent chose to open, it left out one of them, so that deal never reached the answer. In another run, five needed matters appeared in file-name searches, but every later read went to other candidates.

**Where.** Mostly at *Screen candidate matters by reading documents* (144 of 200), the step where the agent reads the start of documents from several candidates to judge which fit.

**Trend.** 39 → 41 → 56 → 64. **The top cause of failure, and rising.** As the stage harness fixed the search errors (kind 3), more runs found the needed matter, so more failures moved to this next step: choosing what to open.

### 2. over-inclusion: names matters that do not qualify

**What it is.** The answer asserts that matters qualify when they do not meet the request. A criterion that says a non-qualifying matter must not be included fails, and the answer's count or list is wrong.

**How it happens.** The agent includes matters on keyword hits or a skim, or reads a condition in the request too loosely. For example:
- financing matters were counted as "completed real-estate deals" because they contained the right terms;
- a privately placed bridge financing was listed as a qualifying public offering;
- a matter used for comparison was presented as meeting the request.

**Where.** Almost always at *Write the response* (134 of 136). The decision is made when the answer is written; the annotation convention files every judgement error there.

**Trend.** 18 → 40 → 42 → 36. **The most frequent error overall** (423 occurrences), often several per run. It rose after the base round: with better searching the agent found more candidates and admitted too many of them.

### 3. search-miss: no search could reach it

**What it is.** None of the agent's searches could reach a needed matter, and the agent didn't widen the search or try another way. The matter never appears anywhere in the run.

**How it happens.** The usual causes:
- **File names only.** The agent searched only file names, which often don't contain the words in the question.
- **The grep tool on Word files.** It used `grep`, which can't read inside Word files.
- **A failed or partly read scan.** A text-extraction scan timed out after 60 seconds, or its huge output was viewed only in part, for example the first 200 of about 7,900 hits.

For example, the agent's only search was one file-name pattern for a deal type, so six qualifying matters whose file names didn't match never surfaced.

**Where.** Mostly at *Scan document text with an extraction script* (68 of 130). The rest are at the search stages.

**Trend.** **85** → 17 → 14 → 14. The main failure of the base agent (40% of its failures), and the one the stage feedback fixed best. Telling the agent at the search stages that `grep` can't read Word files, and that file names miss things, mostly removed it.

### 4. context-overflow: one tool call filled the context

**What it is.** A single tool call returned so much text that the model's context filled up, and the run ended before any answer file was written. With no answer file, every criterion fails.

**How it happens.** A store-wide extraction script with broad search terms printed every hit with no limit. For example, a scan printed about 4.5 million characters of snippets for common fee and cost terms.

**Where.** *Scan document text with an extraction script* (58 of 63).

**Trend.** 15 → 34 → 5 → 9. It jumped in r1, when the stage feedback pushed the agent toward store-wide text scans (the fix for kind 3) without warning about output size. It dropped once the scan stage's feedback warned to cap output. These runs end before any review, so this is the one error the end-of-stage reviewer can never catch. That's why the stage harness also shows each stage's common failures when the stage starts.

### 5. under-inclusion: saw it, then left it out

**What it is.** The agent opened a needed matter, or saw evidence that it qualifies, but the answer leaves it out or calls it not qualifying. It is the mirror image of over-inclusion.

**How it happens.** It reads a condition in the request too narrowly, or judges from part of a matter's documents: a draft, an early memo, the first lines, or only the emails. For example:
- two matters with the right provisions were kept out because no executed agreement was found;
- a matter was judged a "restructuring" from its file names alone and dropped without reading any document;
- the right matter was read in full but ranked below a weaker one.

**Where.** *Write the response* (61 of 62).

**Trend.** 5 → 18 → 24 → 15. Frequent overall (212 occurrences). Like over-inclusion, it is a judgement error at the end of the work, and it became more visible once searching improved.

### 6. partial-listing-as-corpus: mistook a partial listing for the whole store

**What it is.** The agent listed the store with `glob`, got back 100 files (the tool's silent limit) from a handful of matters, and chose what to read from that list without any keyword search, as if those matters were the whole store. The needed matters were never in view.

**How it happens.** For example, the agent picked the one investigation matter visible at the top of the capped listing and never searched further. Several runs concluded "no matter qualifies" from such a listing.

**Where.** *Read documents picked from the file listing* (all 39).

**Trend.** **39** → 0 → 0 → 0. A base-agent error that disappeared completely once the stage feedback said the listing is capped and the store must be searched.

### 7. over-narrow-filter: own filter dropped what the search had found

**What it is.** A broad search or scan reached every needed matter. Then a follow-up filter the agent wrote to narrow the hits, such as an exact phrase, a folder name or a file-name pattern, silently dropped one. The answer was built from the filtered list.

**How it happens.** For example, the scan hits listed every qualifying matter, but a filter for the exact phrase in the question kept only four of them, and twelve qualifying matters were lost. In another run, a matter was dropped because its documents described the practice group in other words.

**Where.** *Scan document text with an extraction script* (27 of 39). The rest are at searching and tabulating steps.

**Trend.** 1 → 14 → 13 → 11. It came with the scan-heavy way of working that the stage feedback encouraged: more scans, followed by more filtering.

### 8. listed-document-not-opened: the same as kind 1, for a document

**What it is.** The same pattern as kind 1, one level down. A document the rubric requires, such as a status memo or a key agreement, appeared in the agent's own listing of a matter it was working on. But when choosing what to read, the agent left it out and never opened or cited it.

**How it happens.** For example, a matter's file list included the status memo that recorded the other side's demand, but the agent read other memos and pleadings instead. In another run, the carry agreement was listed first but never opened, even after the reviewer warned that it might be missed.

**Where.** *Screen candidate matters by reading documents* (26 of 30).

**Trend.** 2 → 7 → 8 → 13. **Rising, like kind 1.** Together, kinds 1 and 8 ("it was in front of the agent and it didn't open it") caused 230 first errors, 32% of all failures.

### 9. misstated-facts: the right matter, a wrong fact

**What it is.** The answer includes a needed matter or document but states something its documents don't support. For example:
- a wrong date or amount;
- the wrong paying side;
- the wrong category;
- the wrong client or role;
- the wrong matter number for a document.

**How it happens.** For example, a settlement was reported at its initial-payment figure, taken from a scan snippet, instead of the larger amount in the executed agreement, which was never opened. In another run, a review done for an investor client was described as the sponsor's own engagement.

**Where.** *Write the response*.

**Trend.** 3 → 3 → 1 → 1 as a first error, but 56 occurrences overall. It usually comes on top of an earlier error.

### 10. missing-detail: the right matter, a detail left out

**What it is.** The answer names the right matter but leaves out a requested detail or qualifier that the documents it read state. It is an omission, not a misstatement. For example, a registration was described without saying it was the automatic shelf type, although the memo the agent read says so.

**Where.** *Write the response*. **Trend.** Defined from round 2 onwards; 4 first errors.

### 11. mistyped-path: dropped after a typo

**What it is.** The agent tried to open a needed matter that had surfaced in its own results, but typed the matter number or path wrong, or guessed a path from a sibling matter. It got "file not found" and never returned to the matter.

**Where.** *Screen candidate matters*. **Trend.** Rare: 3 first errors.

### 12. incomplete-population: the denominator is wrong

**What it is.** For a count or rate question ("what share of our deals…"), the agent fixed the set early and missed part of the population the question covers. The rate comes out wrong, even when every needed matter named in the rubric is present. For example, a rate was computed over three deals instead of four.

**Trend.** Rare: 3 first errors.

### 13. miscount: the tally is wrong

**What it is.** A count or ranking taken from the agent's own listing is wrong. Either the listing was filtered so it dropped items, or the tally skipped groups the listing showed. For example, matters were counted per client only from folders containing an engagement letter, so one client came out one short.

**Trend.** Rare: 2 first errors, both in the base round.

### 14. missing-identifier: the right matter, no matter number

**What it is.** The agent found and read the right matter, but the answer identifies it only by title, parties or date, without the matter number a criterion requires. (If a *wrong* number is given, it counts as misstated-facts.)

**Trend.** Rare: 2 first errors.

### 15. hedged-answer: did not answer the question asked

**What it is.** The agent had the evidence, but scoped or qualified its conclusion so that it doesn't answer the question as asked. For example, it framed the answer around one client and declined to make the firm-wide statement the question asked for.

**Trend.** 1 first error.

### 16. answer-not-written: no answer file

**What it is.** The run ended with the answer only as a chat message and no answer file, so the judge saw nothing. The context was not full. It was seen once, and never as a first error.

---

## 5. What the catalog says

**Three families account for almost all failures:**

1. **Not reaching the needed matter** (kinds 3, 4, 6, 7): 271 first errors.
   - **Base agent:** most of its failures (140 of 213).
   - **Stage harness:** the stage feedback largely fixed searching that never reached the matter (search-miss 85 → 14) and the partial listing (39 → 0).
   - **Still there:** its own scans brought two new problems, overflowing the context and over-filtering the hits (together 20 failures in r3).
2. **Reaching it but not opening it** (kinds 1, 8, 11): 233 first errors. **Rising, and now the top cause** (79 of 169 failures in r3). The agent sees the needed matter or document in its own results and moves on without opening it.
3. **Opening it but judging wrongly when writing** (kinds 2, 5, 9, 10, 12–16): 218 first errors. It is the most frequent kind of mistake overall: over- and under-inclusion together occur 635 times.

**The shift across rounds.** Each fix moved failures to the next step of the work, in this order:
1. **finding** matters;
2. **choosing what to open**;
3. **deciding what qualifies**.

The remaining errors are mostly about choosing and judging. In these, the agent typically had the information in front of it, and often a specific warning from the reviewer, and still moved on.

---

## 6. Caveats

- **Training runs only.** All counts, descriptions and examples come from the four training catalogs (`analysis/stages-train`, `-c29`, `-c30`, `-c31`). An earlier analysis of test runs was archived and is not used here.
- **The rounds are different agents.** C0 is the base harness; r1–r3 are versions of the stage harness. Pooled counts mix them, so read the per-round trend for each kind.
- **Annotation conventions shape some counts.** All judgement errors are filed at *Write the response*, and each failing run has exactly one first error. A run with several problems counts only its earliest.
- **Kinds were added over time.** missing-detail was defined in round 2, so earlier rounds could not use it.
- **"Relevance" here means frequency as a first error.** It is not the cost of fixing an error, or how many tasks it affects.

Sources: annotations in `harvey-ahe-project/analysis/stages-train*/annotations/`, definitions in `stages-train-c31/taxonomy.md`.
