# Domain guidance: Harvey LAB firm-knowledge tasks (RRSI digester)

The trajectories come from a NexAU agent answering questions about a law
firm's past work: it searches one shared store of matter documents (mostly
`.docx`, with `.eml`, `.xlsx`, and `.pptx`) through its file tools and a
shell, and writes one answer file, `/workspace/output/response.md`. One judge
grades that file against a rubric of 1 to 85 pass/fail criteria (median 6),
usually one per matter or fact the answer had to contain, each with a
verdict and the judge's reasoning. A trial's score is the share of criteria
passed; a missing `response.md` fails every criterion, and content left in
chat or scratch files earns nothing. Read the judge's per-criterion verdicts
first (which matters or facts were missed and why), then search the trace
for anchors (search terms, folder and file names, tool calls) to find where
each was found, lost, or never written into the answer.

(Adapted from the Harvey LAB digester brief of google-research/rrsi. The
evidence layout below describes this campaign's evidence bundle.)

## Where the evidence is

The task-detail document lists each trial with:

- `termination_reason`, `outcome`, `score`;
- `native_result`: `agent_error`, `finish_called`, `finish_summary`,
  `tool_call_counts`, `assistant_turns`, `wall_clock_seconds`,
  `output_files` (path, size, hash), `workspace_files`;
- `judges[]`: the judge's `all_pass`, `n_passed`, `n_criteria`, and
  `criteria_results` (each with its verdict and reasoning);
- `artifacts`: the trial `result`, the `trace` (JSON lines: the user
  instruction, then every message with tool calls and tool results, then a
  termination event), the judge's `evaluator` score file, and copies of each
  graded `deliverable`;
- `readable_artifacts` (listed in the query): `readable_trace` is the same
  trace as `trace.md`, with one `## jsonl line N` header per event and real
  line breaks; `readable_deliverable` is each output file as the exact text
  the judge reads (`.docx` through pandoc, `.xlsx` through pandas).

Read the readable trace and the deliverable text, not only the summary
fields. Do not open `.docx` or `.xlsx` files with `read_file`; they are
binary. Search the readable trace for the failed criterion's key terms to find
where the agent handled (or skipped) that point.

## The document store

All tasks share one store of about 9,300 files in 266 matter folders,
mounted read-only at `/workspace/documents`; only a few files matter for a
given task.

## Termination reasons

- `max_turns_exceeded`: the run used every turn; check whether anything
  was written to `/workspace/output` before the limit.
- `context_overflow`: the prompt outgrew the context limit; the largest
  tool results (often a whole document returned by `read`) show why.
- `no_tool_calls`: the agent replied with text and never called `finish`.
- `agent_error`: an exception ended the run; quote it.
- Rejected `finish` calls are in the trace with the reason.

Describe mechanisms, not legal content, in `blocker`, `narrative`, and
`needed_instead`. Quotes in `evidence` may contain task content.
