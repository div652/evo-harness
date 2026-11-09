# Why the agent ignores the reviewer: feedback uptake in the stage harness

**Question.** The stage harness's end-of-stage reviewer often catches the agent's mistake at the moment it happens, yet the run still fails. Is the problem what the advice says, where it appears, or how the agent treats it? The answer decides how to write and where to place advice.

**Data.** Training runs only: stage harness rounds r2 and r3 (campaigns 30 and 31), 80 tasks × 3 trials each. That is 478 runs, 333 failing, and 6,046 end-of-stage reviews. No validation or test run is used.

---

## 1. Summary

1. **The reviewer usually sees the mistake.** In 237 of 333 failing runs (71%), the human annotation says the reviewer flagged the run's first error. Re-judged here, the flag was fully right in 71% of those and partly right in the rest. But it named the exact needed matter or document in only 32%.
2. **The agent almost never does what the flag asks, and it rarely argues.** In the 237 cases it acted partly on the advice in 51% and not at all in 49%. It disputed the flag in only 4%. It simply carried on with its own plan: that is the most common reason, at 42%. Next come acting superficially (22%) and the advice being buried among other asks (20%).
3. **Advice dies when the agent moves on.** Across a random sample of 446 flags, the agent acted fully on 48% of flags when it reopened the flagged stage. When it moved straight on to another stage, the figure was 14%, and moving on is its most common choice.
4. **Shape matters.** Flags that imply one concrete action were acted on fully 34% of the time, against 7% for vague ones. The first flag in a review was acted on more than the fourth or later (35% vs 22%).
5. **Repetition works, but the reviewer has no memory.** When later reviews raised the same problem again, partial uptake rose from 32% (never repeated) to 88% (four or more repeats). But the reviewer sees only the current stage, so 24% of first-error flags were never raised again, and at least 10 later reviews contradicted an earlier one.
6. **Uptake is slow.** When a review names a matter the agent hasn't opened, the agent opens one of them in the next stage in only 19% of cases, and at any later point in 49%.
7. **Uptake is the same in passing and failing runs** (fully acted 28% vs 30%). Passing runs don't follow advice better; they make fewer of the mistakes that need it.
8. **Headroom.** In 38 runs (7.9% of all r2/r3 runs), the flag was right, following it would have fixed the first error, and the run would likely have passed. Training all-pass was 30.3%, so better uptake could add up to about 8 points. That's an upper bound from model judgements.

**What this suggests** (details in section 7). The problem is less *what* the advice says than *where it lives*. Advice sits only in the closing review of a stage the agent is leaving, it competes with several other asks, and it's forgotten by the next review. The most promising changes:
- make flags persist across stages until they're resolved;
- give one prioritised, concrete action that names the item;
- put that action where the agent's next decision is made.

All of these change the mechanism, so they are a separate experiment against r3, not a new round.

---

## 2. Method

**Three layers of evidence:**

| Layer | What | How |
|---|---|---|
| Script measures | All 6,046 reviews | Parsed from the traces: the reviewer's verdict, flags, concerns and recommendation, the list of unopened matters, review length, what the agent did next, and whether matters the reviewer named were opened afterwards (`build_reviews.py`) |
| First-error cases | The 237 failing runs whose first error was flagged (179 "flagged, moved on" plus 58 "flagged, partly fixed") | An annotator model (`claude-opus-5-5`, different from both the agent and the reviewer) read each case: the task, rubric verdicts, the human annotation, the agent's stages and tool calls, and every review with what followed. It recorded which review flagged the error, whether the flag was right, its shape and timing, what the agent did, and why the advice wasn't followed (`annotate_cases.py`) |
| Flag-level sample | A random sample of 150 reviews with verdict "partly" or "no", half from passing and half from failing runs: 446 flags | The same annotator labelled each flag: specific or not, one concrete action or not, whether the agent acted on it in the next two stages, and whether it had already planned to anyway (`annotate_flags.py`) |

**Definitions:**
- "Opened" uses the harness's own definition: a matter number appears in the arguments of `read`, `glob` or `bash`, meaning its files were read or listed.
- The first error and the reviewer outcome ("flagged, moved on" and so on) come from the human training annotations (`analysis/stages-train-c30`, `-c31`).

**Checks:**
- Two pilot cases agreed with my own reading of those runs.
- A spot-check of 8 further cases, across every reason category plus headroom cases, agreed with the human annotations.
- An earlier flag sample that over-represented agent-defined stages was discarded and redrawn.

---

## 3. How good was the feedback? (237 first-error cases)

| | Cases |
|---|---|
| Flag fully right, given the rubric verdicts | 168 (71%) |
| Flag partly right | 69 (29%) |
| Named the exact needed matter or document (or the exact wrongly included one) | 76 (32%) |
| One concrete action for this problem | 16 (7%) |
| One action among several | 210 (89%) |
| Vague | 11 (5%) |
| Arrived **before** the agent's deciding step | 149 (63%) |
| Arrived **after** it (e.g. only at the writing or checking stage) | 88 (37%) |
| Following it would fully fix the first error | 88 (37%) |
| Following it would partly fix it | 148 (62%) |

By the annotation's flag type:

| Flag type | Cases | Flag right | Named the needed item | Agent never acted | Run would likely pass if followed |
|---|---|---|---|---|---|
| Specific | 139 | 80% | 49% | 57% | 33% |
| Generic | 98 | 58% | 8% | 38% | 18% |

Generic flags were right less often and almost never named the needed item. Often they named *other* matters as examples, for instance "about 60 unopened matters, e.g. …" without the one that mattered. That's partly mechanical:
- the unopened-matters list in the review is cut to 40 entries in 87% of the reviews that show it;
- the list is ordered by matter number, not by relevance.

---

## 4. What the agent did with it

| (237 cases) | |
|---|---|
| Ever acted on the advice: partly | 51% |
| Ever acted on the advice: not at all | 49% |
| Ever acted on the advice: fully | 0% (by construction: the error persisted) |
| The agent's next goal addressed the flag: yes / partly / no | 5% / 60% / 35% |
| The agent explicitly argued the flag didn't apply | 4% |
| The agent's stage summary claimed completeness the flag contradicted | 96% (a near-universal label; treat as indicative) |

**Why the advice wasn't followed:**

| Reason | Cases | Typical pattern |
|---|---|---|
| The agent's own plan continued | 99 (42%) | The next stage pursues the agent's existing shortlist or plan. *063 T2:* the review names 1001-00002 as "dismissed as restructuring without opening its documents"; the next stage reads only the agent's own three picks. |
| Acted superficially | 51 (22%) | It reacts in form but not in substance: relabels headings, reruns a scan with the same narrow filter, re-reads instead of opening the named item. *091 T1:* drafts are relabelled "not counted", but the text still says they qualify. |
| Buried among other asks | 47 (20%) | The relevant point is one of several. The agent acts on a different one. *243 T1:* the Word-files-only limit is flagged, but the recommendation centres on something else, and the next scan is still Word-only. |
| Advice too vague | 22 (9%) | "Many surfaced matters remain unopened" without naming the needed one. The agent opens others. |
| Reviewer wrong or misleading | 11 (5%) | A later review told the agent to keep the wrong matter, or pointed it to a different one. *028 T0, 209 T1, 104 T1.* |
| The agent judged the flag wrong | 5 (2%) | It re-read and declared the item verified under a broader standard (*072 T2, 199 T0*). |
| The advice arrived after the decision | 2 (1%) | E.g. the context had already filled up. |

The agent rarely disagrees with the reviewer. It treats the review as information and continues as planned.

---

## 5. What makes a flag get acted on (446 flags, random sample)

Overall, the agent acted on the flag fully for 29%, partly for 35%, and not at all for 35%. In 13% of flags it was going to do that thing anyway.

| Factor | Acted fully | Not acted |
|---|---|---|
| **Next move: reopened the flagged stage** | **48%** | 20% |
| Next move: started a new (agent-defined) stage | 39% | 16% |
| **Next move: went to another declared stage** (the most common: 229 flags) | **14%** | **51%** |
| Implies one concrete action | 34% | 33% |
| Vague or concern-only | 7% | 48% |
| Specific | 31% | 34% |
| Generic | 15% | 45% |
| First flag in the review | 35% | 39% |
| Fourth or later | 22% | 40% |
| Review had only 1 flag (n = 13) | 46% | 23% |
| Reviewer verdict "no" vs "partly" | 32% vs 29% | 34% vs 36% |
| Run passed vs failed | 28% vs 30% | 35% vs 36% |

**By the stage the review was for:**

| Stage | Acted fully | Not acted |
|---|---|---|
| Search file names for request keywords | 52% | 15% |
| Read documents picked from the file listing | 42% | 50% |
| Write the response | 39% | 9% |
| Scan document text with an extraction script | 27% | 31% |
| Screen candidate matters by reading documents | 23% | **49%** |
| List files in candidate matters | 19% | **50%** |
| Read a chosen matter's documents in depth | 10% | **76%** |

The flags at the screening, listing and reading stages are the most often ignored. Those are exactly the stages where the top first error, a matter found but never opened, happens.

**How acted-on flags were acted on:** in the next stage (174), in the second stage after (64), or by reopening the stage (50). So following advice is less a matter of reopening than of carrying the point into whatever comes next.

---

## 6. Persistence and timing (script measures over all reviews)

- **Prompt uptake is low.** When a review names matters the agent hasn't opened (2,783 reviews), one of them is opened in the next stage in 19% of cases, and at any later point in 49%.
- **Repetition drives uptake.** Partial uptake in the 237 cases, by how many later reviews raised the same problem: 0 → 32%, 1 → 45%, 2 → 57%, 3 → 70%, 4 or more → 88%. Among needed matters named while unopened (642): 203 were opened right after the first naming, 84 after the second, 31 after the third and 19 after more; 250 were opened later but never right after a naming; 55 were never opened.
- **But nothing makes repetition happen.** The reviewer sees only the current stage's calls, not its own earlier flags, so a problem from an earlier stage disappears once the agent moves on. 57 of 237 first-error flags (24%) were never raised again, and in at least 10 cases a later review contradicted an earlier one.
- **Timing.** 26% of all reviews are at the writing and checking stages, after the choices about what to open. 37% of first-error flags arrived after the deciding step.
- **Review size.** Median review is 2,400 characters (90th percentile 3,700). About 1,000 of that is the stage's common-failures block, which was already shown when the stage started. Matters named in reviews over 4,000 characters were followed up less (36% vs 51%).

---

## 7. Implications: how to write and place advice

All of these change the harness's mechanism, so they belong in a separate experiment against r3 on the same training tasks, not in a round. They are listed by strength of evidence.

1. **Make flags persist until they're resolved.** Keep a run-level list of open flags. Pass it to every later review, so the reviewer re-checks them and doesn't contradict itself, and show the open items at every `stage_start`. *Evidence:* repetition raises uptake from 32% to 88%; 24% of first-error flags were never raised again; at least 10 reviews contradicted an earlier one.
2. **Put the advice where the next decision is made.** The agent drops advice when it moves to another stage (14% acted on, against 48% when it reopens), and moving on is its usual choice. So the top unresolved action should appear in the result of whatever `stage_start` comes next, not only in the closing review of the stage being left.
3. **One prioritised, concrete action that names the item.**
   - Concrete flags are acted on about five times as often as vague ones (34% vs 7%).
   - The first flag beats the fourth (35% vs 22%).
   - Only 7% of first-error flags were a single concrete ask.
   - The reviewer would output one `top_action` (open X, rerun Y without filter Z), with the rest as secondary.
4. **Name the needed item, not examples.**
   - Rank the unopened-matters list by how strongly each matter matched the agent's own searches, not by matter number.
   - Don't let a 40-entry cut-off hide the relevant matter.
   - Generic flags named the needed item in only 8% of cases.
5. **Review the choice before writing.** 37% of first-error flags came after the deciding step. A check of the open flags before the agent writes ("before writing: these items are unresolved") would move the feedback earlier.
6. **Shorter reviews.** Drop the common-failures block from end-of-stage reviews (it's already shown at the start). The evidence here is weaker: one length comparison.

**About enforcement.** r4's steering gate already *forced* a reason for every flag at stage transitions, and didn't improve the score: the agent overrode 304 times. So making the agent acknowledge a flag isn't enough on its own. Before designing item 2, it's worth reading what those r4 override reasons said, to see whether the agent dismissed real flags or the flags were weak.

---

## 8. Caveats

- **Model-labelled judgements.** "Flag right", "why not followed" and "would pass" come from one annotator model. They agree with the human annotations in the spot-checks, but the headroom figure is an upper bound. Two labels are nearly saturated (summary overclaimed 96%, several asks 89%) and say little.
- **Correlation, not cause.** Reopening goes with acting on advice, but an agent that already intends to fix something is also more likely to reopen. Only an experiment can show that placing advice differently changes behaviour.
- **"Opened" includes listed.** A matter counts as opened if its folder was listed, even if no document was read. So the script measures overstate real uptake.
- **The data come from r2 and r3 only.** The mechanism differs in small ways between them (r3 adds the effective-stage review and the stuck clause).
- **No reasoning.** These campaigns ran before the reasoning-summary fix, so we can't see *why* the agent chose its plan over the advice. A rerun with summaries would show whether it read and dismissed the advice, or never weighed it.

---

## 9. Files

| Path (under `harvey-ahe-project/analysis/`) | What |
|---|---|
| `feedback-uptake/build_reviews.py` | Parses every review and what followed → `data/reviews.jsonl` (17 MB, not committed: rerun the script, about 1 minute), `data/runs.jsonl` |
| `feedback-uptake/annotate_cases.py` | Model labels for the 237 first-error cases → `data/case_labels.jsonl` |
| `feedback-uptake/annotate_flags.py` | Model labels for the 150-review flag sample → `data/flag_labels.jsonl`, `data/flag_sample.json` |
| `feedback-uptake/analyze.py` | All tables → `data/tables.md` |
| `reviewer-feedback-examples/` | Five full trajectories: a specific flag ignored, a generic warning ignored, partly fixed, followed and passed, and the same task ignored and failed |

Further cases cited above, all on training tasks (round, task, trial): r2 063 T2, r2 129 T2, r2 091 T1, r2 243 T1, r2 155 T0, r2 028 T0, r3 209 T1, r2 104 T1, r2 072 T2, r3 199 T0, r3 194 T0, r3 247 T2, r3 140 T2.
