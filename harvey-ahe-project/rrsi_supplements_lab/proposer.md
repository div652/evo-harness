# Domain guidance: Harvey LAB legal tasks (RRSI proposer)

## The benchmark

The agent does professional LEGAL work across 25 practice areas: contract
review, drafting, and redlining; M&A and capital-markets work; governance,
funds, IP, litigation support, and more. Each task gives it a folder of
source documents and instructions, and it must write DELIVERABLE FILES to
`/workspace/output` under the requested names, almost always `.docx`. There
is no network access: everything the agent needs is in the documents folder.

One judge grades the deliverables against a strict per-criterion rubric of
23 to 100 independent pass/fail criteria per task. S is the share of
criteria passed, pooled over every trial, so long rubrics carry more weight.
A criterion fails when the required content is missing from the deliverable
file: work left in the chat answer or in scratch files earns nothing, and a
missing deliverable fails every criterion it should have satisfied. The
frozen policy is a strong model; failures are rarely "the model cannot do
legal work" and usually "the harness starves, floods, or misroutes it".

Passing more criteria on tasks the agent already attempts well (coverage,
completeness, the exact requested file and format, correct figures carried
into the deliverable) is worth as much as rescuing failed runs. Routing
computed results into the output files is a first-class concern.

Out of bounds, and checked before measurement: reading or format-gaming the
judge, and any task-specific content (task names, party or company names,
file names of specific tasks, figures, conclusions, criterion wording). The
run is judged on held-out legal tasks and on other agentic-workspace
benchmarks with different tools, so prefer mechanisms a competent lawyer's
workflow would justify in ANY environment (read what the task asks; check
the figures carried into deliverables; cover every requested item) over
mechanisms keyed to this benchmark's incidental quirks (its tool names,
folder layout, or judge phrasing). Litmus test: would this help a competent
lawyer producing deliverables on many unfamiliar legal tasks, in any
reasonable working environment?

(Benchmark description adapted from the Harvey LAB proposer brief of
google-research/rrsi. The harness facts below describe this campaign's NexAU
harness.)

# Components in This Harness

| Component | Files | Behaviour specific to this harness |
|---|---|---|
| System prompt | `systemprompt.md` | Rendered as a Jinja template: never write Jinja markup (two opening curly braces, or an opening curly brace followed by a percent or hash sign) |
| Tool description | `tool_descriptions/*.tool.yaml` | Sent as an API tool schema (`openai` mode) |
| Tool implementation | `tools/*.py` | Runs on the host; reaches the sandbox only via `handle_for(agent_state)`; must catch every exception |
| Middleware | `middleware/*.py` + `agent.yaml` `middlewares:` | Runs on the host; duck-typed hooks; can rewrite messages and tool results |
| Skill | `skills/<name>/SKILL.md` + `agent.yaml` `skills:` | Text only; its folder is not visible in the sandbox |
| Workspace seed | `workspace_seed/**` | Copied into every trial's `/workspace` before the agent starts (`workspace_seed/skills/docx/scripts/x.py` becomes `/workspace/skills/docx/scripts/x.py`); runs only inside the sandbox through `bash` |
| Sub-agent | `sub_agents/<name>/agent.yaml` + `systemprompt.md` + `agent.yaml` `sub_agents:` | Shares the parent's sandbox; forced onto the evaluated model; `max_iterations` at most 200 |
| Long-term memory | `LongTermMEMORY.md` | Appended verbatim to the end of the evaluated agent's system prompt; an empty file adds nothing |
| Short-term memory | `ShortTermMEMORY.md` | Runtime-owned |

## Registering New Components

**Creating a file is NOT enough. Register it in `agent.yaml`:**

- **New tool:** a `.tool.yaml` (with `binding: tools.<module>:<function>`),
  a `tools/<module>.py`, and a `tools:` entry with `name` and `yaml_path`.
- **New middleware:** a `middleware/<module>.py` and a `middlewares:` entry
  with `import: middleware.<module>:<Class>` and `params:`.
- **New skill:** a `skills/<name>/SKILL.md` with `name` and `description`
  frontmatter, and a `skills:` entry with the folder path.
- **New sub-agent:** a `sub_agents/<name>/agent.yaml` and a `sub_agents:`
  entry with `name` and `config_path`.

The harness folder is on `sys.path`, so `binding: tools.finish:finish` loads
`tools/finish.py`. Confirm exact formats in the framework skill before
editing.

# Protected Invariants (the adapter or manifest rejects violations)

- **Fixed fields:** `finish` stays the stop tool. `stop_tools: [finish]`,
  `max_iterations: 200`, `tool_call_mode`, and the `llm_config` model fields
  are fixed. Sub-agents may not exceed 200 iterations.
- **Sandbox access:** harness Python reaches the sandbox only through
  `harvey_ahe.workspace.handle_for(agent_state)`, called on every tool call.
  Never cache a handle or keep per-trial data in module globals: trials run
  concurrently in one process.
- **Banned imports and calls.** Harness Python may not import:
  - `ahe_runner`, `benchmark_adapter`, or `lab_core`;
  - any `harvey_ahe` module other than `harvey_ahe.workspace`;
  - process, network, FFI, or dynamic-import modules;
  - anything under `workspace_seed/` (no imports or `binding:` entries).

  Python under `workspace_seed/` is exempt from these bans because it only
  runs inside the sandbox.

  It may not call `eval`, `exec`, `compile`, `__import__`, `os.system`,
  `os.popen`, `os.fork*`, `os.exec*`, or `os.spawn*`.
- **Module names:** top-level harness files and folders must not reuse the
  name of a standard-library, protected, or installed module (for example
  `docx.py` or `json/`).
- **Identifiers:** no training task identifiers anywhere, and no grader
  identifiers in `.py` or `.yaml` files.

# Mechanics You Must Get Right

- **New or changed tool.** The Python parameters, minus `agent_state`,
  `global_storage`, and `sandbox`, must equal the schema `properties`.
  Parameters without defaults must equal `required`. Catch every exception
  and return error text; a raised exception ends the trial as `agent_error`.
  Keep `disable_parallel: true` for tools that write to the sandbox.
- **Shell.** Every `exec` is a fresh shell (default timeout 60 s, maximum
  600). Multi-step work must be one command, or a script written to
  `/workspace` first. There is no network, and nothing can be installed.
- **Rejecting `finish`.** Return `{"status": "error", "error": "..."}`. Keep
  a cap on rejections so a run cannot loop.
- **Skills and scripts.** NexAU skill folders are not visible in the
  sandbox. Put scripts the agent should run with `bash` under
  `workspace_seed/`; they appear under `/workspace` in every trial and run
  with the sandbox's own Python, pandoc, and LibreOffice.
- **Middleware.** Keep any rewriting auditable, and never drop the
  instruction or the deliverable requirements.
- **What the judge reads.** The judge reads extracted text:
  - `.docx` through pandoc (the agent can run pandoc in the sandbox to
    preview it);
  - `.xlsx` through pandas, which reads only saved cell values, so
    recalculate formulas with LibreOffice or write the values;
  - `.pptx` through markitdown;
  - `.pdf` through pdfplumber.

  Images and layout are invisible to the judge. A criterion whose judge input
  exceeds 240,000 characters fails without a judge call.
- **Documents.** Each task has its own documents folder, mounted read-only
  at `/workspace/documents`: 2 to 24 files, mostly `.docx`, with `.eml`
  and `.xlsx` files and an occasional `.pptx`. Usually several of them
  matter, and reading all of them in full can still use up context.
- **Context.** `read` returns whole documents. Several long documents can
  exhaust `max_context_tokens` (911793, counted with the o200k_base
  tokenizer). If you change that value, keep it at least 10,000 below the
  evaluated model's advertised 921,793-token input limit: a longer prompt
  is silently cut from the start rather than rejected.

# Safety Constraints for This Benchmark

- Never copy training task identifiers, party names, figures, legal
  conclusions, or criterion wording into the harness. Learn general classes
  from judge reasoning; do not turn individual criteria into a checklist.
- Never add text addressed to the judge, pad deliverables, or try to
  influence grading in any way other than doing the work better.
- Treat runtime-injected benchmark actions and all project supplements as
  protected, unmodifiable campaign inputs.
