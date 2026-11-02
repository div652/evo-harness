# Stage-protocol harness: bootstrapping stages from training runs and guiding the agent through them

This document describes, end to end, how we:

1. learned the stages an agent goes through on Harvey LAB firm-knowledge tasks, from its own training runs;
2. learned the common failures at each stage;
3. built a harness that makes the agent declare each stage, shows it those failures, and reviews every stage with an independent critic.

It is written so the whole process can be repeated on another model, harness or benchmark; the step-by-step version is `docs/stage-protocol-replication-guide.md`.

Status as of 2026-11-02: four rounds run on the training split (80 tasks × 3). The final mechanism is `harness_stage_r3/` (section 4), frozen from now on (#33). r4 added a steering gate, which did not help and was dropped (#34). r2 and r3 were checked on validation (section 7). How the system was built, step by step, is in the history (section 6) and Appendix A.

---

## 1. Idea

An agent solving a task moves through a small number of stages: list the store, search it, screen candidates, read the chosen ones, write, check. Failures cluster at particular stages: a search that cannot reach a document, a candidate that surfaced but was never opened, a condition read too loosely when writing.

The approach:

1. **Observe.** Run the unmodified agent on the training tasks.
2. **Name the stages.** Label each run's tool calls as a sequence of named stages, growing the stage vocabulary bottom-up.
3. **Find failures per stage.** For each failing run, mark the stage where it first went wrong, and the kind of error.
4. **Aggregate.** Per stage, collect the failure patterns, and what passing runs did there.
5. **Guide.** Change the harness so the agent:
   - declares each stage and its goal;
   - is told that stage's past failures when it starts the stage;
   - at the end of the stage, gets an independent critic's review plus the failure list;
   - then decides whether to reopen the stage or move on.

The long-term loop is: train runs → stages → stage-level critics and verifiers → guided model → new train runs → refine the stages.

**The mechanism is built once; the rounds learn stages.** The stage tools, guard, critic, label classifier and build script were built over our first rounds (section 6) and are now frozen. Each later round changes only the learned stage content: the stage list (agent-defined stages promoted, stages split or merged, from data) and the stage reference regenerated from all training catalogs.

### Ground rule: training data only

Every design input (stage names, failure patterns, examples, recommended tools) must come from **training** runs. Validation and test runs must never inform the harness.

An earlier version of this analysis was built on test-task runs. It was moved out of the project, to `/home/agarwaldi/archive/harvey-test-analysis-20261027/`, and must not be used. Claims that came only from test runs were withdrawn. For example, "searching after drafting is a behaviour to avoid" came only from test runs, and was dropped.

---

## 2. Setting

| Item | Value |
|---|---|
| Benchmark | Harvey LAB, firm-knowledge tasks |
| Document store | Shared store of 9,288 files (mostly .docx, plus .eml, .xlsx, .pptx) in 266 matter folders `documents/matters/<NNNN-NNNNN>/…` |
| Deliverable | Usually `response.md` |
| Grading | One judge (`gpt-5.6-sol`, high effort) grades rubric criteria. A trial *all-passes* only if every criterion passes. The metric is the mean all-pass rate. |
| Evaluated model | `gpt-5.6-luna` via the local CAO gateway (`http://127.0.0.1:4141/v1`, Responses API) |
| Base harness | `harness_lab/` (campaign 23's C0): tools `bash`, `read`, `write`, `edit`, `glob`, `grep`, `finish`, plus a long system prompt that is mostly Office-file skills. Its `glob` silently returns at most 100 paths. Its `grep` reads raw bytes, so it cannot see .docx text. `max_iterations` is 200. |
| Split | `splits-firm-knowledge-80-20-20.json` (campaign 12/23): 80 train, 20 validation, 20 test |
| Training data used | Campaign 23's C0 training evaluation: 80 tasks × 3 trials = 240 runs (27 all-pass, 213 fail; 11.3%) in `campaign-artifacts/harvey-lab-campaign-23-cao-luna-allpass-80-20-20/evaluations/C0-train/` |
| Runner | `ahe_runner` (repo `AHE_Harvey_cao`). Eval-only runs use `scripts/run_c0_train_only.py`. |

---

## 3. Phase A: bootstrap the stages from one training run

Everything lives in `analysis/stages-train/`.

### A1. Compact logs (`make_logs.py`)

For each run it takes the latest `attempt-*` per unit (retried units live in `attempt-2`) and writes `logs/<task>_T<k>.txt`. Each log contains:

- **Header:** the request (first 1,500 characters), the judge result, and every rubric criterion (title, verdict and reasoning, about 260 characters each).
- **Rubric matter numbers:** the `NNNN-NNNNN` numbers found in criterion titles. They act as "target matters" for hindsight only.
- **Body:** one line per tool call, `[n] CALL tool args`, and one per result, `[n] -> size: start of result`. A marker `<<target matter in result: …>>` (with `FIRST TIME`) shows where a rubric matter first appeared. `[n]` is the event index, and calls that share an index ran in parallel.

It also writes `runs_index.json`, with each run's task, trial, `all_pass` and `n_passed`/`n_criteria`. The logs are about 3.3 MB for 240 runs.

### A2. Annotation rules (`BRIEF.md`)

1. **Naming.** Stage names are descriptive verb phrases that are specific to the benchmark but not to any task, for example "Search file names for request keywords". Never codes, and never task content (matter numbers, parties, topics, request keywords).
2. **Coverage.** Every tool-call event belongs to exactly one stage. Stages are contiguous, in time order, and cover the whole run; a stage may recur. A stage is the longest run of consecutive calls with one intent. Mixed parallel calls are labelled by their dominant intent.
3. **Reuse before adding.** Reuse an existing stage when it fits; add a new one only when every existing stage would misdescribe the intent. Never rename or delete a stage; record doubts under "Issues".
4. **Agent's view only.** Stage names, notes and tags describe what the agent knew and intended at that moment. No hindsight words ("target", "decoy", "rubric", "correct/wrong") appear there. This was a user requirement: the agent could not know which matter was the answer.
5. **Hindsight fields.** Rubric knowledge goes only into separate fields:
   - the per-stage `hindsight` value;
   - `failure_point`;
   - `first_error` and `other_errors`;
   - `divergence`.

   Hindsight values and error kinds also grow as vocabularies.
6. **First error.** Each failing run gets the earliest stage whose action or decision led to a failed criterion: where the agent's behaviour first went off course, not where the damage became visible. Examples:
   - a needed matter never surfaced: the search that should have found it;
   - surfaced but never opened: the stage where the agent chose what to open;
   - opened but misjudged: the stage where the judgement became observable;
   - context overflow: the stage with the oversized output.

   Later independent errors go into `other_errors`.
7. **Output per task.** `annotations/<task>.json` holds the stages (stage, start, end, tags, hindsight, note), `sequence`, `failure_point`, `first_error`, `other_errors` and `divergence`. A matching `.md` has a table per run, with ⛔ on the first error and ⚠ on later errors, and a "Task context" section, the only place task content may appear.

`taxonomy.md` starts **empty**. It has sections Stages, Tags, Hindsight values, Error kinds and Issues.

### A3. Order of annotation

Annotation was done by LLM subagents (Claude). The order matters, because the vocabulary grows as runs are labelled.

| Step | Tasks | How |
|---|---|---|
| Batch 1 (sequential) | 7 mixed-outcome tasks (some runs pass, some fail) | Built the first vocabulary from nothing: 13 stages, 9 tags, 13 hindsight values, 5 error kinds. Edited `taxonomy.md` directly. |
| Batch 2 (sequential) | 7 more mixed tasks + 2 all-pass tasks | No new stages were needed; 2 error kinds were added. |
| Batches 3–13 (parallel, 11 agents) | The 64 tasks where all runs fail, about 6 per batch | `taxonomy.md`, `changelog.md` and `check.py` were frozen. New names were used with a `NEW:` prefix and listed in `proposals/batch-N.md` (`BRIEF_PARALLEL.md`). |
| Merge (one agent) | All 80 tasks | Folded synonyms together, accepted names used in ≥2 runs or marking a first error, stripped `NEW:` and harmonised conventions (below). |

Mixed tasks go first because comparing passing and failing runs of the same task shows the decisive stage most clearly.

Lessons from running the batches:

- Parallel agents shared one scratch folder and overwrote each other's generator scripts once. Give each agent its own scratch folder.
- The checker should accept the run-ended tags explicitly, so a run that ends without `finish` still validates.

### A4. Merge conventions (applied to all 80 tasks)

- **Judgement errors** (over-inclusion, under-inclusion, misstated-facts, hedged-answer, missing-identifier) sit on the writing stage whose text first shows them. The logs hold no agent reasoning before the answer, so the answer is where the judgement first becomes visible; the reading stage behind it is named in `why`. Choice errors sit where the agent chose what to open, and search errors on the search.
- **Hindsight on store-wide listings** follows the log markers.
- **A parallel event that mixes a store-wide search with reads** is labelled by the search.
- **Searches for a kind of document** (rather than for request words) use "Search file names for a document type".
- **Synonyms merged:**
  - one error kind, under-inclusion: over-exclusion, misjudged-exclusion, opened-but-excluded, opened-then-excluded and dismissed-after-shallow-read;
  - one error kind, misstated-facts: wrong-detail, misattributed-matter, misattributed-document and misclassification;
  - one tag, `run ended: text reply without finish`: the various "run ended without finish" tags.

### A5. Validation (`check.py`)

`check.py` checks, for every run:

- stages are contiguous, cover every tool-call event exactly once, and end at `finish` or with a `run ended: …` tag;
- every stage, tag, hindsight value and error kind exists in `taxonomy.md`;
- no hindsight words or matter numbers appear in stage names, notes or tags;
- each failing run has a `first_error` that matches a stage row, and no passing run has one;
- the markdown markers and error lines match the JSON;
- outcomes match `runs_index.json`;
- no `NEW:` remains.

Final result: **ALL CHECKS PASSED** on 80 tasks, 240 runs and 213 first errors.

### A6. Result: the stage vocabulary (training only)

15 stages:

1. List files in the document store
2. Read documents picked from the file listing
3. Search file contents for request keywords
4. Search file names for request keywords
5. Search file names for a document type
6. Scan document text with an extraction script
7. List matter folders
8. List files in candidate matters
9. Screen candidate matters by reading documents
10. Search within a candidate matter's files
11. Read a chosen matter's documents in depth
12. Calculate figures for the answer
13. Write the response
14. Check or revise the response
15. Finish the run

The vocabulary also has 12 tags, 16 hindsight values and 15 error kinds; see `taxonomy.md`.

The merge also produced 5 **stage groups**, by clustering stage-to-stage transitions:

| Group | Stages |
|---|---|
| Start from the store listing | 1, 2 |
| Search the whole store | 3–7 |
| Choose and screen candidates | 8, 9 |
| Verify the chosen matters | 10, 11 |
| Compose and deliver the answer | 12–15 |

The groups are an **analysis view only**. The harness uses the individual stages; we briefly used the groups as declarable stages by mistake and reverted (see section 6).

### A7. Result: failure patterns per stage (`failure_patterns.md`)

`failure_patterns.md` contains:

- a table of first-error kind × stage;
- for every stage, its patterns with first-error and later-error counts, 2–3 example runs, and what passing runs did differently (from the `divergence` fields of the 16 tasks with a passing run);
- group-level transitions and run-level contrasts.

The most common first errors (213 failing runs):

| Pattern | Stage | Count |
|---|---|---|
| Capped store listing treated as the whole store | Read documents picked from the file listing | 39 |
| Content grep missed the matter (email-only hits, empty globs) | Search file contents | 37 |
| Scan timed out and the partial result was accepted | Scan document text | 34 |
| Matter surfaced but never opened | Screen candidates | 29 |
| Over-inclusion | Write the response | 18 |
| Uncapped scan output overflowed the context | Scan document text | 15 |
| File-name search output was cut off | Search file names | 13 |

Two run-level contrasts: every passing run searched the whole store at least once, and 38 failing runs never did.

**Typical tools per stage** are the tools passing runs used in each stage. We also computed each tool's share of a stage's calls in passing runs, but the shares were nearly the same in passing and failing runs (e.g. store-wide search: bash 49% / grep 25% / glob 20% passing vs 45% / 25% / 23% failing). The shares do not separate success from failure, and they can steer the agent toward the tools behind the top failures (grep cannot read .docx; glob stops silently at 100 files). So the harness shows tool names only, and the examples carry the successful behaviour (see change #16).

### A8. Rule: a stage only learns from failures at that stage

What the harness tells the agent about a stage must come from errors that the annotation placed **at that stage**, in the training runs:

- **`failure_patterns`**: only first errors and later errors whose stage is this stage in `failure_patterns.md`. If no error was placed at a stage, its list says exactly "No failures were recorded at this stage in the training runs", and nothing else.
- **`passing_runs`**: only what passing runs did differently with respect to those same errors. A stage with no recorded failures has no contrast.
- **`examples_from_successful_runs`**: describe only what happened inside the stage, not what the run did afterwards.
- **Not allowed:** observations borrowed from other stages, run-level facts, or knowledge from outside this training data (earlier campaigns, the harness source code).

Why: each stage's critic and checklist must be grounded in what actually goes wrong at that step, so stage-level feedback stays attributable and the method can be repeated on a new model without prior knowledge.

This rule was made explicit after a review of the first version. That version was used by campaign 29: the store-listing stage carried a warning that the whole-store glob is silently capped, but the errors that cap causes were placed at the *next* stage (reading documents from the listing). The fix applied for the next round:
- **No-error stages:** List files in the document store, List matter folders and Calculate figures for the answer now say only "No failures were recorded".
- **Non-failure note removed:** "only seen in failing runs" for Search file names for a document type.
- **Cross-stage clauses trimmed:** removed from the examples and passing notes of Read documents picked from the listing, Search file contents and Scan document text, and the passing note of Search file names was rewritten.

### A9. The stage catalog and `build_stage_reference.py`

Everything the harness tells the agent about a stage is **generated** from the training catalog by one script, never written by hand:

- **The catalog** is `analysis/stages-train/` (annotations, taxonomy, logs), built from training runs only. Each error in it is linked to the stage where it was placed.
- **The script** is `scripts/stage/build_stage_reference.py`. For each declarable stage it:
  1. counts the error kinds placed at that stage (first and later errors);
  2. keeps only the **most common kinds**, at most 4, each seen in at least 2 runs;
  3. asks an LLM (`claude-sonnet-5-5`) to write one generic sentence per kept kind, from that stage's own error descriptions;
  4. has the same LLM write `purpose`, `when_to_use`, `passing_runs` (only when failures were kept) and up to 2 examples, from the passing runs' notes for that stage;
  5. takes `typical_tools` from the tools passing runs used in that stage;
  6. sets `surfaced_not_opened.show_at_stages` to the stages whose kept kinds include `surfaced-not-opened`.

  It writes `stage_reference.json` and regenerates the "## Stage protocol" list in the system prompt.
- **Not bloated.** The output is rebuilt from the whole catalog each time, and holds only the top kinds per stage. It is never appended to: rare errors drop out, and new common ones replace them.
- **Loop.** After each evolution round:
  1. annotate the new training runs with the same taxonomy;
  2. add them to the catalog;
  3. rerun the script.

  The harness's stage knowledge follows the training evidence, and test data never enters it.

With several rounds, pass each round's catalog to `--catalog` (counts are pooled) and the newest taxonomy to `--taxonomy`. For round-2 catalogs, which hold the agent's declared stage labels, the script also counts declared → annotated relabels and writes `often_confused_with` per stage (≥5 relabels, top 2). It also rewrites the `stage_start` enum.

Run it with:

```bash
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
python3 harvey-ahe-project/scripts/stage/build_stage_reference.py \
  --catalog harvey-ahe-project/analysis/stages-train \
  --harness harvey-ahe-project/harness_stage
```

Result on the current catalog (2026-10-28):

| Stage | Kept error kinds (runs) |
|---|---|
| Write the response | over-inclusion (81), under-inclusion (28), misstated-facts (14), hedged-answer (2) |
| Screen candidate matters by reading documents | surfaced-not-opened (41), listed-document-not-opened (2), miscount (2) |
| Read documents picked from the file listing | partial-listing-as-corpus (39) |
| Search file contents for request keywords | search-miss (37) |
| Scan document text with an extraction script | search-miss (35), context-overflow (15) |
| Search file names for request keywords | search-miss (13) |
| List files in candidate matters | surfaced-not-opened (10) |
| Search within a candidate matter's files | surfaced-not-opened (3) |
| The other 6 stages | none recurring: "No recurring failures were recorded at this stage" |

The hand-written version used by campaign 29 is kept at `analysis/stage_reference.handwritten.json` for comparison.

### A10. Round-aware building: active failures, stage policy, regressions

From round 3 on, `build_stage_reference.py` takes the catalogs **oldest round first** and treats the last one as the latest round. For each stage, the error kinds placed there are split into three groups:

- **Active failures:** kinds seen in ≥2 runs of the *latest* round. There is no cap. A stage with more than 5 active kinds prints `SPLIT HINT`, a prompt to check whether its errors belong to different sub-activities.
- **Stage policy:** kinds that were common in an earlier round and have fallen to ≤25% of that peak, or ≤1 run, in the latest round. "Common" means ≥2 runs in a single earlier round **or** ≥2 runs pooled over the earlier rounds. The pooled condition was added for round 4 (change #28), after a kind seen in 1 run in each of two rounds (listed-document-not-opened at "Read a chosen matter's documents in depth") was dropped instead of kept. The guidance worked, so the lesson is kept as a short positive rule ("keep doing X"), shown when the stage starts and checked by the critic.
- **Dropped:** kinds that were never common.

A kind that had become rare and is common again prints `REGRESSION` and goes back into the active failures.

Why:
- Ranking by pooled counts with a top-4 limit could drop a warning that had worked, and the old mistake could come back. That is the ping-pong risk raised in the round-3 discussion (section 8).
- A plain list that only grows would fill up with stale warnings.

Policy keeps what worked in a compact form. Active failures follow the latest round.

**Caveat:** a drop is not always caused by the warning. Context overflow fell after the critic stopped recommending overflowing scans, not only because of Scan's warning. So promotion to policy is evidence of what works, not proof, and a policy line can be tested later by removing it.

---

## 4. Phase B: the stage-protocol harness (final mechanism: `harness_stage_r3/`)

The mechanism was built over rounds 1–3 (history rows #4–#26) and then frozen (#33): from then on a round changes only the learned stage content (the stage list and the regenerated `stage_reference.json`), never the code. `harness_stage_r4/` is r3 plus the steering gate, which was tried and dropped (#32, #34). The first version, `harness_stage/` (r1, campaign 29), is described in **Appendix A**. Exact schemas, prompts and parameters are in the replication guide, sections 9–10.

`harness_stage_r3/` is a copy of `harness_lab/`, the base C0, plus the files below. Nothing in NexAU or the runner was changed.

| File | Role |
|---|---|
| `middleware/stage_reference.json` | **Generated** by `scripts/stage/build_stage_reference.py` from all training catalogs (A9, A10). Per stage: `purpose`, `when_to_use`, `typical_tools`, `examples_from_successful_runs`, `expected_activity`, `policy`, `failure_patterns`, `passing_runs`, `often_confused_with`. Plus the optional run-fact block (B5a). Training data only. |
| `tools/stage.py` | `stage_start`, `stage_end`, the stage classifier (effective stage), the critic call and the review text. |
| `tool_descriptions/stage_start.tool.yaml`, `stage_end.tool.yaml` | Tool schemas. `stage` is an enum of the declarable stages plus `new`, written by the build script. Both tools are `disable_parallel: true`. |
| `middleware/stage_guard.py` | Enforces the protocol, records each stage's calls, updates the run fact, runs the stage-fit check, and handles text-only replies. |
| `middleware/stage_common.py`, `tools/_stage_common.py` | Twin helper modules: per-trial state in agent-state global storage, reference loading, and the critic/fit `chat()` call to CAO. They are twins because the conformance check (see section 5) attributes modules imported by tools to *tool_implementations* and modules imported by middleware to *middleware*. A shared module fails with "runtime-attached … component is not declared". |
| `agent.yaml` | Registers the two tools and `middleware.stage_guard:StageGuardMiddleware`. |
| `systemprompt.md` | "## Stage protocol" section after "Tool conventions"; its stage list is regenerated by the build script. |

### B1. Declarable stages

The stage list is learned content: the training stages except "Finish the run" (14 in r1–r3; 15 from r4, after #31 promoted "Tabulate candidate matters from saved results"). `finish` ends the run, so it cannot be a stage that gets closed with `stage_end`; it is called after the last stage is closed.

`stage="new"` plus `new_stage_name` lets the agent define its own stage when none fits. Agent-defined stages are annotated each round and promoted under rule #29. The prompt presents the stages as a **menu, not a sequence**: any order, repeats and skips are allowed.

### B2. System prompt section

For each stage, generated from the reference:

- its purpose;
- **When** to use it;
- **Typical tools** (names only, no shares; #16);
- 1–2 **examples** of what passing training runs did there;
- **Not for:** the stages it is most often mistaken for (≥5 annotated relabels; #21).

It then gives the rules (written once by hand):

1. Start a stage before any work.
2. Only one stage may be open at a time.
3. Stage calls must be alone in their turn.
4. Read the start notes and the end review.
5. Reopen the stage or move on.
6. Act on stage-fit notes.
7. A text-only reply does not end the task.

### B3. `stage_start(stage, goal, new_stage_name?)`

It validates the stage name, requires a concrete goal, opens the stage with an attempt counter (reopened stages are numbered), and returns:

- the stage's purpose and the agent's goal;
- **"Check the label"**: for each often-confused stage, "if you are going to <its purpose>, that is the stage X: close this stage and start that one" (#21);
- **"Policy for this stage"**: lessons whose errors became rare after earlier guidance (A10, #24);
- **"Watch out: failures seen at this stage in past runs"**, the stage's `failure_patterns`, plus what successful runs did there.

The failures are shown at the start as well as at the end because a run can die inside a stage (for example, an uncapped scan overflowing the context) before it reaches `stage_end` (#13).

### B4. `stage_end(goal_reached, summary)`

1. **Effective stage** (#25). `claude-haiku-5-5` classifies the stage's calls into one listed stage. If that differs from the declared stage, its failures and policy are added to the critic's checklist and to the review. The agent's labels were often wrong and the label note was mostly ignored, so the right feedback is applied anyway.
2. **Run fact** (B5a): only at the stages where it is switched on.
3. **Critic**: `claude-sonnet-5-5` via CAO, a different model family from the solver (`gpt-5.6-luna`) and from the judge (`gpt-5.6-sol`). It receives:
   - the request;
   - the stage, its purpose, the agent's goal, and the agent's self-assessment and summary;
   - the stage's failure patterns (plus the effective stage's) and its policy;
   - from the 3rd opening of the same stage: the earlier goals and an instruction to recommend a different approach, optionally a **new stage** (#26);
   - every other stage's failure patterns: its recommendation must not lead into them (#22);
   - the run fact, where switched on;
   - every tool call in the stage (arguments up to 400 characters, results up to 700; total 40K characters).

   It must flag a failure only with the specific call, result, matter or document that shows it, never as a generic warning (#22). It returns JSON: `goal_reached` (yes / partly / no), `applicable_failures`, `concerns`, `recommendation`, `new_stage`. It does not know the right answer and judges only from the log.
4. **Review** returned to the agent:
   - the agent's own assessment;
   - the critic's verdict, flags, concerns and recommendation;
   - "Label: these calls looked like X work …", if there is an effective stage;
   - the critic's suggested new stage, or, from the 3rd opening, a prompt to try a different approach;
   - the run fact, where switched on;
   - the stage's failure patterns (plus the effective stage's) and what passing runs did;
   - an instruction:
     - if the goal was reached: *reconsider; if anything applies, reopen with the same stage and a goal saying what you will fix; otherwise start the next stage*;
     - if not reached: *reopen this stage with a sharper goal that follows the recommendation, or start a different stage*.

Reopening is advised, never forced: the critic's verdict ("partly" in about 80% of reviews) does not separate passing from failing runs well enough to force on. If the critic call fails, the review says "reviewer unavailable" and still lists the patterns.

### B5. Enforcement: `stage_guard.py`

It uses NexAU's `wrap_tool_call` hook, which can refuse a call without running it by returning `{"status": "error", …}`. This also keeps the run going for the stop tool, because NexAU only stops when the stop tool succeeds.

| Situation | Action |
|---|---|
| `stage_start` while a stage is open | Refused: "close it with stage_end first" |
| `stage_end` with no open stage | Refused |
| A work tool (`bash`, `read`, `write`, `edit`, `glob`, `grep`) with no open stage | Refused: "call stage_start first" |
| `finish` while a stage is open | Refused |
| A turn mixing `stage_start` or `stage_end` with other calls | Every call of that turn is refused: stage calls must be alone, so the order is unambiguous. Detected in `after_model` from `parsed_response.tool_calls`; the call IDs are stored and refused in `wrap_tool_call`. |
| The model replies with no tool call (which would end the run) | `after_model` returns `force_continue=True` and adds a framework message telling the model to continue, close the stage and call `finish`. |

There is **no loop breaker, by design**: if a run keeps getting refused, we want to see it.

The middleware also:

- **Records** every work call inside a stage (tool, arguments, start of the result) for the critic.
- **Updates the run fact**, if one is enabled (B5a).
- **Checks stage fit** for `bash`, `grep` and `glob`: `claude-haiku-5-5` compares the call with the stage's `expected_activity`. On a mismatch it appends a note to the result ("this looks like X; if you moved on, close the stage and start the matching one") and logs it. Writing to the output directory outside the writing stages also adds a note, by rule.
  - It **does not block**. We decided against hard per-stage tool limits:
    - `bash` can do anything;
    - only 27 passing runs existed when this was decided;
    - the agent might pick a stage label just to get a tool;
    - with no loop breaker, a blocked needed tool could stall a run.
- **Captures the request** from the first user message, in `before_model`.

#### B5a. Run facts, and our one example: surfaced but not opened

A **run fact** is a deterministic check computed from the run's own trace that bears on one error kind. It is shown to the critic and in the review only at the stages where that error kind is active in the latest round. Run facts are optional and benchmark-specific: the mechanism only needs to know where to show one; what it tracks is up to the benchmark.

Ours, `surfaced_not_opened`, tracks matters that appeared in search results but were never opened:

- **Origin (stated honestly).** This was a design choice, not something the bottom-up annotation produced. It was first proposed as "give the critic facts from the run, not just a checklist", and its first justification ("listed but not opened was the first error in 48% of failing runs") came from the **test-run analysis that was later archived**. The training annotations support it on their own, with the error kind `surfaced-not-opened` placed 57 times (first and later errors): Screen candidates 41, List files in candidate matters 10, Search within a candidate matter's files 3, Write the response 2, Scan document text 1.
- **Tracking.** A matter number counts as *surfaced* when it appears in a grep, glob or bash result that shows 1–150 matter numbers; a result showing more is a full listing, not a hit list. It counts as *opened* when it appears in the arguments of `read`, `glob` or `bash`.
- **Scope (rule A8).** The list goes to the critic and the review **only at the stages whose active errors (A9, A10) include `surfaced-not-opened`**. At every other stage the line is omitted. In campaign 29 it was still shown at every stage.
- **Configuration.** The block `surfaced_not_opened` in `stage_reference.json` holds `enabled`, `entity` (display name, "matter"), `entity_regex` (`\b\d{4}-\d{5}\b`), `max_entities_for_hit_list` (150) and `show_at_stages`. `entity`, `entity_regex` and the maximum are hand-set; the build script fills `show_at_stages` and `enabled`.
- **Another benchmark.** Define a run fact only for an error kind its own training annotations show is common, and only if it can be computed reliably from the trace. Its settings depend on what it tracks. Without one, leave the block out.

### B6. Critic and fit-check calls

`chat()` in the two `*stage_common.py` files is a plain urllib POST to `STAGE_CRITIC_URL` (default `http://127.0.0.1:4141/v1/chat/completions`), with key `CAO_API_KEY` taken from the environment. The run script exports it from the gateway key file; never print the key. Models are set by environment variables:

| Variable | Default |
|---|---|
| `STAGE_CRITIC_MODEL` | `claude-sonnet-5-5` |
| `STAGE_FIT_MODEL` | `claude-haiku-5-5` (fit check and stage classifier) |
| `STAGE_CRITIC_TIMEOUT` | 180 s |

Notes:

- `harvey_ahe/candidate_checks.py` bans network imports in harness Python. That check runs only when Evolve validates candidates, not in evaluation-only runs, so this hand-built harness works.
- To use the harness inside an Evolve campaign, the ban would need an exception, or the critic would have to move into the adapter.
- Results obtained with a second model in the loop must be reported as such.

---

## 5. Running it

### Configs and scripts

| File | Purpose |
|---|---|
| `ahe-cao-c28-stage-smoke3.yaml` | Smoke test: 3 training tasks (003, 034, 167), 1 trial each, split `splits-firm-knowledge-c28-stage-smoke3.json` |
| `ahe-cao-c29-stage-train80.yaml` | Full training run: 80 tasks × 3, split `splits-firm-knowledge-80-20-20.json`. Concurrency 20, requests 24, judge calls 18. |
| `scripts/run_c28.sh` | Wraps `scripts/run_c0_train_only.py`. Retries up to 12 times on a non-zero exit (e.g. a `podman info` timeout). The config comes from `CFG=…`, and log names from `TAG=…`. |

Both configs copy campaign 24's agent, judge, helper and endpoint settings; only the harness and split change.

Launch the full run from the repository root, inside tmux:

```bash
CFG=harvey-ahe-project/ahe-cao-c29-stage-train80.yaml TAG=c29 \
  bash harvey-ahe-project/scripts/run_c28.sh
```

Artifacts go to `campaign-artifacts/harvey-lab-campaign-29-cao-stage-train80/evaluations/C0-train/units/*/attempt-*/`, with `trace.jsonl`, `result.json` and `grading/…/scores_judge-1.json` per run. Logs are in `campaign-artifacts/c29-run.log` and `c29-run-detail.log`.

### Checks before a run

1. **Harness conformance.** The baseline freeze validates attachment. Every `.py` under `tools/` must be imported only from tools, and every `.py` under `middleware/` only from middleware.
2. **Offline unit test.** `scripts/stage/stage_unit.py` drives the tools and middleware with a fake agent state and checks:
   - refusals;
   - `stage_start` output;
   - surfaced/opened tracking, and that the list appears only at the configured stages;
   - mixed-turn refusal;
   - the critic review (real CAO call);
   - `force_continue`;
   - the `new` stage.
3. **CAO models.** Check that `claude-sonnet-5-5` and `claude-haiku-5-5` answer on `/v1/chat/completions`.

### Inspecting runs

`scripts/stage/stage_runs.py <evaluation dir>` prints, per run:

- the judge score and termination reason;
- tool counts;
- the number of stages and reopens;
- refusals, fit notes and critic availability;
- the stage sequence.

`scripts/stage/live.py <runtime dir>` reads the latest `model_calls/*/request.json`. Requests there are Responses API objects: `kwargs.input` holds `function_call` and `function_call_output` items.

---

## 6. History of design changes

| # | Change | Why |
|---|---|---|
| 1 | Test-task annotations archived; everything redone on training runs | Avoid contaminating the harness with test information |
| 2 | Labels written from the agent's view; hindsight kept in separate fields | The agent did not know which matter was the answer |
| 3 | Descriptive stage names that are benchmark-level, not task-level | Comparable across tasks; readable |
| 4 | Stage start/end are **tools**, not text markers | With tool calling, the model rarely writes text next to calls; tools are structured and enforceable |
| 5 | "Goal not reached" handled by **reopening with a new `stage_start`**, rather than removing the end marker | One mechanism for both cases; honest, auditable history |
| 6 | Critic uses facts from the run (surfaced-not-opened list), not just a checklist | A model asked "did you reach the goal?" tends to say yes |
| 7 | Independent critic and fit checker on a **different model** (via CAO) | Less self-confirmation |
| 8 | No hard per-stage tool limits; soft notes plus logging | See section B5; decide from data later |
| 9 | Custom stages (`stage="new"`) | Room for new solution paths. Plan: promote custom stages seen in passing runs into the taxonomy each round |
| 10 | No loop breaker | Observe what happens first |
| 11 | ~~Model declares the 5 groups~~ → reverted to the **individual stages** | The user wanted stages, not groups; groups stay an analysis view |
| 12 | System prompt gives each stage When, Tools in successful runs and Examples from successful runs | A one-line purpose was too thin to choose a stage |
| 13 | Failure patterns shown at **`stage_start` as well as `stage_end`** | A run can end inside a stage (context overflow) before seeing the end review |
| 14 | Twin helper modules for tools and middleware | Harness conformance attributes imports by caller |
| 15 | Cost and extra turns are not optimised for now | The user's priority is behaviour, not cost |
| 16 | Tool-usage percentages removed from the prompt; tool names kept as "Typical tools" | Shares were nearly the same in passing and failing runs, could steer toward failure-prone tools (grep, capped glob) and discourage exploration. The first 80×3 launch (with percentages) was stopped after 20 runs and restarted; its partial results are in `campaign-artifacts/c29-aborted-pct/` |
| 17 | Stage feedback restricted to errors placed at that stage (rule A8); cross-stage notes removed | Insights must be learnable from the failures of that stage in training runs; the first version had borrowed cross-stage observations. Applied after campaign 29, for the next round |
| 18 | Surfaced-not-opened list shown only at the 5 stages where training placed that error; tracked entity made configurable (`surfaced_not_opened` block) | Its first justification came from archived test analysis; showing it at every stage broke rule A8; the matter-number regex was benchmark-specific (B5a). Applied after campaign 29, for the next round |
| 19 | `stage_reference.json` generated by `build_stage_reference.py` from the training catalog (top error kinds per stage, regenerated each round) instead of written by hand | Stage knowledge must come only from the stage-linked training error catalog, not from the designer's knowledge or test data, and must stay compact as rounds add runs (A9). Applied after campaign 29, for the next round |
| 20 | Round-2 stage reference built from both rounds' catalogs (`--catalog` takes several folders) | The loop of A9; errors moved from search to Write and Scan |
| 21 | Stage-confusion check: each stage lists the stages it is most often mistaken for (≥5 annotated relabels), in the prompt ("Not for: … That is X") and at `stage_start` ("Check the label …") | 21% of declared stage spans in campaign 29 were mislabelled, so the wrong stage's feedback and checklist were used |
| 22 | Critic must cite specific evidence for each flagged failure; its recommendation must not lead into another stage's known failures (it now receives all stages' patterns); the hand-written list of failure types in its system prompt removed | 56 of 114 flagged first errors in campaign 29 were generic stock flags; reviews recommended scans that then overflowed, and pushed decisions behind 223_T0 and 230_T0 |
| 23 | Round-aware build (A10): active failures from the latest round only (no cap), stage policy for errors that became rare after guidance, `REGRESSION` and `SPLIT HINT` checks | Pooled top-4 counts risked dropping working warnings (ping-pong) or keeping stale ones; user idea: a lesson that worked becomes the stage's "policy" |
| 24 | Policy shown at `stage_start`, before the "Watch out" failures; the critic checks it still holds | Policy is what to keep doing in that stage; the failures are what still goes wrong |
| 25 | Review against the stage the calls actually belong to: at `stage_end` the fit model classifies the stage's calls; if they match another stage, that stage's failures and policy are added to the critic's checklist and the review, with "Declare X for this kind of work" | Round 3: the label note at `stage_start` was followed 9 times and ignored 392 times. Rather than relying on the agent's labels, apply the right stage's feedback anyway |
| 26 | Critic suggests a different approach, optionally a **new stage** (name and goal), when a stage is opened a 3rd time; the review offers `stage="new"` | No exploration so far (the agent never used `new` in 720 runs); reopens are frequent (about 5 per run in r2); being stuck is the natural moment to try something new |
| 27 | **Not applied:** splitting Write into "Decide which candidates qualify" + "Write the response" | The agreed criterion (passing runs show a distinct decision sub-step) is not met in the training data: within mixed tasks, the last stage before writing states include/exclude decisions in 7/26 passing vs 10/22 failing runs (r1) and 8/22 vs 11/26 (r2). Decision (user, 2026-10-28): keep it out until the training data supports it; re-check this criterion after each round |
| 28 | Policy eligibility also counts pooled earlier rounds (≥2 runs pooled **or** in one round) | Check of r1/r2 → r3 feedback: every r2 error kind survived in r3 as active or policy except one (listed-document-not-opened at Read in depth, 1 + 1 runs over two rounds), which the per-round rule dropped. Applied from round 4 |
| 29 | Promotion rule for agent-defined (`new`) stages: group them by what their calls do (not by name); promote a group to the stage list if it occurs in ≥2 different runs, at least one of which all-passed, and no existing stage describes it; give it a generic, benchmark-level name | r3 runs started using `new` stages (60 of the first 86 runs, against 0 of 720 before); exact names rarely repeat, so counting by name would never promote anything (user decision). Applied from round 4 |
| 30 | Stage-level steering (enforced rules between stages) is in scope, if the round's data supports it | Round 3: advice at Screen and Write reached its limit (98 specific or generic flags ignored). User decision before round 4 |
| 31 | New stage **"Tabulate candidate matters from saved results"**, promoted under rule #29 | Round 4: 142 spans in 100 runs, 26 passing, work only on saved hit files, which no existing stage describes (Scan extracts from documents, Calculate computes answer figures) |
| 32 | **Steering gate** at stages chosen from data. A review at a gated stage with specific flags and verdict "partly" or "no" blocks starting a different stage, unless `override_reason` explains each flag. Reopening clears it; overrides are logged. Gated if ≥5 specific flags were ignored there in the latest round and review-endorsed ≤25% of that (round 4: Scan, Screen; not Write) | Round 4: specific flags ignored at Screen 21 (3 endorsed), Scan 13 (0), Write 32 (10 endorsed). Applied in r4 |
| 33 | **Mechanism frozen.** Rows 1–32 built the mechanism. From now on a round changes only the learned stage content (the stage list and the regenerated stage reference); stage tools, guard, critic, review format and build script stay unchanged. A proposed mechanism change is a separate experiment, not a round | User decision (2026-11-02): the system is built; rounds must only learn stages, not change components |
| 34 | **Steering gate dropped** (row 32): the final mechanism is r3's; r4 = r3 + gate | r4 training all-pass 26.7% vs r2 30.8% and r3 29.6%; the gate fired in 227/240 runs with 598 reopens and 304 overrides, without gain. User decision (2026-11-02): not needed, too much |

Ideas discussed but not built yet:

- **Exploration.** Across parallel runs, have the critic sometimes suggest a stage or path not yet tried, then mine passing runs for new stages. *Built in part as #26: the critic suggests a new stage when a stage is stuck (3rd opening); not across parallel runs.*
- **Promotion loop for custom stages.** After each training round, annotate `new` stages and add those that recur in passing runs to the taxonomy, with their own failure patterns. *Built from round 4 with the rule of change #29.*

---

## 7. Results so far

### Smoke test

Campaign 28: 3 training tasks, 1 trial each, with the 14 stages but before the per-stage examples and start-of-stage patterns were added.

| Task | Judge | End | Calls | Stages | Reopened | Refused | Fit notes |
|---|---|---|---|---|---|---|---|
| 003 | **3/3 pass** | finish | 99 | 11 | 5 | 0 | 6 |
| 034 | **2/2 pass** | finish | 42 | 9 | 3 | 0 | 0 |
| 167 | 1/5 | context overflow | 8 | 3 | 1 | 0 | 0 |

- The critic answered at every stage end.
- No `new` stages were used: in these runs the 14 stages covered everything the agent did. That needs confirming on the full run, because the enum and the menu may also steer the agent.
- In 167, an uncapped extraction scan overflowed the context inside the stage. That led to change #13.
- In an earlier run using the groups, the critic flagged "treated the capped whole-store listing as the full store (5 of ~266 matters)" and the agent reopened the stage to enumerate every matter. That listing mistake is the most common first error in training.

### Full training run

Campaign 29 (80 × 3) started on 2026-10-27 at 22:14 IST (relaunched without the tool percentages; the first launch at 21:57 was stopped after 20 runs: 7/20 all-pass, 2 context overflows, no `new` stages). The comparison point is campaign 23's C0 on the same 240 training runs: 11.3% all-pass, criterion pass rate 0.394.

**Result** (finished 2026-10-28, 12:42 IST):

| | Base C0 | Stage harness r1 |
|---|---|---|
| All-pass | 27 / 240 (11.3%) | **64 / 240 (26.7%)** |
| Criterion pass rate | 0.394 | 0.631 |

The all-pass difference is +15.4 points, 95% CI [+8.3, +22.5], bootstrapped over tasks. These are training tasks whose base-harness runs built the stage reference, so the gain is optimistic; validation and test are the fair check.

### Round 2 (annotation of campaign 29)

Full report: `analysis/round2-c29-analysis.md`. Catalog: `analysis/stages-train-c29/`. In short:
- **What the stage harness removed:** treating the capped listing as the whole store (39 → 0 first errors) and most search misses (85 → 17).
- **Where failures moved:** judgement at Write (over-inclusion 39, under-inclusion 18) and context overflow at Scan (33, always before any review).
- **Critic:**
  - it flagged 122 of 176 first errors, but 74 of those flags were ignored and about half were generic stock warnings;
  - its verdict ("partly" in 83% of reviews) barely separates passing from failing runs;
  - in a few runs it steered toward the error.
- **Stage labels:** 21% of declared stage spans were mislabelled (e.g. screening declared as in-depth reading).
- **New stages:** none were found.

The resulting proposal is `harness_stage_r2` (changes #20–#22).

### Round 2 result (campaign 30: `harness_stage_r2`, 80 training tasks × 3, finished 2026-10-28 at 16:10 IST)

| | Base C0 | r1 (campaign 29) | r2 (campaign 30) |
|---|---|---|---|
| All-pass | 27 / 240 (11.3%) | 64 / 240 (26.7%) | **74 / 240 (30.8%)** |
| Criterion pass rate | 0.394 | 0.631 | **0.679** |
| Tasks passing 0 / 1 / 2 / 3 of 3 runs | 64 / 7 / 7 / 2 | 49 / 8 / 13 / 10 | 46 / 10 / 8 / 16 |

Differences in all-pass (95% CI, bootstrapped over tasks):
- r2 vs r1: +4.2 points, CI [−1.3, +10.0];
- r2 vs C0: +19.6 points, CI [+12.5, +27.1].

These are still training tasks.

---

### Round 3 (annotation of campaign 30) and the proposed `harness_stage_r3`

Full report: `analysis/round3-c30-analysis.md`. Catalog: `analysis/stages-train-c30/`.

**Errors:**
- context overflow fell 34 → 5;
- the remaining first errors are at Screen (surfaced-not-opened 41) and Write (over-inclusion 41, under-inclusion 24).

**Critic:**
- specific flags rose 58 → 75;
- ignored flags rose 74 → 98;
- reviews that pushed toward the error rose 1 → 10.

**Labels and stages:** the label note was followed 9 times and ignored 392 times. No new stages.

`harness_stage_r3` adds changes #23–#26:
- the reference is built round-aware from all three catalogs;
- stage policy is shown at `stage_start`;
- the review covers the stage the calls actually belong to;
- the critic suggests a new approach or stage when a stage is stuck.

It has not been run yet.

### Round 4 (annotation of campaign 31) and `harness_stage_r4`

Full report: `analysis/round4-c31-analysis.md`. Catalog: `analysis/stages-train-c31/`.
- **r3 result:** 29.6% all-pass, the same as r2 (CI [−5.8, +3.3]).
- **First errors:** found but not opened keeps rising (41 → 56 → 64), mostly at Screen.
- **Exploration:** the agent used agent-defined stages in 155 runs, mostly copying the critic's suggestions. One recurring step was promoted to a stage (#31).
- **Label notes:** the start note was followed 4 times and ignored 263; the end note 85 and 140.

`harness_stage_r4` adds the steering gate (#32) and was launched as campaign 32 on 2026-10-29 at 03:43 IST.

**Round-4 result** (campaign 32, finished 06:45 IST):

| | All-pass | Criterion pass rate | Tasks passing 0/1/2/3 of 3 runs |
|---|---|---|---|
| r4 | 64 / 240 (26.7%) | 0.670 | 50 / 10 / 6 / 14 |
| r3 | 29.6% | 0.672 | |
| r2 | 30.8% | 0.679 | |

Differences in all-pass (95% CI, bootstrapped over tasks):
- r4 vs r3: −2.9, CI [−8.7, +2.5];
- r4 vs r2: −4.2, CI [−9.2, +0.4];
- r4 vs C0: +15.4.

**The steering gate fired in 227 of 240 runs,** about 3.8 times per run, in passing and failing runs alike. The agent then:
- reopened the stage 598 times;
- gave an `override_reason` 304 times;
- was refused 124 times.

The gate changed behaviour, but it did not improve the score. If anything, it is slightly worse. **The gate was dropped (#34);** the final mechanism is r3's.

### Validation check of r2 and r3 (campaign 33)

The 20 validation tasks × 3 runs, the same tasks as campaign 25. Finished 2026-10-29 at 10:45 IST.

| Harness | All-pass | Criterion pass rate | Tasks passing 0/1/2/3 of 3 runs |
|---|---|---|---|
| Base C0 | 7 / 60 (11.7%) | 0.407 | 15 / 4 / 0 / 1 |
| **r2** | 11 / 60 (18.3%) | **0.653** | 14 / 3 / 1 / 2 |
| **r3** | 11 / 60 (18.3%) | **0.655** | 15 / 1 / 2 / 2 |
| Campaign 23's evolved C3 | 14 / 60 (23.3%) | 0.586 | 14 / 1 / 2 / 3 |

Differences in all-pass (95% CI, bootstrapped over tasks):

| Comparison | All-pass difference |
|---|---|
| r2 vs C0 | +6.7, CI [−5.0, +21.7] |
| r3 vs C0 | +6.7, CI [−5.0, +20.0] |
| r3 vs C3 | −5.0, CI [−10.0, 0.0] |
| r3 vs r2 | 0.0 |

**Reading:**
- On held-out tasks, the stage harness keeps a large gain in **criterion pass rate** (+0.25 over C0, and above C3's 0.586).
- The **all-pass** gain shrinks from +19.6 on training to +6.7, which is within noise on 20 tasks.
- It does not beat campaign 23's evolved harness on all-pass.

So much of the training gain came from feedback tuned to the training tasks, which is the optimism we flagged earlier.

## 8. Insights

Recorded verbatim from the author (2026-10-28):

> adding stages help us capture errors in the longer runs, and provide feedback at a granularity at which the model can be expected to follow. a natural way to also leverage the middlware as it can be triggered when the model thinks to go into the next step without finsih the current step. By this way we are conssciously preventing the model from hallucinating and moving on to the next task befrore it finished the current task. a judge provides feecback if it thinks the model did not finish the previous task and is moving ahead. This can also be leverage to improve parallel sampling since we can sample only failing sections till we thik it passes. it also passess verfier feedback at the right granularity. We also have space for exploration where a model can choose new steps it thinks would relevant. Open Questoin : what is the right granularity to choose stages. Also an insight is that tool calls in themselves don't carry a lot of semantic meaning when looking at it from a task perspective. at a task perspective we usually want to achievesome subgoals, each subgoal is the more meaningul granularity for a human. we also leverage the same as the right granularity for planning. a single tool call doesn't capture a ubgoal picutre. at this granularity we can do stage wise RL to improve certain model deficiencies. we can also mask some subgoals and train others. the insight here is again that solving every day tasks invling learning these workflows in some structure, encourgaing models to output their current stage by putting them as tool calls seems to be a natural way to push them. we can also simply increase test time ocmpute this way by making models generate more and more tool calls. partially by adding newer tools, partially by insinuating the model to tell past failures and ask it to make sure it is not doing that. By adding the "new" step we are giving the model enough ability to explore and try out new things, this also help us build the idea of evolution. a harness evolutoin step may pick these new steps and add them as possible stages to reach the answer.

> the insight is not to provide more information to the model, the insight is to add the right structure in the harness that tells the model to think more and more on a task before coming out saying that it has done. this helps us sort of have more sequential thinking into the model. if the average number of tokens  increase in a model, the average performance also increases. In a sense this helps in redoing only a certain sections of the problems, instead of all of them. so essentially parallel sampling at the right granulairty

> in training time when we are labelling the various steps, perhaps the model learns separte experts for separate tasks. similra to how humans have a different collections of skills, and they may use a different skill in differen subtask to achieve a biger whole goal

Recorded verbatim from the author (2026-11-02), on what a round may change:

> component changes were done in this current run because i was buildng it for the first time. now that we have a system, I would assume that our component changegs are not needed. only the chanes to learning stages mmust be needed !

Notes from the round-3 discussion (2026-10-28; ideas raised by the author and discussed, recorded in summary):

- **Ping-pong risk.** If the reference keeps only each stage's current most common errors, a warning that worked disappears once its error becomes rare, and the old mistake can come back. Pooling counts across rounds softens this but does not remove it (a top-k limit can still push a working warning out), and it keeps stale warnings forever.
- **Stage policy.** When adding an error as guidance makes it nearly disappear, the guidance acts as a *policy* for that stage. Lessons that worked move into a policy text shown when the stage starts. The failure list then holds only what still goes wrong. This replaced the earlier "sticky entries" idea; implemented as A10.
- **Bloat.** Bounded in practice. Each stage has only ever had about 2–5 error kinds over three rounds, and the taxonomy has about 16. Policy lines are short. Retire a policy line only if its error stays at zero for several rounds *and* removing it does not bring the error back.
- **Too many errors at a stage means the stage is too complex: split it.** Agreed in principle, but the count of error kinds is a noisy signal. Write collects most kinds partly because the annotation convention files every judgement error there. The better signal is errors that belong to different sub-activities within one stage (deciding which candidates qualify vs writing the answer up). The split must also be grounded in training data: passing runs should show a distinct sub-step. This criterion was **not** met for Write (see #27); the decision is to keep the split out until the data supports it, and to re-check after each round.
- **Splitting raises mislabelling, and data can also argue for merging.** "List files in the document store" and "List matter folders" were confused 144 times in round 2.
- **Why there is no exploration with `new`:**
  - **Anchoring:** 14 detailed stages, a fixed list of names in the schema, and "new only if none fits".
  - **No incentive:** a `new` stage gets no patterns, examples or checklist.
  - **Mislabelling absorbs the demand:** when nothing fits, the agent reuses the nearest label.
  - **The taxonomy may also be complete at this level of detail:** annotators never needed a new stage either.
  - **`new` names a step; it does not push the agent to try a different strategy.**

  Exploration has to be prompted explicitly, for example by the critic when a stage is stuck (implemented as #26), or in some of the parallel runs.
- **Diminishing returns.**
  - C0 → r1 was +15.4 points (significant); r1 → r2 was +4.2 points (within noise).
  - Reminders fixed what reminders can fix: listing, search and overflow errors.
  - The remaining errors are judgement errors at Screen and Write, where the agent already gets specific feedback and ignores it. More information will not fix these; structure or steering might.
  - *Later (round 4):* steering was tested as the steering gate. It fired in 227 of 240 runs without improving the score, and was dropped (#34).
  - All gains so far are on the training tasks the feedback came from, so validation and test are needed.
- **Preventing mislabelling, options considered:**
  1. Review against the stage the calls belong to (implemented, #25).
  2. Merge or rename stages that are often confused.
  3. Have `stage_start` declare the first planned action and check it against the stage.
  4. Accept labels and let the classifier decide which feedback applies.

## 9. Replicating on another setting

**The full step-by-step guide is `docs/stage-protocol-replication-guide.md`** (schemas, prompts, parameters, components, checklists). In short:

1. **Observe:** run the unmodified agent on the training split, 3 trials per task; build compact logs; annotate the runs into stages and errors (A1–A5); merge the vocabulary.
2. **Build the mechanism once** (section 4): generate `stage_reference.json` from the catalog (A9, A10, rule A8), then add the stage tools, guard, critic, label classifier and prompt section. Optionally define run facts for common, trace-computable error kinds (B5a). Unit test and smoke run, then freeze the code.
3. **Each round:** run the training split; annotate the new runs; update the stage list only where the data supports it (promotion #29, split or merge); rebuild the reference from all catalogs; no code changes.
4. **Stop** when a round's gain over the previous one is within noise.
5. **Evaluate:** choose the round on validation, then compare with the base on test (paired CI), disclosing the second model in the loop.

---

## 10. File index

| Path (under `harvey-ahe-project/`) | What |
|---|---|
| `analysis/stages-train/make_logs.py` | Builds the compact logs and `runs_index.json` |
| `analysis/stages-train/BRIEF.md`, `BRIEF_PARALLEL.md` | Annotation rules |
| `analysis/stages-train/taxonomy.md` | Stage groups, stages, tags, hindsight values, error kinds, conventions, issues |
| `analysis/stages-train/failure_patterns.md` | Failure patterns per group and stage, with counts and examples |
| `analysis/stages-train/changelog.md` | How the vocabulary grew |
| `analysis/stages-train/check.py` | Annotation validator |
| `analysis/stages-train/annotations/<task>.json/.md` | Per-task annotations (240 runs) |
| `analysis/stages-train/proposals/batch-*.md` | Parallel-batch proposals before the merge |
| `harness_stage/` | First stage harness, r1 (Appendix A) |
| `analysis/stages-train-c29/`, `analysis/round2-c29-analysis.md` | Round-2 catalog and analysis |
| `harness_stage_r2/` | Proposed round-2 harness (changes #20–#22) |
| `analysis/stages-train-c30/`, `analysis/round3-c30-analysis.md` | Round-3 catalog and analysis |
| `analysis/stages-train-c31/`, `analysis/round4-c31-analysis.md` | Round-4 catalog and analysis |
| `harness_stage_r3/` | **Final mechanism** (section 4); round-3 harness (changes #23–#26) |
| `harness_stage_r4/` | Round-4 harness: r3 + steering gate (dropped, #34) and the stage list with #31 (changes #28–#32) |
| `scripts/stage/stage_stats.py` | Run-level stage and critic statistics of an evaluation |
| `scripts/stage/build_stage_reference.py` | Generates `stage_reference.json` and the prompt's stage list from the training catalog (A9) |
| `analysis/stage_reference.handwritten.json` | The hand-written reference used by campaign 29 (superseded) |
| `ahe-cao-c28-stage-smoke3.yaml`, `splits-firm-knowledge-c28-stage-smoke3.json` | Smoke-test config and split |
| `ahe-cao-c29-stage-train80.yaml` | Full training-run config, r1 (campaign 29) |
| `ahe-cao-c30-stage-r2-train80.yaml`, `ahe-cao-c31-stage-r3-train80.yaml`, `ahe-cao-c32-stage-r4-train80.yaml` | Training-run configs, r2–r4 (campaigns 30–32) |
| `ahe-cao-c33-stage-r2-val20.yaml`, `ahe-cao-c33-stage-r3-val20.yaml`, `splits-firm-knowledge-c25-c23val20.json` | Validation runs of r2 and r3 (campaign 33) and their split |
| `scripts/run_c28.sh` | Launcher with retries (`CFG`, `TAG`) |
| `scripts/stage/stage_unit.py`, `stage_runs.py`, `live.py` | Offline unit test, per-run summary, live view of running trials |
| `campaign-artifacts/c28-aborted-groups/` | The stopped run that used groups as stages |
| `docs/stage-protocol-harness.md` | This document |
| `docs/stage-protocol-replication-guide.md` | Detailed replication guide |

---

## Appendix A. Phase B as first built: `harness_stage/` (r1, campaign 29)

Kept for reference: how the harness looked before rounds 2–3 completed the mechanism (history rows #4–#19). Section 4 describes the final mechanism. Section labels below are prefixed `r1-` to keep them apart from section 4's.

`harness_stage/` is a copy of `harness_lab/`, the base C0, plus the files below. Nothing in NexAU or the runner was changed.

| File | Role |
|---|---|
| `middleware/stage_reference.json` | **Generated** by `scripts/stage/build_stage_reference.py` (A9). Per stage: `purpose`, `when_to_use`, `typical_tools`, `examples_from_successful_runs` (paraphrased from passing training runs, task content removed), `expected_activity`, `failure_patterns` and `passing_runs`. Training data only. |
| `tools/stage.py` | The `stage_start` and `stage_end` tools, and the critic call. |
| `tool_descriptions/stage_start.tool.yaml`, `stage_end.tool.yaml` | Tool schemas. `stage` is an enum of the 14 declarable stages plus `new`. Both tools are `disable_parallel: true`. |
| `middleware/stage_guard.py` | Enforces the protocol, records each stage's calls, runs the stage-fit check, tracks matters that surfaced but were never opened, and handles text-only replies. |
| `middleware/stage_common.py`, `tools/_stage_common.py` | Twin helper modules: per-trial state in agent-state global storage, reference loading, and the critic/fit `chat()` call to CAO. They are twins because the conformance check (see section 5) attributes modules imported by tools to *tool_implementations* and modules imported by middleware to *middleware*. A shared module fails with "runtime-attached … component is not declared". |
| `agent.yaml` | Registers the two tools and `middleware.stage_guard:StageGuardMiddleware`. |
| `systemprompt.md` | New "## Stage protocol" section, inserted after "Tool conventions". |

### r1-B1. Declarable stages

The 14 training stages, excluding "Finish the run". `finish` ends the run, so it cannot be a stage that gets closed with `stage_end`; it is called after the last stage is closed.

`stage="new"` plus `new_stage_name` lets the agent define its own stage when none fits. The prompt presents the stages as a **menu, not a sequence**: any order, repeats and skips are allowed.

### r1-B2. System prompt section

For each stage, the section gives:

- its purpose;
- **When** to use it;
- **Typical tools** (names only, no shares);
- 1–2 **examples** of what passing training runs did there.

It then gives the rules:

1. Start a stage before any work.
2. Only one stage may be open at a time.
3. Stage calls must be alone in their turn.
4. Read the start notes and the end review.
5. Reopen the stage or move on.
6. Act on stage-fit notes.
7. A text-only reply does not end the task.

### r1-B3. `stage_start(stage, goal, new_stage_name?)`

It validates the stage name, requires a concrete goal, opens the stage with an attempt counter (reopened stages are numbered), and returns:

- the stage's purpose and the agent's goal;
- **"Watch out: failures seen at this stage in past runs"**, the stage's `failure_patterns`, plus what successful runs did there.

Showing the patterns at the start was added after the smoke test. There, a run's uncapped scan overflowed the context inside the stage, so it never reached `stage_end` and never saw the warning.

### r1-B4. `stage_end(goal_reached, summary)`

It closes the stage and calls the **critic**: `claude-sonnet-5-5` via CAO, a different model family from the solver (`gpt-5.6-luna`) and from the judge (`gpt-5.6-sol`). The critic receives:

- the request;
- the stage, its purpose and the agent's goal;
- the agent's self-assessment and summary;
- the stage's failure patterns;
- **only at the stages listed in `surfaced_not_opened.show_at_stages`** (see B5a): the matters that appeared in search results so far but have no document opened or folder listed;
- every tool call in the stage (arguments up to 400 characters, results up to 700; total 40K characters).

It returns JSON: `goal_reached` (yes / partly / no), `applicable_failures`, `concerns` and `recommendation`. The critic does not know the right answer and is told to judge only from the log.

The tool result (the review) contains:

- the agent's own assessment;
- the critic's verdict, flags, concerns and recommendation;
- at the same stages only, the list of matters that surfaced but were never opened;
- the stage's failure patterns and what passing runs did;
- an instruction:
  - if the goal was reached: *reconsider; if anything applies, reopen with the same stage and a goal saying what you will fix; otherwise start the next stage*;
  - if not reached: *reopen this stage with a sharper goal that follows the recommendation, or start a different stage*.

Both cases go through a new `stage_start`, which keeps the history honest and numbers each attempt.

If the critic call fails, the review says "reviewer unavailable" and still lists the patterns.

### r1-B5. Enforcement: `stage_guard.py`

It uses NexAU's `wrap_tool_call` hook, which can refuse a call without running it by returning `{"status": "error", …}`. This also keeps the run going for the stop tool, because NexAU only stops when the stop tool succeeds.

| Situation | Action |
|---|---|
| `stage_start` while a stage is open | Refused: "close it with stage_end first" |
| `stage_end` with no open stage | Refused |
| A work tool (`bash`, `read`, `write`, `edit`, `glob`, `grep`) with no open stage | Refused: "call stage_start first" |
| `finish` while a stage is open | Refused |
| A turn mixing `stage_start` or `stage_end` with other calls | Every call of that turn is refused: stage calls must be alone, so the order is unambiguous. Detected in `after_model` from `parsed_response.tool_calls`; the call IDs are stored and refused in `wrap_tool_call`. |
| The model replies with no tool call (which would end the run) | `after_model` returns `force_continue=True` and adds a framework message telling the model to continue, close the stage and call `finish`. |

There is **no loop breaker, by design**: if a run keeps getting refused, we want to see it.

The middleware also:

- **Records** every work call inside a stage (tool, arguments, start of the result) for the critic.
- **Tracks surfaced vs opened entities** (see B5a). When enabled, an entity identifier (here a matter number) counts as *surfaced* when it appears in a grep, glob or bash result that shows 1–150 entities; a result showing more is a full listing, not a hit list. It counts as *opened* when it appears in the arguments of `read`, `glob` or `bash`.

#### r1-B5a. The surfaced-but-not-opened fact: origin, scope, portability

- **Origin (stated honestly).** This was a design choice, not something the bottom-up annotation produced. It was first proposed as "give the critic facts from the run, not just a checklist", and its first justification ("listed but not opened was the first error in 48% of failing runs") came from the **test-run analysis that was later archived**. The training annotations support it on their own, with the error kind `surfaced-not-opened` placed 57 times (first and later errors): Screen candidates 41, List files in candidate matters 10, Search within a candidate matter's files 3, Write the response 2, Scan document text 1.
- **Scope (rule A8).** The list goes to the critic and the review **only at the stages whose most common errors (as kept by the build script, A9) include `surfaced-not-opened`**. On the current catalog these are Screen candidates, List files in candidate matters, and Search within a candidate matter's files. Write (2) and Scan (1) fall below the cut. At every other stage the line is omitted entirely. In campaign 29 it was still shown at every stage.
- **Configuration.** The block `surfaced_not_opened` in `stage_reference.json` holds:
  - `enabled`;
  - `entity` (display name, here "matter");
  - `entity_regex` (here `\b\d{4}-\d{5}\b`);
  - `max_entities_for_hit_list` (150);
  - `show_at_stages`, set by the build script.

  `entity`, `entity_regex` and the maximum are the only hand-set, per-benchmark values. Both helper modules read the block.
- **Another benchmark.** Enable this only if that benchmark's own training annotations contain a "surfaced but not opened" error kind. Then set `entity_regex` to its entity identifier (a case ID, a file path pattern, a ticket number…); the build script fills `show_at_stages`. Otherwise set `enabled: false`. With the matter-number regex left in place on another benchmark, nothing would match and the line would always read "none".
- **Checks stage fit** for `bash`, `grep` and `glob`: `claude-haiku-5-5` compares the call with the stage's `expected_activity`. On a mismatch it appends a note to the result ("this looks like X; if you moved on, close the stage and start the matching one") and logs it. Writing to the output directory outside the writing stages also adds a note, by rule.
  - It **does not block**. We decided against hard per-stage tool limits:
    - `bash` can do anything;
    - only 27 passing runs exist;
    - the agent might pick a stage label just to get a tool;
    - with no loop breaker, a blocked needed tool could stall a run.
  - The plan is to count mismatches first and decide on limits later, from data.
- **Captures the request** from the first user message, in `before_model`.

### r1-B6. Critic and fit-check calls

`chat()` in the two `*stage_common.py` files is a plain urllib POST to `STAGE_CRITIC_URL` (default `http://127.0.0.1:4141/v1/chat/completions`), with key `CAO_API_KEY` taken from the environment. The run script exports it from the gateway key file; never print the key. Models are set by environment variables:

| Variable | Default |
|---|---|
| `STAGE_CRITIC_MODEL` | `claude-sonnet-5-5` |
| `STAGE_FIT_MODEL` | `claude-haiku-5-5` |
| `STAGE_CRITIC_TIMEOUT` | 180 s |

Notes:

- `harvey_ahe/candidate_checks.py` bans network imports in harness Python. That check runs only when Evolve validates candidates, not in evaluation-only runs, so this hand-built harness works.
- To use the harness inside an Evolve campaign, the ban would need an exception, or the critic would have to move into the adapter.
- Results obtained with a second model in the loop must be reported as such.
