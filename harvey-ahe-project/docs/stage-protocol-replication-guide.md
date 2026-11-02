# Replication guide: stage-level error statistics, feedback and steering for an agent harness

This guide explains, step by step, how to rebuild the **stage-protocol harness** on your own agent and dataset. It assumes no prior knowledge of our project. Every file, schema, prompt, parameter and decision is described here; where we give our concrete choice for the Harvey LAB benchmark, we say what to change for yours.

Companion documents in this repository:

- `docs/stage-protocol-harness.md`: the history of *our* project (why each change was made, results, insights).
- `analysis/stages-train*/`: our catalogs (examples of every artifact described below).
- `harness_stage_r3/`: our final harness, the reference implementation of everything in sections 9 and 10. (`harness_stage_r4/` is r3 plus a steering gate we tried and dropped; see section 12.5.)
- `scripts/stage/`: our scripts.

---

## Contents

0. What you are building
1. Prerequisites
2. Ground rules (read before starting)
3. Step 1: run the unmodified agent on the training split
4. Step 2: build compact logs
5. Step 3: set up the catalog and the annotation rules
6. Step 4: annotate the runs (LLM annotators)
7. Step 5: validate the annotations
8. Step 6: merge the vocabulary
9. Step 7: generate the stage reference
10. Step 8: build the harness components
11. Step 9: test and run
12. Step 10: the round loop (annotate the new runs, rebuild, rerun)
13. Step 11: final evaluation
14. Parameters (all in one table)
15. Cost and time (what it took us)
16. Pitfalls we hit
17. Checklists
18. Glossary

---

## 0. What you are building

An agent solving a task moves through **stages**: purposeful stretches of work such as "search the store", "screen candidates", "write the response". Failures cluster at particular stages. The method:

1. **Observe:** run your unmodified agent on training tasks several times.
2. **Name the stages:** label every run as a sequence of named stages, growing a stage vocabulary bottom-up from the runs themselves.
3. **Place the errors:** for every failing run, mark the stage where it first went wrong and the kind of error.
4. **Aggregate:** per stage, count the error kinds, and record what passing runs did there.
5. **Guide:** change the harness so that the agent:
   - declares each stage and its goal by calling a `stage_start` tool;
   - is shown that stage's policy (lessons that worked) and its current common failures when it starts the stage;
   - closes the stage by calling `stage_end`, which triggers an independent critic (a different LLM) that reviews the stage's tool calls against the stage's failures;
   - reads the review and decides to reopen the stage or move on.
6. **Iterate:** run the guided agent on the training tasks, annotate those runs the same way, regenerate the stage feedback from all rounds, and run again.

Picture of one run under the finished harness:

```
request
  └─ stage_start("Search file contents…", goal)  → purpose + policy + "watch out" failures
       grep …, bash …                           → (optional) stage-fit notes on results
     stage_end(goal_reached, summary)          → critic review + failures + "reopen or move on"
  └─ stage_start(same stage, sharper goal)       (reopen)
       …
     stage_end(…)
  └─ stage_start("Screen candidate matters…", goal)
       read …, read …
     stage_end(…)                              → review also lists entities seen but never opened
  └─ … Write the response … Check or revise …
  └─ finish
```

The hypothesis being tested: **stage-level grouping, per-stage error statistics, and stage-level feedback and steering improve the harness.** Keep every change you make within that scope (see section 2).

Our results on the Harvey LAB firm-knowledge training split, 80 tasks × 3 runs, all-pass rate:

| Harness | All-pass rate |
|---|---|
| Base (C0) | 11.3% |
| Round 1 (r1) | 26.7% |
| Round 2 (r2) | 30.8% |
| Round 3 (r3) | 29.6% |
| Round 4 (r4: r3 plus a steering gate, dropped; section 12.5) | 26.7% |

r2 vs C0 is +19.6 points, 95% CI [+12.5, +27.1]. These are training numbers. On 20 held-out validation tasks × 3, r2 and r3 both reached 18.3% all-pass vs 11.7% for C0, so most of the training gain did not transfer. Validate on held-out tasks before claiming anything.

---

## 1. Prerequisites

You need the following. If one is missing, the method still works, but the named step must be adapted.

| # | Requirement | Why | Our setup |
|---|---|---|---|
| 1 | An agent that works through **tool calls** (function calling) | Stages are declared through tools | NexAU agent, OpenAI tool-call mode, model `gpt-5.6-luna` |
| 2 | A harness framework with these **hooks**: (a) wrap or veto a tool call before it runs, (b) inspect the model's response after each turn and force the loop to continue, (c) see the messages before each model call, (d) per-run state | Enforcing the protocol | NexAU middleware: `wrap_tool_call`, `after_model` (with `force_continue`), `before_model`, agent-state global storage |
| 3 | A dataset with a **train / validation / test split** | Everything is learned from train only | 80 / 20 / 20 tasks |
| 4 | **Per-criterion grading** with the grader's reasoning per criterion | Locating errors needs to know *what* failed | One LLM judge, rubric criteria with pass/fail and reasoning; a run "all-passes" only if every criterion passes |
| 5 | **Full traces** of every run: every tool call with its arguments and its result, in order, with an index, plus the termination reason | Annotation reads them | `trace.jsonl` per run, one JSON event per line |
| 6 | A **second LLM endpoint** (different model family from the agent) | Critic, stage-fit classifier, reference builder | Local OpenAI-compatible gateway; `claude-sonnet-5-5` critic and builder, `claude-haiku-5-5` classifier |
| 7 | An **LLM coding agent** that can read files and write JSON or markdown, and can run several copies in parallel | Annotating hundreds of runs | Claude subagents |
| 8 | A way to **re-run** the agent on the training split with a modified harness, 3 trials per task | Measuring each round | `ahe_runner` eval-only script |

Things that are specific to our benchmark, and that you must replace:

- **The "entity" that answers are made of.** For us it is a *matter number* (`NNNN-NNNNN`) naming a folder in a shared document store. Yours may be a ticket ID, a file path, a product SKU, a case number, or nothing at all. The compact-log target markers (section 4) and the annotation checks (section 7) use it, and so does our one run fact (sections 9.3 and 10.6). If your tasks have no such entity, leave those pieces out.
- **The words that would leak task content** into stage labels (section 7).
- **Domain wording in the critic prompt** ("legal document-search task", section 10.5).

---

## 2. Ground rules (read before starting)

These rules exist because breaking them silently invalidates the experiment.

1. **Training data only.** Stage names, error statistics, examples, recommended tools, critic checklists and every other piece of harness guidance must come from runs on the **training** split. Never look at validation or test runs while designing. If you analysed test runs earlier, move that material out of the project and do not reuse it. We did this once and had to archive a whole analysis.
2. **Agent's view only, in labels.** Stage names, stage notes and tags describe what the agent knew and intended *at that moment*. Never use hindsight words such as "target", "decoy", "correct matter" or "rubric" there. Knowledge from the grader goes only into separate hindsight fields (section 5.4).
3. **Benchmark-level, not task-level, names.** Stage names are descriptive verb phrases that apply to any task in the benchmark ("Search file names for request keywords"). They never contain task content (entity IDs, party names, topic words) and are never codes ("S3").
4. **A stage only learns from failures at that stage** (our rule A8). The feedback for stage X lists only errors that the annotation placed *at stage X*. Do not borrow observations from other stages, from run-level statistics, or from your own knowledge of the system. If no recurring error was placed at a stage, its feedback says exactly that.
5. **Scope: the mechanism is built once; rounds change only what is learned about the stages.** Build the full mechanism once (sections 9 and 10: stage tools, guard, critic, label check, build script) and then freeze its code. Each round may change only the **learned stage content**: the stage list (promoted, split or merged stages, section 12.4) and the stage reference regenerated from the catalogs (failures, policy, examples, typical tools, confusion notes, where run facts are shown). No code changes between rounds. Do **not** add general harness improvements, such as an output cap on every shell call, a better search tool, or prompt tips unrelated to stages. They may help, but they confound the test of the hypothesis. We proposed an output-cap middleware once and rejected it for this reason; the same failure (context overflow) was then fixed through stage feedback (34 → 5 runs).
6. **Every claim must be inferable from the training runs.** If a design idea came from elsewhere (intuition, an earlier campaign, test data), either find training evidence for it or drop it. Record the origin honestly in your design log.
7. **Keep a design log.** For every change: what changed, the evidence behind it, and the round it took effect. Ours is the "History of design changes" table in `docs/stage-protocol-harness.md`.

---

## 3. Step 1: run the unmodified agent on the training split

1. Use your **base harness** exactly as it is. Nothing changes in this round.
2. Run every training task **3 times** (3 trials). Single runs are too noisy: a task with mixed outcomes, where some runs pass and some fail, is where you learn the most.
3. For every run, keep:
   - the full trace: an ordered list of events, each tool call with its name and full arguments, each tool result with its full content, plus any text messages, all with an **event index**;
   - the termination reason (`finish_tool`, `context_overflow`, `max_turns`, `agent_error` …);
   - the grader output per criterion: id, title, verdict (pass or fail), reasoning;
   - the run outcome: `all_pass` (true or false), `n_passed`, `n_criteria`;
   - the task id and trial number.
4. If an infrastructure failure kills a run, re-run that run. If a retry leaves several attempts per run, always use the **latest** attempt.

Our numbers: 80 tasks × 3 = 240 runs; 27 passed, 213 failed.

---

## 4. Step 2: build compact logs

Raw traces are too large to annotate: tool results can be millions of characters. Build one compact, human-readable log per run. This is our `make_logs.py`; the copy in `analysis/stages-train-c30/make_logs.py` handles stage-harness runs.

### 4.1 Format of a compact log

File name: `logs/<task>_T<trial>.txt`.

```
# task <task> trial T<k>  unit <unit id>
# source: <absolute path of the raw trace>
# judge: <n_passed>/<n_criteria> passed, all_pass=<True|False>
# rubric matter numbers (target matters): <entity ids found in criterion titles, or "none named">
#   C-001 [pass] <criterion title> :: <grader reasoning, first 260 chars>
#   C-002 [fail] <criterion title> :: <...>
[1 user] TEXT: <the request, first 1,500 chars>
[2] CALL glob {"pattern": "**/*", "path": "documents"}
[3]   -> 7457 chars: <first 220 chars of the result>  <<target matter in result: 1037-00003 (FIRST TIME)>>
[4] CALL read {...}
...
```

Rules:
- `[n]` is the **event index** from the raw trace. Calls issued in parallel share one index.
- **Arguments:** truncated to 1,400 chars. For `write` and `edit`, `content` and `new_string` are cut to 900 chars and `old_string` to 150, so long drafts don't drown the log.
- **Results:** shown as their length plus the first 220 chars.
- **Text messages:** the user message is cut to 1,500 chars, assistant text to 400.
- **Target markers:** after each result, a marker lists the rubric entities that appear in it, with `(FIRST TIME)` on the first appearance. This lets annotators see at a glance when a needed entity first surfaced. It is hindsight information and is used only for the hindsight fields.
- **`runs_index.json`:** written alongside, with one row per run: task, trial, `all_pass`, `n_passed`, `n_criteria`, log path.

### 4.2 What to adapt

- **Entity regex.** Ours is `\b\d{4}-\d{5}\b`, applied to criterion titles. Use your benchmark's identifier. If your criteria don't name entities, leave the markers out: annotators then derive hindsight from the criterion reasoning, which is slower.
- **Field names** of your trace format.
- **From round 2 on,** the runs contain your own stage tools. Log `stage_start` and `stage_end` calls with their arguments. Shorten their results to:
  - for `stage_start`, the line "Stage started: …" plus any "Check the label: …" note;
  - for `stage_end`, the critic's verdict, flags and recommendation (about 900 chars).

  Never put target markers on these results, because the harness's own feedback lists entity IDs.
  - **Pitfall:** our shortened `stage_end` result cut off the appended "entities seen but not opened" list, so annotators missed it. Keep that list in the log, or tell annotators to open the raw trace for it.

### 4.3 Runs with no events

Occasionally an agent error leaves a trace with no tool calls, but a deliverable was still produced and graded. Either rebuild the calls from saved model requests if you keep them (we did this once), or record the run under a top-level `missing_runs` field of the task's annotation and exclude it from stage statistics.

---

## 5. Step 3: set up the catalog and the annotation rules

A **catalog** is one folder per round holding everything about that round's training runs:

```
analysis/<catalog-name>/
  BRIEF.md              annotation rules (sections 5.3–5.6)
  BRIEF_PARALLEL.md     extra rules for parallel batches (section 6.3)
  taxonomy.md           the vocabulary: stages, tags, hindsight values, error kinds (+ critic values for runs under the stage harness, i.e. round 2 on)
  changelog.md          one bullet per batch or merge: what was added and why
  make_logs.py          section 4
  logs/                 compact logs (regenerable; keep out of version control)
  runs_index.json
  annotations/<task>.json, <task>.md
  proposals/batch-<N>.md
  check.py              section 7
```

Round 1 starts with an **empty** `taxonomy.md`. Later rounds start from a copy of the previous round's merged taxonomy.

### 5.1 `taxonomy.md` layout

Markdown tables; the first column is the name, and `check.py` reads these tables.

```
## Stage groups               (optional analysis view; added at the first merge)
## Stages
| Stage | What the agent is doing | Typical tools | Added in | Example |
## Tags (agent-observable)
| Tag | Meaning | Added in |
## Hindsight values
| Value | Meaning |
## Error kinds (hindsight)
| Kind | Meaning | Added in |
## Critic values            (runs under the stage harness only)
| Value | Meaning |
## Issues                   (free list of doubts raised by annotators)
```

Examples are written `<task>_T<k> [a]-[b]`, where a and b are event indices.

### 5.2 Annotation output per task: JSON schema

`annotations/<task>.json`:

```json
{
  "task": "056",
  "context": "1–3 lines of task context (the ONLY place task content may appear in JSON)",
  "runs": [
    {
      "trial": 0,
      "all_pass": false,
      "n_passed": 0,
      "n_criteria": 2,
      "stages": [
        {
          "stage": "<stage name from taxonomy.md>",
          "start": 2,
          "end": 5,
          "tags": ["<tag>", "..."],
          "hindsight": "<hindsight value>",
          "note": "generic note, agent's view, no task content",
          "label_check": "followed | ignored | none"
        }
      ],
      "sequence": "Stage A → Stage B → … (consecutive repeats collapsed)",
      "failure_point": "generic sentence; empty for passing runs",
      "first_error": {
        "stage_no": 4,
        "stage": "<name of stage row stage_no>",
        "start": 20,
        "end": 31,
        "events": "[24]-[26] if narrower than the stage, else empty",
        "kind": "<error kind>",
        "why": "one sentence; may use task content but no entity IDs",
        "critic": "flagged-ignored | flagged-fixed-partly | not-flagged | no-review | review-endorsed",
        "critic_note": "(specific flag) … | (generic flag) … | short reason"
      },
      "other_errors": [ { "same shape as first_error": "…" } ]
    }
  ],
  "divergence": "mixed tasks: where passing and failing runs split; all-pass: what the passing runs had in common, and any different routes they took to succeed; all-fail: whether the runs failed the same way and at which stage",
  "missing_runs": [ { "trial": 0, "reason": "agent_error, no events" } ]
}
```

Notes on the fields:
- `label_check`, `critic` and `critic_note` exist only for runs under a stage harness (round 2 on).
- `first_error` is `null` for passing runs, and `other_errors` is `[]`.
- `stages` must cover every tool-call event exactly once, in order (section 5.3).

`annotations/<task>.md` presents the same content for humans. For each run:
- a table `| # | Stage | Events | Notes | Hindsight |`;
- the row of the first error gets " **⛔ first error**" appended to its Notes, and later errors get " **⚠ later error**";
- under the table:
  - `**First error:** stage <n> (<stage>) [a]-[b], <kind>: <why>`;
  - one `**Later error:** …` line per other error;
  - `**Critic:** …` for runs under the stage harness (round 2 on; round 1 runs the base agent, which has no critic);
  - `**Sequence:** …`.

After all runs come a short comparison and a `## Task context` section, the only place in the md where task content may appear.

### 5.3 Segmentation and stage rules

1. **Coverage.** Every tool-call event belongs to exactly one stage. Stages are contiguous ranges of event indices in time order and cover the whole run. A stage's `start` is its first tool-call event; its `end` is the event just before the next stage starts, so result events are covered. The last stage ends at the `finish` call ("Finish the run"), or at the last logged event if the run ended without `finish`; then it carries a `run ended: …` tag.
2. **A stage is the longest run of consecutive calls with one intent.** The same stage may occur several times in a run.
3. **Mixed parallel calls:** label the stage by the dominant intent and say so in the note. Our merge later fixed one convention: a parallel event that mixes a store-wide search with reads is labelled by the search.
4. **Reuse before adding.** Use an existing stage whenever it describes the intent. Add a new one only when every existing stage would misdescribe what the agent was doing.
5. **Never rename or delete** existing rows during annotation. Doubts go under "Issues".
6. **Names:** descriptive, benchmark-level, verb phrases. Good: "Screen candidate matters by reading documents". Bad: "Screen FDA matters" (task content), "S5" (a code), "Find the right matter" (hindsight).
7. **From round 2 on** (runs under the stage harness):
   - use the agent's declared stages as default boundaries: a stage runs from its `stage_start` to its `stage_end`, inclusive;
   - keep the declared name if it describes the work; otherwise relabel the span with the correct stage and start the note with `declared: <declared name>`;
   - split a declared span at a tool-call boundary if it clearly had two intents;
   - calls the protocol refused get tag `tool error`. A refused `stage_start` ("still open") stays in the open stage; a call refused with "No stage is open" goes into the next stage.

### 5.4 Tags, hindsight values, error kinds, critic values

- **Tags:** short labels for facts the agent could see at the time, e.g. `no matches`, `timed out`, `huge output`, `file not found`, `run ended: context overflow`. No hindsight.
- **Hindsight values:** one per stage, from the grader's point of view. Our list:
  - `target surfaced`: a needed entity appears in this stage's results;
  - `target opened`;
  - `target missed`;
  - `answer passes`, `answer over-inclusive`, …;
  - `none`.
- **Error kinds:** the category of a first or later error. Ours, after three rounds:
  - search-miss; partial-listing-as-corpus; surfaced-not-opened; listed-document-not-opened;
  - over-inclusion; under-inclusion; misstated-facts; missing-identifier; missing-detail;
  - context-overflow; over-narrow-filter; miscount; mistyped-path; incomplete-population; hedged-answer; answer-not-written.

  Start yours empty; let them emerge.
- **Critic values** (round 2 on), recorded on each error:

  | Value | Meaning |
  |---|---|
  | `flagged-ignored` | a review in reach named this problem and the agent moved on without fixing it |
  | `flagged-fixed-partly` | flagged; the agent acted, but the error remained |
  | `not-flagged` | the reviews in reach did not name it |
  | `no-review` | the run ended (e.g. overflow) before any review |
  | `review-endorsed` | the review pushed toward the wrong decision and the agent followed it |

  The `critic_note` starts with "(specific flag)" if the review named the entity, document or exact cause, and with "(generic flag)" for stock warnings.
- **`label_check`** (round 2 on, when the harness shows "Check the label" notes):
  - `followed`: the agent closed the stage and started the suggested one before doing that work;
  - `ignored`: it did that work under the declared label;
  - `none`: no note, or the note didn't apply.

### 5.5 First error (failing runs)

The **first error** is the earliest stage whose action or decision led to a failed criterion: where the agent's behaviour first went off course, not where the damage became visible.

| Situation | Where the first error goes |
|---|---|
| A needed entity never surfaced | the search that should have found it |
| Surfaced but never opened | the stage right after it surfaced, where the agent chose what to open and left it out |
| Opened but misjudged | the stage where the judgement became observable. With no visible reasoning, that is the writing stage whose text first shows it; name the reading stage in `why` |
| Context overflow | the stage with the oversized output |

Later independent errors go into `other_errors`.

### 5.6 What is written where, and why

| Field | May contain hindsight? | May contain task content? |
|---|---|---|
| stage name, tags, note | no | no |
| hindsight, failure_point, first_error, other_errors, divergence | yes | `why` may describe the task, but no entity IDs; the others must stay generic |
| context, md "Task context" section | yes | yes |

---

## 6. Step 4: annotate the runs (LLM annotators)

### 6.1 Order

Annotate in this order:
1. **Tasks with mixed outcomes** (some trials pass, some fail), sequentially, in batches of about 7 tasks. They build the vocabulary, and comparing passing and failing runs of the same task shows the decisive stage most clearly. Batch 1 starts from an empty taxonomy and creates the first stages; batch 2 extends it.
2. **Tasks where every run passed:** their `divergence` describes what the passing runs had in common, and any different routes they took to succeed. All passing does not mean all alike: in our round 1, one task's runs reached the answer by screening many agreements or by paging the full listing, and another's found the client three different ways. Alternative successful routes are useful evidence for the stage reference.
3. **Tasks where every run failed:** in parallel, about 6 tasks per batch, with the vocabulary frozen (section 6.3).
4. **One merge** (section 8).

From round 2 on, the vocabulary is mature, so all batches can run in parallel from the start: 10 batches of 8 tasks, then a merge.

### 6.2 Prompt for a sequential batch (template)

```
You are annotating agent runs (trajectories) into named stages. Read and follow exactly:
<catalog>/BRIEF.md
Then read taxonomy.md and changelog.md there <and study these finished annotations as style models: …>.
Use only files in that folder plus the raw traces named in the log headers. Do not open <paths of
validation/test material or older analyses>.

This is batch <N> of a sequential process; later batches extend the vocabulary you leave.
Your tasks (3 runs each, logs/<task>_T0..T2.txt): <list>. <All have mixed outcomes, so divergence matters most.>

Edit taxonomy.md directly (rows with "Added in" = "batch <N>" and examples) and append one bullet to
changelog.md listing what you added. Keep stage names descriptive and at a granularity that will
generalise to other tasks.

Before finishing, run check.py on your tasks; all checks must pass.

Reply under 400 words: the vocabulary you created or added, issues with existing rows, and per task a
one-line divergence summary.
```

### 6.3 Parallel batches: `BRIEF_PARALLEL.md`

```
Several batches run at the same time, so taxonomy.md, changelog.md and check.py are FROZEN.
- Use existing stages, tags, hindsight values and error kinds wherever they fit.
- If none fits, invent a descriptive name and use it prefixed with "NEW: ".
- Record every NEW name in proposals/batch-<N>.md:
  kind | name | definition | example <task>_T<k> [a]-[b] | why no existing name fits.
  Add an "Issues" list.
- check.py will reject NEW names; the only errors allowed are about your NEW names.
- Write only annotations/<your tasks>.* and proposals/batch-<N>.md.
- Use a private scratch folder (/tmp/<round>-batch-<N>/), never a shared one.
```

Each parallel prompt is the sequential template plus: "You are batch N. Tasks: …. Every run of these tasks failed." (or the outcome mix).

### 6.4 Practical advice

- **Give each batch a private scratch folder.** Our parallel agents once overwrote each other's generator script in a shared folder.
- **When a batch raises a consistency question mid-flight,** send the same rule to all running batches at once. Ours was how to code generic critic flags.
- **Budget about 95K–580K tokens and 6.5–22 minutes per batch of 8 tasks** (our rounds 2–4, measured from the annotation agents' usage reports; later rounds cost more because their logs include stage calls and reviews). These figures depend on our setup: log sizes, trace lengths of this benchmark, and the annotator model (Claude subagents). Measure one batch of your own before planning the rest.
- **Spot-check** at least one task per batch against the raw trace.
- **Parallel tool results can come back in a different order from the calls.** Annotators must attribute results by content, not by position.

---

## 7. Step 5: validate the annotations (`check.py`)

Write a checker and run it after every batch and after the merge. Ours (`analysis/stages-train-c30/check.py`, about 120 lines) checks, for every run:

1. **Outcome fields:** `all_pass`, `n_passed` and `n_criteria` match `runs_index.json`.
2. **Coverage:**
   - the first stage starts at the first tool call;
   - stages are contiguous (`next.start == prev.end + 1`), non-empty, and each contains at least one call;
   - every call is covered exactly once.
3. **Ending:** the last stage is "Finish the run" and ends at the `finish` call; or it carries a `run ended: …` tag and reaches the last event. No `run ended` tag appears on any other stage.
4. **Vocabulary:** every stage, tag, hindsight value and error kind exists in `taxonomy.md`.
5. **No leaks:**
   - no hindsight words in stage names, notes or tags;
   - no entity IDs or task words in names, notes, tags, `failure_point` or `divergence`;
   - no entity IDs in `why`.
6. **Sequence:** `sequence` equals the stage names with consecutive repeats collapsed.
7. **Errors:**
   - passing runs have no error fields;
   - failing runs have `first_error`;
   - each error's stage, start and end match the stage row `stage_no`;
   - `events` lies inside the stage.
8. **Markdown:** it has one table row per stage, and the markers and error lines match the JSON.

To adapt:
- `HINDSIGHT_WORDS` (ours: target, decoy, correct, wrong, rubric, criteri*, needed matter);
- the entity regex;
- `TASK_WORDS`: a list of topic words, party names and similar that must not appear. Build it from your task requests; ours is hand-made and benchmark-specific;
- handle `missing_runs` (skip them).

---

## 8. Step 6: merge the vocabulary

One agent (or you) merges after the parallel batches. The merge prompt should ask for:

1. **Collect every `NEW:` name** from the annotation JSON, not only from the proposals.
2. **Fold synonyms into one canonical name.** For example, "under-inclusion", "opened-but-excluded", "misjudged-exclusion" and "over-exclusion" became **under-inclusion**.
3. **Acceptance rule:** keep a name if it is used in ≥2 runs or marks a first error. Otherwise map it to the closest existing name.
4. **Add the accepted names to `taxonomy.md`** with "Added in = merge (batch …)" and an example, then strip `NEW:` everywhere (JSON and md).
5. **Harmonise conventions the batches disagreed on,** state each rule in `taxonomy.md`, and apply it to every task. Our conventions:
   - judgement errors sit on the writing stage;
   - hindsight on whole-store listings follows the log markers;
   - mixed parallel events are labelled by the search;
   - searches for a kind of document get their own stage.
6. **Fix definitions the batches flagged.**
7. **Re-run `check.py` on all tasks** until ALL CHECKS PASSED.
8. **Append a "merge" bullet to `changelog.md`.**
9. **Optional:** cluster stage-to-stage transitions into **stage groups**, as an analysis view only. Do not use groups as declarable stages (we tried; it was the wrong level).

Also write `failure_patterns.md` for humans: per stage, its error kinds with counts, 2–3 examples, and what passing runs did differently. The harness does not read it; section 9 generates the harness's version.

---

## 9. Step 7: generate the stage reference (`build_stage_reference.py`)

Everything the harness tells the agent about stages is **generated** by one script from the catalogs. Never write it by hand: hand-writing is how our own knowledge leaked in during round 1.

### 9.1 Inputs and command

```bash
export CAO_API_KEY=<key for your second-LLM endpoint>      # read from a file; never print it
python3 scripts/stage/build_stage_reference.py \
  --catalog analysis/stages-train analysis/stages-train-c29 analysis/stages-train-c30 \
  --taxonomy analysis/stages-train-c30/taxonomy.md \
  --harness harness_stage_r3
```

- `--catalog`: one folder per round, **oldest first**. The last one is the latest round.
- `--taxonomy`: the newest merged taxonomy. Stage definitions come from its "Stages" table.
- `--harness`: the harness folder to write into.

Environment variables:
- `STAGE_BUILD_MODEL`: default `claude-sonnet-5-5`;
- `STAGE_BUILD_URL`: an OpenAI-compatible `/v1/chat/completions` endpoint.

### 9.2 Algorithm

For each stage in the taxonomy (except "Finish the run", which is not declarable):

1. **Collect**, across all catalogs:
   - every error (first and later) placed at this stage: its kind, the round it came from, and its `why`;
   - notes of this stage from **passing** runs (with the `declared: …` prefix stripped);
   - tools used in this stage in passing runs (from the logs, via the stage's event range);
   - relabels from catalogs of runs under the stage harness (round 2 on; only those runs declare stages): how often a span *declared* as this stage was annotated as another stage.
2. **Classify the error kinds** with counts per round:
   - **active** if the kind occurs in ≥ `MIN_RUNS` (2) runs of the **latest** round. There is no cap. If more than `SPLIT_WARN` (5) kinds are active, print `SPLIT HINT` (section 12.4);
   - **policy** if the kind was common in an earlier round and has fallen to ≤ `POLICY_RATIO` (25%) of its peak, or ≤1 run, in the latest round. "Common" means ≥ `MIN_RUNS` in a single earlier round **or** ≥ `MIN_RUNS` pooled over all earlier rounds. Without the pooled condition, a kind seen once in each of two rounds is silently dropped. The guidance worked, so the lesson becomes a positive rule;
   - **regression** if it had already fallen like that in an intermediate round and is active again now. Print `REGRESSION` and keep it active;
   - **dropped** if it was never common.
3. **One LLM call per stage** (system and user prompt below) writes:
   - `purpose`;
   - `when_to_use`;
   - one generic sentence per active kind, from that stage's latest-round `why`s;
   - one imperative rule per policy kind;
   - `passing_runs`;
   - up to 2 `examples` from the passing-run notes.
4. **Stage confusion:** list up to 2 stages that this stage was declared for while the work was really another stage, if ≥ `MIN_RELABELS` (5) relabels.
5. **Run facts (optional):** a *run fact* is a deterministic check computed from the run's own trace that bears directly on one error kind. For example, "items that appeared in search results but were never opened" targets an error kind such as "found but not opened". If you define run facts for your benchmark, the script switches each one on only at the stages where its error kind is active in the latest round, and the critic and the review receive it there. Define a run fact only for an error kind your catalogs show is common, and only if it can be computed reliably from the trace. Our one run fact is described in section 10.6.

Builder system prompt:

```
You write guidance for one stage of an AI agent's work, from annotated training runs of that agent.
Use ONLY the material given. Write generically: no matter numbers, client or party names, legal topics
(claim, deal, document or practice types specific to a task) or request wording from any task; describe
behaviour that would apply to any request. Do not mention other stages' failures. Reply with JSON only.
```

Replace "matter numbers … legal topics" with your benchmark's equivalents. Our first build let "damages counterclaims" slip into a rule; the stricter wording above fixed it. Always read the generated rules for leaks before using them.

Builder user prompt: the stage name and definition; "CURRENT ERRORS (latest round)" grouped by kind with up to 25 `why`s each; "ERRORS THAT WERE COMMON HERE BEFORE AND ARE NOW RARE"; "WHAT PASSING RUNS DID IN THIS STAGE" (up to 30 notes); and the required JSON keys:

| Key | Content |
|---|---|
| `purpose` | one sentence, no failure information |
| `when_to_use` | one sentence, or "" |
| `failure_patterns` | one sentence per current kind, in order |
| `policy` | one imperative rule per now-rare kind, in order |
| `passing_runs` | what passing runs did differently about the *current* failures, or "" |
| `examples` | up to 2 short generic examples |

### 9.3 Output: `middleware/stage_reference.json`

The file has two parts: the per-stage feedback, which is the method and is always present, and optional run-fact blocks, which are benchmark-specific.

**Per-stage feedback (always present):**

```json
{
  "_source": "Generated by … from <catalogs> (training runs only). Active = … Policy = …",
  "stages": {
    "<stage name>": {
      "purpose": "…",
      "when_to_use": "…",
      "typical_tools": "glob, bash",
      "examples_from_successful_runs": ["…", "…"],
      "expected_activity": "<taxonomy definition>",
      "policy": ["keep doing …"],
      "policy_kinds": {"search-miss": 37},
      "failure_patterns": ["…"],
      "failure_kinds": {"over-inclusion": 41},
      "passing_runs": "…",
      "often_confused_with": {"<other stage>": 144}
    }
  }
}
```

If a stage has no active failures, `failure_patterns` is exactly `["No recurring failures (seen in two or more runs) were recorded at this stage in the latest training round."]` and `passing_runs` is `""`.

**Optional run-fact blocks (benchmark-specific).** A run fact (defined in section 9.2, step 5) needs two pieces of code you write yourself: tracking code in the middleware, and display code in `stage_end`. It also needs one config block in this file. That block holds a few values you set by hand, plus the list of stages where the fact is shown, which the script fills from the error statistics. Our only run fact is called `surfaced_not_opened`. It is **not** part of the method; it is shown here as the example to copy:

```json
  "surfaced_not_opened": {
    "enabled": true,
    "entity": "matter",
    "entity_regex": "\\b\\d{4}-\\d{5}\\b",
    "max_entities_for_hit_list": 150,
    "show_at_stages": ["Screen candidate matters by reading documents", "…"],
    "_why": "…"
  }
```

What each field is, and who writes it:

| Field | Meaning | Written by |
|---|---|---|
| `entity` | what the tracked items are called in messages ("matter") | you, once |
| `entity_regex` | pattern that recognises an item in text (our matter numbers) | you, once |
| `max_entities_for_hit_list` | a search result showing more items than this is a full listing, not hits, so its items don't count as "seen" | you, once |
| `show_at_stages` | stages where the fact is shown: those whose active error kinds include the kind it targets (`surfaced-not-opened`) | build script, every build |
| `enabled` | on if `show_at_stages` is non-empty and `entity_regex` is set | build script |

The script reads your hand-set values from the existing file before rewriting it, and keeps them. Our code supports exactly this one run fact, under this name. If your benchmark needs a different run fact, you need:
- a new block like this one, with your own name;
- the matching tracking code in the middleware and display code in `stage_end` (section 10.6 shows ours);
- a line in the build script that fills its `show_at_stages` from the error kind it targets.

If you don't need a run fact, leave the block out; the harness then simply doesn't show one.

**General shape of any run-fact block.** Only three things are common to every run fact:

| Field | Meaning | Written by |
|---|---|---|
| the error kind it targets (ours is implicit in the code: `surfaced-not-opened`) | decides where the fact is shown | you, once |
| `show_at_stages` | stages where that error kind is active in the latest round | build script, every build |
| `enabled` | on if `show_at_stages` is non-empty and the fact's own settings are complete | build script |

Everything else in the block is **specific to that fact**: whatever its tracking code needs, possibly nothing. Our `entity`, `entity_regex` and `max_entities_for_hit_list` exist only because our fact tracks matter numbers in search results. Other domains would need different settings, for example:
- **Coding agent, fact "files edited but tests never run":** a pattern for test commands.
- **Web agent, fact "pages opened but never read past the first screen":** a length or scroll threshold.

When you write your own, give it its own name, record the error kind it targets explicitly, and keep its settings to what its code needs.

The script also rewrites two other files:
- the **"## Stage protocol" list** in the harness system prompt (section 10.7);
- the **`enum` of the `stage` argument** in `tool_descriptions/stage_start.tool.yaml`: every stage name plus `new`.

### 9.4 Typical tools: names only, never shares

**What to do.** For each stage, `typical_tools` lists the names of the tools that **passing** training runs used in that stage. These are the 4 most frequent, counted from the calls inside the stage's event ranges. They appear in the prompt as "Typical tools: glob, bash." Show the names only. Never show how often each tool was used, as a percentage or a count.

**Why not shares:**
- **No signal:** the share of each tool in a stage is usually about the same in passing and failing runs, so it says nothing about what makes a run succeed.
- **Can push toward bad tools:** a high share can steer the agent toward a tool whose limitations cause failures at that stage.
- **Reads as a quota:** a number like "read 99%" reads as an instruction and discourages trying other tools or approaches.

What successful runs did differently belongs in the examples (`examples_from_successful_runs`) and the passing-run note (`passing_runs`), not in tool statistics.

**Our evidence.** In the store-wide search stages:

| Runs | bash | grep | glob |
|---|---|---|---|
| Passing | 49% | 25% | 20% |
| Failing | 45% | 25% | 23% |

In our benchmark, `grep` (which cannot read `.docx` text) and `glob` (which silently stops at 100 files) were behind the most common search failures. Showing their high shares would have encouraged exactly those tools.
---

## 10. Step 8: build the harness components

Start from a **copy** of your base harness. Add the files below; change nothing else (rule 5). Our reference implementation is `harness_stage_r3/`; this section describes it exactly. Line counts are given to show the size.

| File | What it is |
|---|---|
| `tools/stage.py` (~300 lines) | `stage_start`, `stage_end`, critic call, review text, label classifier |
| `tools/_stage_common.py` (~110) | per-run state, reference loader, `chat()` to the second LLM |
| `middleware/stage_common.py` (~110) | twin copy of the above (section 10.9) |
| `middleware/stage_guard.py` (~250) | enforcement, call recording, run-fact tracking (ours: surfaced-not-opened), fit notes, forced continue |
| `middleware/stage_reference.json` | generated (section 9) |
| `tool_descriptions/stage_start.tool.yaml`, `stage_end.tool.yaml` | tool schemas |
| `agent.yaml` | register the 2 tools and the middleware |
| `systemprompt.md` | add the "## Stage protocol" section |

### 10.1 Per-run state

Keep the state in the framework's **per-run storage** (NexAU: `agent_state.get_global_value / set_global_value`, key `harvey_stage_state_v1`). **Never use module-level globals**: runs execute concurrently in one process. Guard reads and writes with a lock if your hooks run in threads.

```python
state = {
  "open": None | {"stage", "label", "goal", "attempt", "calls": [{"tool", "args", "result"}]},
  "history": [{"stage", "label", "goal", "attempt", "goal_reached", "n_calls", "summary",
               "effective_stage", "critic"}],
  "request": "<first user message>",
  "blocked_ids": ["<tool_call_id refused because its turn mixed stage and work calls>"],
  # run-fact state, one entry per run fact (ours, surfaced_not_opened):
  "surfaced": {"<entity>": "<stage label where it first appeared>"},
  "opened": ["<entity>", ...],
  "mismatches": [{"stage", "tool", "args"}],
  "text_replies": 0
}
```

`label` is the stage name, or `new: <name>` for agent-defined stages. `attempt` counts how many times this label has been opened; a reopened stage has attempt ≥ 2.

### 10.2 Tool schemas

`tool_descriptions/stage_start.tool.yaml`:

```yaml
type: tool
name: stage_start
description: >-
  Declare the stage you are entering and its goal. Every other tool call must
  happen inside an open stage. Call this alone in its own turn. To reopen a
  stage after its review, call it again with the same stage and a sharper
  goal. Use stage "new" with new_stage_name when none of the listed stages
  describes what you are about to do.
input_schema:
  type: object
  properties:
    stage:
      type: string
      enum: [<generated stage names>, new]
      description: The stage you are entering.
    goal:
      type: string
      description: What this stage must achieve, concretely enough that you can later say whether it was reached.
    new_stage_name:
      type: string
      description: Only with stage "new"; a short descriptive name for the stage you are defining.
  required: [stage, goal]
disable_parallel: true
binding: tools.stage:stage_start
```

`stage_end.tool.yaml`: properties `goal_reached` (boolean: "Whether the stage goal was fully reached") and `summary` (string: "What you did and found in this stage: searches run and their outcome, candidates found, which were opened or excluded and why, open questions"); both required; `disable_parallel: true`; binding `tools.stage:stage_end`.

The description tells the agent to call it alone, and that an independent reviewer then checks the stage's tool calls and lists that stage's common failures.

### 10.3 `stage_start(stage, goal, new_stage_name=None)`

1. If a stage is already open, return an error. The middleware normally refuses this first; keep it as a second defence.
2. Validate `stage`: one of the reference's stage names, or `new` with a non-empty `new_stage_name`. Require a non-empty `goal`.
3. Open the stage: set `label`, set `attempt` = 1 + the number of earlier history entries with the same label, and start with an empty call list.
4. Return text in this order:
   1. `Stage started: <label> (attempt N: you are reopening this stage).`
   2. `Purpose: <purpose>` and `Your goal: <goal>`.
   3. For each stage in `often_confused_with`: `Check the label: runs often declared this stage while doing other work. If you are going to <that stage's purpose> that is the stage "<X>": close this stage and start that one.`
   4. If the stage has a policy: `Policy for this stage (lessons that removed past failures; keep following them):` followed by the rules.
   5. `Watch out: failures seen at this stage in past runs:` followed by the failure patterns.
   6. `What successful runs did here: <passing_runs>`, if not empty.
   7. `Every tool call from now on belongs to this stage. When you believe the goal is reached (or you cannot get further), call stage_end alone in its own turn.`

The failures are shown at the start as well as at the end, because a run can die inside a stage, for example from context overflow, before ever seeing the end review.

### 10.4 `stage_end(goal_reached, summary)`

1. If no stage is open, return an error.
2. **Effective stage** (label safety net). If the stage has calls and isn't `new`, ask the fit model which listed stage the calls belong to:
   - system prompt: "You classify a stretch of an agent's tool calls into one stage from a fixed list. Judge only from what the calls do. Reply with JSON only: {"stage": "<exact name>"}";
   - user prompt: the stage menu (name and purpose) plus up to 40 calls (tool and arguments, 300 chars each).

   If the answer differs from the declared stage, that is the *effective* stage, and its failures and policy are added to the critic's checklist and to the review. In our runs a note asking the agent to relabel was ignored 392 times out of 401, so applying the right feedback anyway works better than asking.
3. **Run facts:** computed only if the declared or effective stage is one where that run fact is switched on (section 9.2, step 5; our example in section 10.6).
4. **Critic call** (section 10.5).
5. **Append to history:** the summary (600 chars), the effective stage and the critic result. Close the stage.
6. **Return the review text**, in this order:
   1. `[Stage review: <label>, attempt N]`;
   2. `You reported: goal reached = yes|no.`;
   3. `Independent reviewer: goal reached = yes|partly|no.`, then `Reviewer flags: …`, `Reviewer concerns: …`, `Reviewer recommendation: …` (or "unavailable" if the call failed);
   4. if there is an effective stage: `Label: these calls looked like '<X>' work, so they were also reviewed against that stage's failures. Declare '<X>' for this kind of work.`;
   5. if the critic proposed a new stage: `Reviewer suggests a new step: '<name>' (<goal>). You can start it with stage_start(stage="new", new_stage_name="<name>", goal=...).` Otherwise, if attempt ≥ 3: `This stage has been opened N times. If repeating it is not getting further, try a different approach; you may define a new stage …`;
   6. each run fact switched on here, as one line. Ours: `<Entity>s that appeared in your search results but none of whose documents you have opened or listed: …` (up to 40);
   7. `Common failures at this stage in past runs:` followed by the patterns, plus the effective stage's patterns if any;
   8. `What successful runs did: …`, if not empty;
   9. the instruction:
      - if `goal_reached` is true: *"Reconsider before moving on. If the goal was not fully reached, or any failure above applies, reopen this stage now: call stage_start with stage="<same>" and a goal that says what you will fix. Otherwise call stage_start for the next stage you need."*
      - if false: *"You said the goal was not reached. Reopen this stage … with a sharper goal that follows the recommendation above, or start a different stage if that is what is needed."*

Reopening is advised, never forced: the critic's verdict ("partly" in about 80% of reviews) does not separate passing from failing runs well enough to force on.

### 10.5 The critic

- **Model:** different from the agent and from the grader (ours: `claude-sonnet-5-5`), with `max_tokens` 900 and a timeout of 180 s.
- **On failure:** if the call fails, the review says "unavailable" and still lists the patterns.

**System prompt** (replace the domain sentence with yours):

```
You review one stage of an AI agent's work on a <domain> task. The agent <one line on what the agent
does>. You do NOT know the right answer; judge only from the request, the stage goal and the stage's
tool calls and results shown. Use the known failure patterns of this stage as your checklist, but list
a failure in applicable_failures ONLY if you can point to the specific call, result, <entity> or
document in this stage's log that shows it; name that evidence. Do not repeat a pattern as a generic
warning. Your recommendation must not itself lead into a known failure pattern of the stage it points
to (those patterns are listed for every stage). Do not invent facts.
Reply with JSON only: {"goal_reached": "yes"|"partly"|"no", "applicable_failures": [short strings,
each naming its evidence], "concerns": "<=120 words", "recommendation": "<=80 words, concrete next
actions", "new_stage": {"name": "...", "goal": "..."} or null}.
```

**User message**, in this order:
1. `REQUEST`: the first user message, up to 6,000 chars;
2. `STAGE: <label> (attempt N)`, `STAGE PURPOSE`, `AGENT'S GOAL`;
3. `AGENT'S SELF-ASSESSMENT`: goal_reached plus the summary, up to 3,000 chars;
4. `KNOWN FAILURE PATTERNS AT THIS STAGE`, plus the effective stage's patterns if any;
5. `STAGE POLICY (rules that removed past failures; check they still hold)`, if any;
6. only when attempt ≥ 3: `THE AGENT HAS OPENED THIS STAGE N TIMES (<earlier goals>). Recommend a different approach from the earlier attempts. If a step that is not among the listed stages would help, propose it as a new stage in "new_stage" with a short name and goal.`;
7. `KNOWN FAILURE PATTERNS OF OTHER STAGES (your recommendation must not lead into these)`: every other stage that has active failures;
8. each run fact switched on at this stage (section 9.2, step 5), as one block. Ours: `<ENTITY>S THAT APPEARED IN SEARCH RESULTS SO FAR BUT HAVE NO DOCUMENT OPENED OR FOLDER LISTED: …` (up to 60);
9. `STAGE TOOL CALLS (n)`: each as `- tool args(400 chars)\n  -> result(700 chars)`, keeping only the last 40,000 chars if longer.

Why each part is there:
- **"Cite the evidence":** in round 2, half of the critic's flags were generic stock warnings, and the agent ignored them. Specific flags rose 58 → 75 after this rule.
- **"Don't lead into other stages' failures":** the critic once recommended uncapped store-wide scans that then overflowed the context.
- **The stuck clause:** it is the only exploration mechanism. The agent never used `new` on its own in 720 runs.

### 10.6 Middleware: `stage_guard.py`

**Enforcement** happens in `wrap_tool_call`, which runs before the tool and can return an error instead of calling it.

| Situation | Action (return `{"status": "error", "error": "[Stage protocol] …"}` without running the tool) |
|---|---|
| `stage_start` while a stage is open | "Stage '<label>' is still open. Call stage_end first." |
| `stage_end` with no open stage | "No stage is open. Call stage_start first." |
| `finish` (your stop tool) while a stage is open | "Stage '<label>' is still open. Call stage_end before finish." |
| any work tool (`bash`, `read`, `write`, `edit`, `glob`, `grep`; list *your* tools) with no open stage | "No stage is open. Call stage_start (alone in its turn) with the stage you are in and its goal, then repeat this call." |
| a turn that mixes `stage_start` or `stage_end` with other calls | every call of that turn is refused: "stage_start and stage_end must be called alone in their own turn. None of the calls in this turn were run …" |

The mixed-turn rule needs two hooks:
- in `after_model`, read the parsed tool calls of the turn; if a stage tool appears with any other call, store all their call IDs in `blocked_ids`;
- in `wrap_tool_call`, refuse any call whose ID is in `blocked_ids`, and remove it from the list.

Returning `status: error` from a refused `finish` keeps the run going, because NexAU stops only when the stop tool succeeds. Check how *your* framework treats a stop tool that returns an error.

**Text-only replies:** in `after_model`, if the model replied without any tool call (which would end the run in most frameworks), add a framework message and return `force_continue=True`. The message: *"[Stage protocol] You replied without calling a tool, which does not end the task. <Stage 'X' is still open.> Continue through the stages; write the deliverable …, close the open stage with stage_end, then call finish."*

**No loop breaker,** by design. If the agent keeps getting refused, you want to see it. In practice refusals were rare: 0.4 per run.

**Recording** (after a work tool has run):
- append `{tool, args (400 chars), result (700 chars)}` to the open stage's calls; the critic reads these;
- **update each enabled run fact** (section 9.3), if you have any. A run fact's tracking code reads the call's arguments and result and keeps whatever it needs in the per-run state. At its `show_at_stages`, the fact's current value is added to the review and to the critic's input. With no run facts, skip this step.

  *Our example (dataset-specific):* the `surfaced_not_opened` fact keeps two sets of matter numbers:
  - *opened*: numbers found in the arguments of reading or listing tools;
  - *surfaced*: numbers found in the results of search tools (grep, glob, bash), but only when a result shows between 1 and `max_entities_for_hit_list` (150) distinct numbers. A result with more is a full listing, not a hit list.

  The fact's value is the surfaced numbers that were never opened.

**Stage-fit notes** (soft, never blocking):
- for each `bash`, `grep` or `glob` call inside a non-`new` stage, ask the fit model (ours: `claude-haiku-5-5`, `max_tokens` 120) whether the call fits the stage's `expected_activity`: system prompt "Classify one tool call … Reply with JSON only: {"fits": true|false, "activity": "<=12 words"}";
- if it doesn't fit, append to the tool result: *"[Stage protocol] Stage check: this call looks like <activity>, which does not match the open stage '<label>' (<expected activity>). If you have moved on to different work, call stage_end and start the matching stage."*;
- a `write` or `edit` to the output directory outside the writing stages gets a similar note, by rule;
- log every mismatch to `mismatches`.

We decided **against** hard per-stage tool limits:
- a shell tool can do anything;
- the few passing runs are a thin basis for limits;
- the agent might pick a stage label just to unlock a tool;
- without a loop breaker, a blocked tool the agent needs could stall a run.

**Request capture:** in `before_model`, on the first call, store the first user message's text as `state["request"]`.

**Robustness:** wrap every hook in try/except and fall back to "no change" or "run the call". A middleware crash must never end a run.

### 10.7 System prompt section

Insert a "## Stage protocol" section after your tool conventions. The build script regenerates the stage list in it:

```
## Stage protocol

Work in declared stages. A stage is a stretch of work with one purpose and a
concrete goal. The stages seen in this kind of task, with when to use them,
the tools typically used in them, and examples of what successful runs did in
them:

1. **<Stage name>**: <purpose>
   - When: <when_to_use>
   - Typical tools: <typical_tools>.
   - Example: <example 1>
   - Example: <example 2>
   - Not for: <purpose of a confused stage> That is **<Other stage>** (runs often mislabelled it as this stage).
2. …

These are a menu, not a fixed sequence: use them in any order, repeat them,
and skip the ones you do not need. If none of them describes what you are
about to do, define your own with `stage="new"` and a `new_stage_name`.

Rules (enforced; a call that breaks one is refused without running):

- Call `stage_start` with the stage and a concrete goal before any other
  tool call. Every <list your work tools> call must happen inside an open stage.
- Only one stage is open at a time. Close it with `stage_end`
  (`goal_reached` true or false, and a summary of what you did and found)
  before starting another stage or calling `finish`.
- Call `stage_start` and `stage_end` alone, each in its own turn, never
  together with other calls.
- `stage_start` lists the failures seen at that stage in past runs and what
  successful runs did there; keep them in mind while you work.
- `stage_end` returns a review: an independent reviewer's assessment of the
  stage and the failures common at that stage in past runs. Read it and
  decide: if the goal was not reached or a listed failure applies, reopen the
  same stage with `stage_start` and a goal that says what you will fix;
  otherwise start the next stage you need.
- Some results carry a stage note when a call looks like work belonging to a
  different stage. If you have moved on, close the stage and start the
  matching one.
- Replying without a tool call does not end the task; only `finish` does.
```

The text from "These are a menu" onwards is written once by hand; the build script replaces only the list above it.

### 10.8 Registration

In NexAU's `agent.yaml`:

```yaml
tools:
  - … existing tools …
  - name: stage_start
    yaml_path: ./tool_descriptions/stage_start.tool.yaml
  - name: stage_end
    yaml_path: ./tool_descriptions/stage_end.tool.yaml
middlewares:
  - import: middleware.stage_guard:StageGuardMiddleware
```

Leave the stop tool, iteration limit, model settings and all other fields unchanged.

### 10.9 Framework-specific pitfalls (NexAU / our runner)

- **Twin helper modules.** Our harness conformance check attributes every local module imported by a tool to "tool implementations", and every module imported by middleware to "middleware". A single shared helper file therefore failed with "runtime-attached … component is not declared". The fix: two copies of the helpers, `tools/_stage_common.py` and `middleware/stage_common.py`, identical except for the path to the reference file. If your framework has no such check, keep one copy.
- **Network calls from harness code.** The critic and the fit model are called over HTTP from the harness. Our candidate checker bans network imports, but it runs only in automated evolution, not in evaluation-only runs. If your setup forbids network access from harness code, move the critic into the adapter or runner.
- **The runner freezes a copy of the harness at launch.** So editing the harness folder during a run doesn't affect that run. Verify this before you edit a harness that is being evaluated.
- **The key** for the second LLM is read from an environment variable that the launch script exports from a key file. Never print or log it.

### 10.10 Porting to another framework

You need the equivalents of:

| Need | NexAU hook | Elsewhere |
|---|---|---|
| refuse a tool call before it runs | `wrap_tool_call` returning an error instead of calling `call_next` | a tool-dispatch wrapper or proxy around each tool |
| see all calls of a turn | `after_model` with `parsed_response.tool_calls` | inspect the assistant message before executing tools |
| keep the loop running after a text-only reply | `after_model` returning `force_continue=True` plus a message | inject a user or system message and continue |
| per-run state | agent-state global storage | any per-run object passed to tools |
| request capture | `before_model` | read the first user message at run start |

If your framework runs parallel tool calls in threads, keep `stage_start`, `stage_end` and the writing tools serial (`disable_parallel: true` in NexAU).

---

## 11. Step 9: test and run

### 11.1 Offline unit test (no agent)

Write a script that builds a fake agent state, imports the middleware and the tools, and drives them directly. Ours is `scripts/stage/stage_unit.py`. It must show:

1. a work tool with no open stage is refused;
2. `stage_start` returns the purpose, policy and watch-out text;
3. a second `stage_start` is refused while a stage is open;
4. `finish` is refused while a stage is open;
5. each run fact updates as expected (ours: a grep result with three entity IDs marks them surfaced);
6. a write to the output directory outside a writing stage gets a stage note;
7. a turn with `stage_end` plus `read` refuses both;
8. `stage_end` returns a critic review (real call to the second LLM);
9. each run fact appears only at its `show_at_stages`;
10. a text-only reply returns `force_continue=True`;
11. `stage="new"` without a name is refused, and with a name it opens `new: <name>`;
12. the policy is shown at start;
13. a stage whose calls clearly belong to another stage (ours: a "read in depth" stage whose calls screen five candidates) gets the line `Label: these calls looked like '<other stage>' …`;
14. opening a stage for the 3rd time makes the critic suggest a new step;

Use neutral, made-up example data in the test, never content from a validation or test task.

### 11.2 Smoke run

Run 3 training tasks × 1 trial. Check from the traces:
- stages open and close;
- the critic answers;
- there are no unexpected refusals;
- the run finishes.

Write a per-run summary script (ours: `scripts/stage/stage_runs.py`) that prints the judge score, termination reason, tool counts, number of stages, reopens, refusals, fit notes and the stage sequence.

### 11.3 Full training run

Run all training tasks × 3 trials. Compare with the previous round on the **same task and trial pairs**:
- all-pass rate and criterion pass rate;
- the distribution of tasks by passes out of 3 (0, 1, 2, 3);
- a **paired bootstrap over tasks** for the all-pass difference: take each task's mean all-pass per harness, difference them, resample the 80 task differences with replacement 5,000 times, and report the 2.5% and 97.5% quantiles.

Also compute run-level stage statistics (ours: `scripts/stage/stage_stats.py`):
- calls per run, stages per run and reopens per run;
- context overflows;
- the critic verdict distribution;
- how often the agent moved on despite a "no" or "partly" verdict;
- how often the agent itself said "not reached";
- stage usage in passing vs failing runs.

---

## 12. Step 10: the round loop

After each training run of a new harness:

### 12.1 Annotate the new runs (new catalog)

- Build compact logs for the new runs (section 4.2).
- Copy the latest merged `taxonomy.md`, and copy `check.py` with the path updated.
- Write a round brief that says:
  - follow the earlier briefs;
  - use declared stages as default boundaries and relabel when wrong (section 5.3, rule 7);
  - add `critic`, `critic_note` and `label_check` (section 5.4);
  - "never open validation or test material".
- Run 10 parallel batches with frozen vocabulary and `NEW:` proposals, then merge (sections 6 and 8). In our rounds 2 and 3, no batch proposed a new stage. New names were only an error kind (`missing-detail`) and a critic value (`review-endorsed`).

### 12.2 Analyse

Write a round report covering:
1. **Outcome** vs the previous rounds.
2. **First-error kinds across rounds:** what the last change fixed, and where failures moved.
3. **Most common first error by kind and stage.**
4. **Split stage in mixed tasks:** where passing and failing runs of the same task diverge.
5. **Critic outcome table:** flagged-ignored, flagged-fixed-partly, not-flagged, no-review, review-endorsed; plus specific vs generic flags.
6. **Mislabelling:** declared vs annotated stage counts, and `label_check` followed vs ignored.
7. **New stages,** if any.

### 12.3 Update the learned stage content (no code changes)

The mechanism (sections 9 and 10) is fixed. A round changes only what was learned about the stages from the new catalog:

1. **Stage list:** promote agent-defined stages, or split or merge stages, only when section 12.4's criteria are met. Update `taxonomy.md`.
2. **Stage reference:** rerun `build_stage_reference.py` with **all** catalogs (oldest first). It recomputes, per stage:
   - the active failures and the policy;
   - examples and typical tools;
   - "Not for" confusion notes;
   - where each run fact is shown.
3. **Read the generated text** for leaks of task content or hindsight words (section 9.2), and check the `REGRESSION` and `SPLIT HINT` lines.
4. Copy the harness folder, put in the new reference, system-prompt stage list and `stage_start` enum, and run the unit test (section 11.1).
5. Run the training split again.

For each change to the stage list, record the evidence (counts from the report) in the design log.

Do **not** change the stage tools, the guard, the critic's prompt, the review format or the build script between rounds. A change to any of them is a different mechanism, not a round. If a round's report suggests one, write it down as a proposal and test it as a separate experiment against the same baseline.

**How we got to this mechanism (history, not a recipe).** We built the mechanism over our first rounds, so our rounds 2–4 also changed code. Each of those changes is already part of sections 9 and 10, so you implement them from the start:

| Our evidence | Mechanism part it added |
|---|---|
| half of the critic's flags were generic | critic must cite evidence (10.5) |
| the critic recommended scans that overflowed | critic receives every stage's failures (10.5) |
| 21% of declared spans were mislabelled | confusion notes, effective-stage review (9.2, 10.4) |
| warnings that worked could be dropped by top-k | stage policy (9.2) |
| no exploration | critic proposes a new stage when a stage is stuck (10.5) |

### 12.4 Splitting and merging stages

**When to split a stage.** A stage with many recurring error kinds (`SPLIT HINT`) may be too complex. Split it only if both of these hold:
- its errors belong to **different sub-activities**. Watch out for annotation conventions that pile kinds onto one stage: we file every judgement error at "Write the response";
- passing runs in the training data show a **distinct sub-step** inside that stage.

We tested this for "Decide which candidates qualify" before "Write the response". Within mixed tasks, the last stage before writing stated include/exclude decisions in 7 of 26 passing vs 10 of 22 failing runs. That doesn't support the split, so it stays out until the data supports it. Re-check the criterion after each round.

**When to merge stages.** Stages confused very often (for us: "List files in the document store" vs "List matter folders", 144 times) are candidates for merging or renaming. Merging is also a stage-level change; justify it the same way.

**Promoting agent-defined (`new`) stages.** The agent may define its own stages (`stage="new"`, `new_stage_name`). In our runs this only started once the critic was asked to propose a new approach when a stage was stuck (section 10.5). The names are free text and rarely repeat exactly, so never count them by name. The procedure:
1. **Annotation:** for every agent-defined stage, the annotator checks whether an existing stage describes its calls. If one does, relabel the span to it, with the note `declared: new: <name>`. If none does, keep it as a `NEW:` stage, described by what its calls do.
2. **Merge:** group the remaining `NEW:` stages by what their calls do, not by their names. For example, "Per-matter proof check" and "Verify proof documents for each matter" are one group.
3. **Promote a group into the stage list only if all three hold:**
   - it occurs in **at least 2 different runs** (repeats inside one run don't count);
   - **at least one** of those runs all-passed;
   - **no existing stage** describes it.
4. **Name it generically,** at benchmark level, with no entity IDs or task words, and add it to `taxonomy.md` with a definition and an example.
5. **Rebuild the reference** (section 9). The new stage appears in the system prompt and in the `stage_start` enum; its failure patterns come from later rounds.

If nothing reaches the bar, report the candidates with their counts instead of lowering it.


### 12.5 Expect diminishing returns

Our training all-pass rates went C0 11.3% → r1 26.7% → r2 30.8%: r1 vs C0 was significant, and r2 vs r1 was within noise. Reminders fixed the "information" failures (search, listing, overflow). What remained were judgement failures at Screen and Write, where the agent got specific feedback and ignored it. Past that point, more information doesn't help. We then tried a **steering gate** (r4): at stages where specific flags were often ignored, the agent could not start another stage until it reopened the stage or gave a reason for each flag. It fired in 227 of 240 runs, but r4's all-pass was 26.7%, below r2, so we dropped it. It is not part of the mechanism.

---

## 13. Step 11: final evaluation

Only after the round loop:
1. **Pick the harness to evaluate** using validation data, never test. If you compare several harness rounds, run each on validation (3 trials) and choose by all-pass rate, with criterion pass rate as the tie-break.
2. **Run the chosen harness and the base harness on test,** 3 trials each, on the same tasks.
3. **Report the paired bootstrap CI.**
4. **State that the critic, the classifier and the builder are a second model in the loop.**

All of our stage-harness results so far are on the training split, which the stage feedback was built from. They are therefore optimistic.

---

## 14. Parameters (all in one table)

| Parameter | Value | Where |
|---|---|---|
| Trials per task | 3 | runner config |
| Log truncation: request / assistant text / args / write content / old_string / result / stage_end result | 1,500 / 400 / 1,400 / 900 / 150 / 220 / 900 chars | `make_logs.py` |
| `MIN_RUNS` (active or policy threshold) | 2 runs | build script |
| `POLICY_RATIO` | 0.25 of peak (or ≤1 run) | build script |
| `SPLIT_WARN` | more than 5 active kinds | build script |
| `MIN_RELABELS` (confusion notes) | 5 | build script |
| Examples per stage | 2 | build script |
| Builder model / max tokens | claude-sonnet-5-5 / 1,500 | build script |
| Critic model / max tokens / timeout | claude-sonnet-5-5 / 900 / 180 s | `*_stage_common.py` (env `STAGE_CRITIC_MODEL`, `STAGE_CRITIC_TIMEOUT`, `STAGE_CRITIC_URL`) |
| Fit / classifier model / max tokens | claude-haiku-5-5 / 120 (fit), 80 (classifier) | env `STAGE_FIT_MODEL` |
| Critic input: request / summary / per-call args / per-call result / total log | 6,000 / 3,000 / 400 / 700 / 40,000 chars | `tools/stage.py` |
| Calls shown to the stage classifier | up to 40, 300 chars each | `tools/stage.py` |
| Run fact, ours only: entities in the critic input / in the review | 60 / 40 | `tools/stage.py` |
| Run fact, ours only: hit-list cap for "surfaced" | 1–150 distinct entities per result | `stage_reference.json` |
| Stuck threshold (critic asked for a new approach) | 3rd opening of the same stage | `tools/stage.py` |
| Fit-checked tools | bash, grep, glob | `stage_guard.py` |
| Writing stages (no write note) | Write the response, Check or revise the response, Calculate figures | `stage_guard.py` |
| Loop breaker | none (deliberate) | — |
| Concurrency (our runs) | 20 runs, 24 requests, 18 judge calls | runner config |

---

## 15. Cost and time (what it took us)

| Item | Our figure |
|---|---|
| One training round (240 runs, concurrency 20) | 1.5–2 hours; failures from sandbox infrastructure are retried automatically by the launch script |
| Annotation of one round (10 parallel batches of 8 tasks) | about 15–25 minutes wall time; about 95K–580K tokens per batch (setup-dependent, see section 6.4) |
| Round-1 bootstrap annotation (2 sequential + 11 parallel batches + merge) | about 1.5 hours |
| Merge | 10–15 minutes, about 200K tokens |
| Reference build | 14 LLM calls, about 3 minutes |
| Critic and classifier calls per run | about 10–15 critic calls, plus classifier and fit calls |
| Runs per stage-harness round | about 55–75 tool calls and 9–13 stages per run (vs about 30–60 calls in the base harness) |

---

## 16. Pitfalls we hit

1. **Test contamination.** Our first analysis was on test runs; we archived it and redid everything on train.
2. **Hindsight in labels.** We first wrote "decoy" in stage notes; the agent could not have known that.
3. **Hand-written guidance leaks the designer's knowledge.** It also produced cross-stage notes, which break rule A8. Generate the reference instead.
4. **Groups instead of stages.** The model briefly declared 5 coarse groups. The individual stages were the intended level.
5. **Tool-usage percentages** carried no signal and could steer toward failure-prone tools.
6. **A feature whose motivation came from test analysis** (tracking entities seen but not opened) had to be re-justified from training data and restricted to the stages where training placed that error.
7. **General improvements are out of scope.** We rejected an output cap.
8. **The critic can make things worse.** Review-endorsed errors rose to 10 in round 3. Measure it.
9. **Notes asking the agent to fix its label are ignored.** Classify instead.
10. **A shared scratch folder for parallel annotators** caused overwritten scripts.
11. **Machine reboots kill runs.** Resume from the graded runs, and move units with zero-byte files aside before resuming.
12. **Parallel tool results out of order:** annotators must match results by content, and so must the agent. It mixed up matter paths several times.
13. **Traces with no events** (agent error): handle them explicitly (section 4.3).
14. **The harness is frozen at launch,** so edits apply only to the next run. Know which version produced which runs.

---

## 17. Checklists

**Setup (once)**

- [ ] Train, validation and test split fixed; validation and test material out of reach.
- [ ] Base harness copied untouched.
- [ ] Traces record calls, arguments, results, indices and termination; grader gives per-criterion reasoning.
- [ ] Second-LLM endpoint works (critic, classifier, builder).
- [ ] Entity regex for compact-log target markers chosen (or markers left out); `TASK_WORDS` and `HINDSIGHT_WORDS` set (section 7).

**Round 1: observe the base agent (sections 3–8)**

- [ ] Base harness run on all training tasks × 3 trials: all units graded, latest attempts used, empty traces handled.
- [ ] Compact logs built (section 4); first catalog folder created with `taxonomy.md` and `check.py` (section 5).
- [ ] First stage vocabulary grown bottom-up by sequential batches; descriptive, benchmark-level names, no hindsight words (sections 5.3, 6.1, 6.2).
- [ ] Remaining tasks annotated in parallel batches with the vocabulary frozen and `NEW:` proposals (section 6.3); private scratch folders.
- [ ] Vocabulary merged (section 8); `check.py` reports ALL CHECKS PASSED.
- [ ] Run facts decided: defined only for a common error kind that can be computed from the trace, or none (section 9.2, step 5).

**Build the mechanism (once, sections 9–11)**

- [ ] Stage reference generated from the round-1 catalog; generated text read for task content and hindsight words (section 9).
- [ ] Stage tools, guard, critic, label classifier, fit notes and system prompt section built (section 10).
- [ ] Unit test passes (section 11.1); smoke run passes (section 11.2).
- [ ] Code frozen: from here on, rounds change only the stage list and the regenerated reference (rule 5).
- [ ] First stage-harness training run complete (section 11.3).

**Each later round (section 12)**

- [ ] Compact logs built for the new runs; new catalog folder with the latest merged `taxonomy.md` and `check.py`.
- [ ] Round brief written (section 12.1).
- [ ] Annotation batches run with the vocabulary frozen; declared stages used as default boundaries and relabelled when wrong; `critic`, `critic_note` and `label_check` filled.
- [ ] Agent-defined (`new`) stages relabelled to an existing stage, or kept as `NEW:` stages (section 12.4, step 1).
- [ ] Vocabulary merged; `check.py` reports ALL CHECKS PASSED.
- [ ] Round report written (section 12.2).
- [ ] Stage list updated only where section 12.4's criteria are met:
  - `NEW:` stages put together by what their calls do; promoted only if seen in ≥2 runs, at least one all-pass, and no existing stage fits; otherwise candidates reported with their counts;
  - splits and merges only with the evidence 12.4 asks for;
  - each change logged with its evidence in the design log.
- [ ] No code changes.
- [ ] Reference rebuilt from **all** catalogs (oldest first); generated text read for task content and hindsight words.
- [ ] `REGRESSION` and `SPLIT HINT` outputs reviewed; the split criterion re-checked.
- [ ] Unit test passes with the new reference.
- [ ] Training run launched; results compared with the previous round on the same task and trial pairs, with a paired bootstrap CI and the 0/1/2/3-of-3 distribution (section 11.3).
- [ ] Decided whether another round is worth it: stop when the gain over the previous round is within noise (section 12.5).

**Before claiming a result (section 13)**

- [ ] Candidate rounds run on validation, 3 trials each, same tasks; harness chosen by all-pass rate, criterion pass rate as tie-break.
- [ ] Chosen harness and base harness run on test, 3 trials each, same tasks; paired bootstrap CI reported.
- [ ] Second model in the loop (critic, classifier, builder) disclosed.

---

## 18. Glossary

| Term | Meaning |
|---|---|
| **All-pass** | A run in which every rubric criterion passes. |
| **Stage** | A named stretch of work with one intent, at benchmark level. |
| **Catalog** | One round's annotated training runs and vocabulary (section 5). |
| **First error** | The earliest stage whose action or decision led to a failed criterion. |
| **Active failure** | An error kind seen in ≥2 runs at a stage in the latest round. |
| **Stage policy** | A positive rule kept for an error kind that became rare after guidance. |
| **Effective stage** | The stage a stretch of calls actually belongs to, according to the classifier. |
| **Review-endorsed** | An error the critic's review pushed the agent into. |
| **Mixed task** | A task with both passing and failing trials. |
| **Divergence** | Where passing and failing runs of a mixed task split. |
| **Entities seen but not opened** (surfaced-not-opened) | A needed entity appeared in the agent's results but none of its documents was opened. |
