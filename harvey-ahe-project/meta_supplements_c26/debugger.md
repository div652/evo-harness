# Domain guidance: LAB legal-work tasks

## Scoring facts that shape the diagnosis

- One judge marks every criterion pass or fail. A trial **all-passes**
  (outcome `all_pass`) only when every criterion passes, and the campaign
  metric is the mean all-pass rate: a trial that fails even one criterion
  counts as 0. Trial `score` (the share of criteria passed) is reported and
  only breaks ties.
- So the decisive question for every failing trial is: **which criteria
  stopped it from all-passing, and why?** Identify each failed criterion
  specifically, not just the overall impression. A trial that failed one or
  two criteria in otherwise complete work is a near-miss; say exactly what
  each of those criteria needed.
- `[harvey-ahe judge-input limit]` in a judge's reasoning means the deliverable
  text was too large to grade and was failed without a model call.
- Judges read text extracted from the output files (`.docx` through pandoc,
  `.xlsx` through pandas, `.pptx` through markitdown, `.pdf` through
  pdfplumber). If the judge reasoning says content is absent, check whether
  it was in the file in a form the extraction drops.

## Campaign strategy: inconsistent tasks and one-criterion misses

This campaign improves the harness through two kinds of evidence. Establish
them first for every task, and give them the most care.

1. **Inconsistent task:** some of the task's trials all-pass and others do
   not (count `evidence_only` trials too). This is the most important
   evidence there is: the harness has already produced a fully passing run
   of this task, so the failing runs did not lack the ability; something
   in their path differed. Compare a passing and a failing trial closely
   and find the decisive step: the earliest point where the failing trial
   did something different that led to the criterion it missed. Say
   whether that difference looks like chance or a systematic weakness, and
   what would make the passing behaviour happen in every run.
2. **One-criterion miss:** a trial that failed exactly one criterion.
   Everything else in it passed, so that one criterion is the whole
   difference between 0 and 1. Work out precisely why it was missed.

For each criterion missed by a failing trial of an inconsistent task, and
for each one-criterion miss, give a short, generic label of your own that
describes what kind of requirement was missed and why, in terms that could
recur on other tasks (never task content). The Evolve Agent groups these
labels across tasks, so make them descriptive and reuse the wording
consistently.

Report it in the existing fields:

- `recurrent_pattern_key`: `inconsistent:<your label>` or
  `one-criterion-miss:<your label>` (use `inconsistent:` when both apply);
  for any other task, a key as usual.
- The first line of `root_cause`: `Focus: <inconsistent | one-criterion
  miss | neither>; all-pass trials: <k> of <n>; one-criterion misses: <m>;
  missed: <your label>; decisive step: <short phrase or none>`.

## Where the evidence is

The task-detail document lists each trial with:

- `termination_reason`, `outcome`, `score`;
- `native_result`: `agent_error`, `finish_called`, `finish_summary`,
  `tool_call_counts`, `assistant_turns`, `wall_clock_seconds`,
  `output_files` (path, size, hash), `workspace_files`;
- `judges[]`: one entry, with `all_pass`, `n_passed`, `n_criteria`, and
  `criteria_results` (each with its verdict and reasoning);
- `artifacts`: the trial `result`, the `trace` (JSON lines: the user
  instruction, then every message with tool calls and tool results, then a
  termination event), the judge's `evaluator` score file, and copies of each
  graded `deliverable`;
- `readable_artifacts` (listed in the query): `readable_trace` is the same
  trace as `trace.md`, with one `## jsonl line N` header per event and real
  line breaks; `readable_deliverable` is each output file as the exact text
  the judges read (`.docx` through pandoc, `.xlsx` through pandas).

Read the readable trace and the deliverable text, not only the summary
fields. Do not open `.docx` or `.xlsx` files with `read_file`; they are
binary. Search the readable trace for the failed criterion's key terms to find
where the agent handled (or skipped) that point.

## Diagnosis order for this benchmark

Work through these in order and stop at the earliest consequential failure:

1. **How the run ended.**
   - `max_turns_exceeded`: where did the turns go (re-reading, retries,
     failing scripts, long drafting in many small edits)? Was anything written
     to `/workspace/output` before the limit?
   - `context_overflow`: which tool results were largest (often a whole
     long document returned by `read`)?
   - `no_tool_calls`: the agent replied with text and never called `finish`;
     were the deliverables already written?
   - `agent_error`: quote the error. A tool exception points to a tool
     implementation; a model or infrastructure error is
     `framework_or_adapter` or `environment`.
   - Rejected `finish` calls: what was missing?
2. **Deliverables.** Compare the instruction's requested files (names,
   formats, count, required sections) with `output_files`. Common failures:
   a file missing, in `/workspace` instead of `/workspace/output`, in the
   wrong format (text or markdown where `.docx` or `.xlsx` was asked for),
   empty or truncated, or a script that errored so the file was never
   produced.
3. **Reading.** Did the agent find and open every relevant document? The
   documents folder is a shared store of about 9,300 files from 266
   matters, so also check the search: which folders, names or terms it
   looked for, and whether a needed document was never found. Look for
   `read` results starting with `Error`, parse failures, partial reads
   through `offset`/`limit` that never continued, or decisions based on
   `grep` hits alone.
4. **Substance.** For each failed criterion (on a near-miss, every one of
   them), classify the judge's reason:
   an issue not covered, a factual or numerical error versus the documents,
   a required section or element missing, a wrong format or structure, or an
   instruction not followed (audience, length, scope). Group failures by
   class.
5. **Process.** Did the agent plan, keep notes, and verify its output before
   finishing? Did it finish while known gaps remained?

## Mapping to components (typical, not automatic)

- Missing or misformatted deliverables, early finish: `system_prompt`, the
  `finish` tool implementation or description, or `memory`.
- Incomplete reading, context overflow from large reads: `tool_implementation`
  (`read` paging or summaries), `tool_description`, or `middleware`.
- Turn exhaustion: `system_prompt` (planning), or `middleware` (budget
  reminders).
- Coverage and accuracy gaps: `system_prompt` (review protocol), `skill`
  (text-only procedure), or `sub_agent` (bounded reviewer or reader).
- Tool exceptions or confusing tool errors: `tool_implementation` or
  `tool_description`.

## Paired comparison and reporting

A trial is `passing` when it all-passes. Training runs three trials per
task, so a task may have both passing and failing trials: compare them
directly and name the step where the failing trial diverged, since that
inconsistency is what the metric punishes. When none of the three passes,
the task gets two more trials marked `evidence_only` (artifacts under the
`raw_extra_evaluation` root). No metric counts them, but they are full
evidence: if one of them passes, compare it with the failing trials like
any other passing trial. When no trial passes, give "no
passing trial" as the limitation, and contrast the higher- and lower-scoring
trials, and passed against failed criteria inside one trial, in the
root-cause text.

Use generic `recurrent_pattern_key` labels that can recur across tasks, for
example `deliverable-format-mismatch`, `incomplete-document-reading`,
`turn-budget-exhaustion`, `context-overflow-large-read`, `issue-coverage-gap`,
`factual-error-vs-source`, `early-finish`, `tool-error-unhandled`.

Describe mechanisms, not legal content. Do not copy criterion wording, party
names, figures, or conclusions from a training task into recommendations.
