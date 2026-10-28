# Brief: stage annotation of base-harness training runs

Goal: describe how the agent solved each run as a sequence of named stages,
growing a finite stage vocabulary (`taxonomy.md`) as more runs are labelled,
and mark where each failing run first went wrong. All paths are relative to
`/home/agarwaldi/AHE_Harvey_cao/harvey-ahe-project/analysis/stages-train/`.

Data: the base harness (C0) of campaign 23 on its 80 TRAINING tasks, 3 runs
each (Harvey LAB firm-knowledge: a shared store of ~9,300 files in 266 matter
folders under `documents/matters/<NNNN-NNNNN>/`; the agent searches it and
writes a deliverable, usually `response.md`; one judge grades it against
rubric criteria; a run all-passes only if every criterion passes).
Use ONLY these training runs. Do not open anything under `analysis/` other
than this folder, and nothing under `/home/agarwaldi/archive/`.

## Inputs
- `taxonomy.md`, `changelog.md`: the vocabulary so far (empty at the start).
- `logs/<task>_T<k>.txt`: one compact log per run. Header: request, judge
  result, rubric criteria (title + verdict + judge reasoning), rubric matter
  numbers. Body: `[n] CALL tool args` and `[n] -> size: start of result`,
  with `<<target matter in result: …>>` markers (`FIRST TIME` on first
  appearance). `[n]` is the event number; calls sharing a number ran in
  parallel. The raw trace path is in the header if a log line is not enough.
- `runs_index.json`: task, trial, all_pass, n_passed/n_criteria per run.

## Rules for stages
1. Stage names are descriptive verb phrases specific to this benchmark but
   not to a task (e.g. "List matter folders", "Search file names for request
   keywords"); never codes, never task content (no matter numbers, parties,
   legal topics, request keywords).
2. Every tool-call event belongs to exactly one stage. Stages are contiguous
   event ranges in time order covering the whole run; a stage may recur. A
   stage is a maximal run of consecutive calls with one intent; if parallel
   calls mix intents, label by the dominant intent and say so in the note.
3. Reuse an existing stage when it describes the intent correctly; add a new
   one only when every existing one would misdescribe it. Never rename or
   delete existing rows; record doubts under "Issues".
4. Agent's view only: stage names, notes and tags describe what the agent
   knew and intended at that moment. Never use hindsight words ("target",
   "decoy", "correct/wrong matter", "rubric") in stage names, tags or notes;
   say "a candidate matter", "the matter it later picked". Tags are short
   labels for agent-observable facts (e.g. a search returned nothing).
5. Hindsight goes only into: the per-stage `hindsight` field, `failure_point`,
   `first_error`, `other_errors`, `divergence`. Hindsight values and error
   kinds are also a growing vocabulary in taxonomy.md.
6. Task content may appear only in the task's `context` field and in a
   "Task context" section at the end of its markdown.

## First error (failing runs only)
The earliest stage whose action or decision led to a failed criterion: where
the agent's own behaviour first went off course, not where the damage became
visible (e.g. a needed matter never surfaced → the search that should have
found it; surfaced but never opened → the stage right after it surfaced where
the agent chose what to open and left it out; opened but misjudged → the
stage where the judgement was made; context overflow → the stage with the
oversized reads). Later independent errors go to `other_errors`. Each error
gets a `kind` from the error-kind vocabulary in taxonomy.md (add kinds as
needed, short and generic).

## Outputs per task
`annotations/<task>.json`:
{"task": "...", "context": "1-3 lines of task context",
 "runs": [{"trial": 0, "all_pass": false, "n_passed": 0, "n_criteria": 3,
   "stages": [{"stage": "<name>", "start": 2, "end": 5, "tags": [...],
               "hindsight": "<value>", "note": "generic note"}],
   "sequence": "stage → stage → … (collapse consecutive repeats)",
   "failure_point": "generic; empty for passing runs",
   "first_error": {"stage_no": <1-based row>, "stage": "...", "start": a,
                   "end": b, "events": "[x]-[y] if narrower, else empty",
                   "kind": "...", "why": "one sentence"} | null,
   "other_errors": [same shape]}],
 "divergence": "mixed outcomes: where passing and failing runs split;
                all pass: the shared successful procedure; all fail: whether
                the runs failed the same way and at which stage"}
`annotations/<task>.md`: per run a stage table
`| # | Stage | Events | Notes | Hindsight |`, with " **⛔ first error**" appended
to that row's Notes (" **⚠ later error**" for other_errors), a
`**First error:** stage <n> (<stage>) [a]-[b], <kind>: <why>` line under the
table, a `**Sequence:**` line, a short comparison, and a Task context section.

## taxonomy.md layout
Sections: Stages (| Stage | What the agent is doing | Typical tools | Added in
| Example |), Tags (| Tag | Meaning | Added in |), Hindsight values
(| Value | Meaning |), Error kinds (| Kind | Meaning | Added in |).
Examples are `<task>_T<k> [a]-[b]`.
