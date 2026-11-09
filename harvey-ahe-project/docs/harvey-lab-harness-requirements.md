# Harvey LAB: what a task gives your harness, and what your harness must provide

This guide is for someone who wants to run the **Harvey LAB** benchmark (`harveyai/harvey-labs`) with their own agent harness and stay faithful to LAB's reference harness. It covers:

1. what one LAB task consists of;
2. what LAB's reference harness gives the model: system prompt, tools, skills, sandbox and loop;
3. how a run is graded;
4. a checklist of what your harness must reproduce.

Everything below was checked against the LAB source at commit `86678eba` ("feat: inject the deliverable filename matcher"). File references are relative to the repo root. The main ones are:
- `lab_core/harness/run.py`: assembles a run;
- `lab_core/harness/agent_loop.py`: the loop;
- `lab_core/harness/tools.py`: the tools;
- `lab_core/sandbox/sandbox.py`: the container;
- `lab_core/evaluation/`: grading.

LAB's own design notes are in `docs/harness-internals.md`.

---

## 1. The big picture

LAB's reference harness is deliberately small:

- **One loop.** It runs one model and one tool executor, with no planner, sub-agents, middleware, memory or context compaction.
- **One Podman container per run.** All six workspace tools run against it.
- **System prompt:** a fixed preamble plus three skill manuals (`docx`, `xlsx`, `pptx`).
- **First user message:** the task's instructions.
- **The model never sees the rubric.**
- **Grading** is a separate phase after the run. An LLM judge checks each rubric criterion against the deliverables the agent wrote. A task *all-passes* only if every criterion passes.

```text
task.json ──instructions──────────────► first user message
           └─docs_dir / documents/ ────► /workspace/documents (read-only)
system_prompt.md + finish note + 3 × SKILL.md ──► system message
skills/*/scripts/ ─────────────────────► /workspace/skills/<name>/scripts/
7 tools (bash, read, write, edit, glob, grep, finish) ──► model's tool list
loop: model → tool calls (sequential) → results → … until finish / no tool calls / 200 turns / context overflow
/workspace/output/* ───────────────────► judge, one call per criterion
```

---

## 2. What a task contains

### 2.1 Layout

```text
tasks/<practice-area>/<task-name>/task.json
tasks/<practice-area>/<task-name>/documents/...      (the task's own documents), or
tasks/<practice-area>/tasks/<id>/task.json  with  "docs_dir": "../../dms"  (shared corpus)
```

At this commit there are **2,010 tasks in 27 practice areas**, for example:
- contracts: 498;
- firm-knowledge: 250;
- corporate-ma: 161;
- intellectual-property: 147.

Most tasks have their own `documents/` folder (median 8 files, up to about 4,000). The 250 **firm-knowledge** tasks instead share one document store via `"docs_dir": "../../dms"`. That store has 9,288 files: 8,055 .docx, 615 .eml, 573 .xlsx, 45 .pptx. Each firm-knowledge task is a question about the firm's own past matters, and the agent has to search that store to answer it.

### 2.2 `task.json`

```json
{
  "id": "002",
  "title": "Count of Merger Reviews Drawing a Second Request",
  "instructions": "A merger client is asking about … which were they?\n\nOutput: write your complete answer to `response.md` — a single self-contained markdown file …",
  "docs_dir": "../../dms",
  "criteria": [
    {
      "id": "C-001",
      "title": "Qualifying matter — Harrowgate PE 1003-00001",
      "match_criteria": "Identifies matter 1003-00001 (Harrowgate PE) as a qualifying matter.",
      "deliverables": ["response.md"]
    }
  ],
  "deliverables": {"response.md": "response.md"}
}
```

| Field | Required | Used by | Meaning |
|---|---|---|---|
| `title` | yes | judge | Short task title. It is the only task context the judge gets. |
| `instructions` | yes | agent | The assignment. It becomes the **first user message**, verbatim. It names the expected deliverable file(s) in prose. If missing, LAB reads `instructions.md` (no task at this commit does). |
| `criteria[]` | yes | judge | Rubric items: `id`, `title`, `match_criteria`, and optional `deliverables` (the output files the judge sees for that criterion). Median 54 per task. |
| `deliverables` | no | judge | Map from deliverable key to expected filename. Types across all tasks: .docx 1,560, .md 261, .xlsx 45. |
| `docs_dir` | no | harness | Points at a shared corpus instead of `documents/`, as a path relative to the task folder. |
| `criteria[].evaluation_options.include_docx_redlines` | no | judge | Show tracked changes to the judge instead of accepting them. No task uses it at this commit. |

**What the agent must never get:** `task.json` itself, the criteria, and the `deliverables` map. LAB mounts only the documents folder into the sandbox. The system prompt also warns that reading `task.json` counts as a rule violation.

---

## 3. What the model receives

### 3.1 Messages

```text
[system]  system_prompt.md  (+ finish note)  + "## Skill: docx" … + "## Skill: pptx" … + "## Skill: xlsx" …
[user]    task.json "instructions"
```

That's all there is: no few-shot examples, no task metadata and no extra turns.

### 3.2 System prompt (`lab_core/harness/system_prompt.md`, verbatim)

```markdown
You are an AI agent executing a task provided by the user within a workspace.

## Workspace layout

Everything you work with lives under one workspace root. **`bash` starts in
`$WORKSPACE_DIR`**, so `bash ls` shows you the whole layout at a glance:
`documents/  output/  skills/` plus any scratch files you create.

- **`$WORKSPACE_DIR`** — your working area, default `bash` cwd. Use it for
  notes, intermediate files, and skill output. Skill scripts live at
  `$WORKSPACE_DIR/skills/<name>/scripts/`.
- **`$DOCUMENTS_DIR`** (`$WORKSPACE_DIR/documents`) — task documents.
  Read-only.
- **`$OUTPUT_DIR`** (`$WORKSPACE_DIR/output`) — deliverables. The harness
  routes relative `write` and `edit` paths here automatically.
- **Task configuration** (`task.json`) — contains the task definition and the
  grading rubric. Do not read, search, or reference it. Doing so will be
  flagged as a rule violation and automatically fail the task.

## Tool conventions

- Use `read` to consume input files (handles .docx, .xlsx, .pptx, .pdf, and
  plain text).
- Use the file-type skill manuals below to produce binary deliverables
  (.docx, .xlsx, .pptx).
- Use `write` only for plain markdown — typically a `response.md`
  summarizing your work.
- Use `edit` for incremental refinement of a file you have already created.

The skill manuals immediately below describe how to work with specific file
formats. Read them before tackling the task.
```

**Finish note.** When the `finish` tool is enabled (the default), `run.py` inserts this right after the `edit` bullet:

```markdown
- When all deliverables have been created in `$OUTPUT_DIR` and no further
  work is needed, call `finish` with a brief summary and the list of
  deliverable files you produced. Do not keep reading or editing after
  the work is complete.
```

**Skills.** Each `SKILL.md` is then appended, in sorted order (docx, pptx, xlsx), as `\n\n## Skill: <name>\n\n<full SKILL.md text>`. See section 5.

### 3.3 Model settings (reference defaults)

| Setting | Default | Notes |
|---|---|---|
| `max_turns` | 200 | One turn is one model call plus its tool calls. |
| `temperature` | 0.0 | Sent only to models that accept it. |
| `reasoning_effort` | none | On the OpenAI Responses adapter, `reasoning: {effort, summary: "auto"}` is sent **only when an effort is set**. With no effort, LAB sends no `reasoning` field, so reasoning summaries are not requested. If you want the model's reasoning in your traces, request summaries yourself. |
| Max output tokens | 128,000 (OpenAI adapter) | Reasoning tokens share this budget. |

Adapters exist for OpenAI (Responses API), Anthropic, Google, Mistral, Meta, Fireworks, Baseten, OpenAI-compatible servers and GitHub Copilot (Chat Completions). Whatever the transport, the loop just calls `adapter.chat(messages, tools)`.

---

## 4. Tools

There are seven tools: six workspace tools plus `finish`. Each has a JSON-schema definition the model sees (`TOOL_DEFINITIONS` in `tools.py`) and a Python implementation the model doesn't see (`ToolExecutor`).

These rules apply to all of them:
- **Tool calls in one turn run sequentially, in order.**
- **Every result is a string.** Errors come back as text (`Error: …`, `SecurityError: …`, `Error: <ExceptionType>: …`). No exception ever ends the run.
- **Arguments** arrive as a JSON string. If it doesn't parse, the result is `Error: invalid JSON arguments: …`.

### 4.1 Paths inside the sandbox

| Path | Mode | Contents |
|---|---|---|
| `/workspace` | read-write | Scratch space and the default `bash` directory. Skill scripts are under `/workspace/skills/<name>/scripts/`. |
| `/workspace/documents` | **read-only** | The task's documents. |
| `/workspace/output` | read-write | Deliverables. **Only this folder is graded.** |

These env vars are set for every `bash` command: `WORKSPACE_DIR=/workspace`, `DOCUMENTS_DIR=/workspace/documents`, `OUTPUT_DIR=/workspace/output`. Absolute paths outside `/workspace` are refused.

### 4.2 Tool by tool

**`bash(command)`.** Runs `podman exec -w /workspace <ctr> timeout --kill-after=2 <T> bash -lc '<command>'`, with T = 60 s by default.
- **Result:** stdout, then `\nSTDERR:\n…` if there was any, then `(exit code N)` on failure. On timeout: `Error: command timed out after 60s` plus any output. Empty output gives `(no output)`.
- **Mismatch between description and behaviour:** the description says "the working directory persists between calls". In fact every call starts in `/workspace` in a fresh login shell, so `cd` and `export` do **not** carry over. Files (including `/tmp`) do persist, because the container lives for the whole run.

**`read(file_path, offset?, limit?)`.**
- **Relative paths** are looked up in `/workspace`, then `/workspace/documents`, then `/workspace/output`.
- **Office files and PDFs** are parsed **inside the sandbox** by the image's `parse-doc` command (120 s timeout):

  | Type | Parser | Output |
  |---|---|---|
  | .docx | pandoc | markdown, `--wrap=none` |
  | .pdf | pdfplumber | page text, plus tables as tab-separated rows |
  | .pptx | markitdown | text |
  | .xlsx | pandas | `=== Sheet: <name> ===` followed by each sheet as a table |

- **Everything else** is read as UTF-8, with undecodable bytes replaced.
- **No truncation.** `offset` (0-based) and `limit` slice the text by lines. Without them the whole file comes back, however large.
- **Errors:** a missing file gives `Error: file not found: …`. A parser failure gives `Error: failed to parse …`.

**`write(file_path, content)`.**
- Relative paths go to `/workspace/output/`, with parent folders created.
- An absolute path must be writable: under `/workspace`, but not `/workspace/documents`.
- Returns `Wrote N bytes to <path>`.
- The description tells the model to write only plain markdown this way, and to build .docx, .xlsx and .pptx files with the skill scripts.

**`edit(file_path, old_string, new_string, replace_all=false)`.**
- Relative paths are looked up in `/workspace/output`, then `/workspace`, then `/workspace/documents`.
- Documents are read-only, so editing one gives a `SecurityError`.
- `old_string` must occur exactly once unless `replace_all` is true. Otherwise the result is `Error: old_string found N times …` or `… not found …`.

**`glob(pattern, path?)`.**
- Runs **on the host** with Python's `Path.glob`. The search root defaults to `/workspace/documents`.
- Returns files only, **newest modification time first**, as paths relative to the search root, **at most 100**.
- **The cap is silent.** Nothing in the result says it was cut, so `**/*` over a large corpus looks like the whole corpus.

**`grep(pattern, path?, glob?, output_mode?)`.**
- Runs **on the host** with a Python regex over each file's raw bytes, decoded as UTF-8. The search root defaults to `/workspace/documents`, and the file filter (`glob`) to `**/*`.
- **It can't see inside .docx, .xlsx or .pptx files**, because those are zip archives. In practice it only finds text in plain-text files and .eml.
- **Output modes:**
  - `files_with_matches` (default): file paths;
  - `count`: `path: N` per file;
  - `content`: `path:line: text`.
- At most 250 result lines. Symlinks that escape the root are skipped.

**`finish(summary, deliverables?)`.**
- **Checks the deliverable list:** each listed path must exist under `/workspace/output`. Bare (`response.md`), `output/…` and absolute spellings are all accepted.
- **If a file is missing**, the call is refused with `Not finished: the following file(s) you listed do not exist …`. This happens at most **2 times**; after that, `finish` is accepted anyway.
- **When accepted**, it returns `Finished.` and the loop ends after that turn.
- **Doesn't validate against the task:** it never reads `task.json`, so it only checks the agent's own claim, not whether these are the right files.
- **The `summary`** goes into the run's `metrics.json` only. The judge never sees it.

### 4.3 How a run ends (`finish_reason`)

| Reason | When |
|---|---|
| `finish_tool` | `finish` was accepted, checked after that turn's tool results are added. |
| `no_tool_calls` | The model replied without tool calls. |
| `max_turns_exceeded` | 200 turns were used up. |
| `context_overflow` | The provider rejected the prompt with "prompt is too long" or "context_length_exceeded". |

The output folder is graded whatever the reason. There is no retry and no compaction.

---

## 5. Skills

A skill is a manual plus some scripts, with **no tool and no lazy loading**:

| Skill | `SKILL.md` | Scripts (run with `bash`) |
|---|---|---|
| `docx` | 8.5 KB: write, edit, redline, comment, validate .docx | `generate_from_md.py` (pandoc + reference template), `template_fill.py` (docxtpl), `unpack.py`/`pack.py` (XML editing), `redline.py`, `comments_add.py`, `accept_changes.py`, `validate.py` (mandatory last step), `soffice.py` |
| `xlsx` | 5.4 KB: build and edit workbooks, recalculate, check for errors | `build_workbook.py` (JSON spec), `recalc_libreoffice.py`, `recalc_pure_python.py`, `scan_errors.py`, `validate.py`, `pack.py`/`unpack.py`, `soffice.py` |
| `pptx` | 4.4 KB: build and edit decks, QA | `generate_pptxgenjs.js`, `generate_marp.sh`, `edit_shape.py`, `deterministic_qa.py`, `thumbnail.py`, `validate.py`, `pack.py`/`unpack.py`, `soffice.py` |

How LAB uses them:
1. Each `SKILL.md` is appended **in full** to the system prompt before turn 1 (section 3.2).
2. Each skill's `scripts/` folder is copied into the run's workspace at `/workspace/skills/<name>/scripts/`.
3. The model runs the scripts through `bash`, for example `python /workspace/skills/docx/scripts/generate_from_md.py …`.

Every manual says **"for reading, use the `read` tool"**. The skills are only for writing, editing and checking files.

The scripts need what the sandbox image provides (section 6): python-docx, openpyxl, docxtpl, pandoc, LibreOffice, Node, and so on. That's why skills only work inside LAB's image or an equivalent one.

---

## 6. Sandbox

| Item | Value |
|---|---|
| Runtime | Podman, rootless. LAB checks it with `podman info` (10 s timeout) before each run. |
| Image | `lab-sandbox:latest`, pulled from `ghcr.io/harveyai/lab-sandbox:latest` or built from `lab_core/sandbox/Dockerfile` |
| Base | `python:3.12-slim` |
| Software in the image | bash, coreutils, findutils, grep, ripgrep, sed, gawk, jq, git, curl, gcc/g++, LibreOffice, Node + npm, poppler-utils, tesseract-ocr, pandoc (pinned version); Python packages for the parsers and skills (defusedxml, diff-match-patch, docxtpl, lxml, markitdown, pdfplumber, pandas, python-docx, openpyxl, python-pptx, …); the `parse-doc` command |
| Isolation | `--network=none`, `--cap-drop=ALL`, `--security-opt=no-new-privileges` |
| Limits | 2 CPUs, 2 GB memory, 256 processes |
| Mounts | workspace rw → `/workspace`, documents **ro** → `/workspace/documents`, output rw → `/workspace/output` |
| Lifetime | one container per run, started before the first turn and removed afterwards (`podman rm -f`; the container is also started with `--rm`) |
| Timeouts | bash 60 s (`--shell-timeout`); document parsing 120 s |

**No network** applies to the agent's commands only. Model calls go from the host.

---

## 7. Grading

Grading runs after the agent finishes and is separate from the harness (`python -m lab_core.evaluation.run_eval`).

1. **Find the deliverables.** For each expected filename, the grader looks in `output/` for:
   1. the exact name;
   2. otherwise, the only file with the same extension;
   3. otherwise, the file whose name shares the most words with the expected name;
   4. otherwise, a match picked by an LLM (`claude-sonnet-4-6`, or a matcher supplied by the caller).

   Files named `output.*` are skipped.
2. **Make each file judge-readable**, with the same parsers as `read`:
   - .docx through pandoc, with tracked changes **accepted** and Word margin comments appended;
   - .xlsx through pandas;
   - .pptx through markitdown;
   - .pdf through pdfplumber.

   A missing file appears to the judge as `(File not found: <name>)`.
3. **One judge call per criterion**, using `lab_core/evaluation/prompts/rubric_criterion.txt`. The call contains:
   - the task **title**;
   - only **that criterion's deliverables**;
   - the criterion title;
   - its `match_criteria`.

   The judge returns JSON `{"reasoning", "verdict": "pass"|"fail"}`, with up to 64,000 output tokens. Criteria are judged in parallel (6 by default).
4. **Score:** a task scores `1.0` if **every** criterion passes, else `0.0`. LAB also reports the fraction of criteria passed.
5. **Standard profile:** two judges, `claude-sonnet-4-6` and `gpt-5.5` (`lab-standard-dual-v1`). Each judge grades every criterion; the reported all-pass rate is the mean of the two judges' all-pass results (0, 0.5 or 1 per run). One or two custom judges can be chosen instead.

What this means for a harness:
- **Only `/workspace/output` counts.** The judge never sees anything else: the final assistant text, the `finish` summary, the transcript, or scratch files.
- **Use the filename the instructions ask for.** Matching is lenient, but the exact name is the only certain hit.
- **Binary deliverables must open.** The judge reads them with the same parsers, so a broken .docx is graded as an error string.

---

## 8. What a LAB run records

| File | Contents |
|---|---|
| `config.json` | Model, task, max turns, temperature, shell timeout, reasoning effort, skills, image, finish setting. |
| `transcript.jsonl` | One line per assistant turn (text, tool calls, tokens, finish/stop reasons, requested and returned model), and one per tool result (name, arguments, full result). |
| `metrics.json` | Turns, tokens, wall clock, `finish_reason`, `finish_summary`, documents read and skipped, and counts of bash/glob/grep calls, writes and edits. |
| `output/`, `workspace/` | Deliverables and scratch files. |
| `scores*.json` | Written by the grader. |

---

## 9. Checklist: adopting the LAB base harness

To be **LAB-faithful**, meaning your numbers can be compared with LAB's, your harness must:

**Inputs**
- [ ] Send `system_prompt.md` + finish note + the three full `SKILL.md` files as the system message, exactly as described in section 3.2 (same text, order and headings).
- [ ] Send `task.json["instructions"]` verbatim as the first and only user message.
- [ ] Never expose `task.json`, the criteria or the deliverables map to the agent.

**Workspace and sandbox**
- [ ] Provide `/workspace` (rw), `/workspace/documents` (**ro**, the task's `documents/` or its `docs_dir`) and `/workspace/output` (rw), plus the three env vars.
- [ ] Copy skill scripts to `/workspace/skills/<name>/scripts/`.
- [ ] Use LAB's sandbox image, or one with the same software, with no network and the same limits (2 CPUs, 2 GB, 256 processes).

**Tools**
- [ ] Expose the seven tools with **the same names, descriptions and JSON schemas** (copy `TOOL_DEFINITIONS` and `FINISH_TOOL_DEFINITION`).
- [ ] Reproduce their behaviour, including the quirks the model adapts to:
  - `bash`: 60 s timeout, starts in `/workspace` each call, result format;
  - `read`: lookup order, parsers inside the sandbox, line slicing, no truncation;
  - `write` and `edit`: path rules;
  - `glob`: newest first, silent 100-file cap;
  - `grep`: raw-byte regex that can't see inside Office files, 250-line cap;
  - `finish`: deliverable check with at most 2 refusals.
- [ ] Return every result and every error as a string; never end the run on a tool exception.
- [ ] Run tool calls from one turn sequentially, in order.

**Loop**
- [ ] Stop on accepted `finish` (checked after that turn's results are added), on a reply without tool calls, at 200 turns, or on a provider context-overflow error. No compaction or retries.
- [ ] Keep the provider's native message history between turns. With the Responses API that includes reasoning items, which LAB's OpenAI adapter sends back as `input`.
- [ ] Use the reference model settings (temperature 0.0, reasoning effort per your protocol). Decide deliberately whether to request reasoning summaries; LAB does so only when an effort is set.

**Outputs and grading**
- [ ] Leave deliverables in `/workspace/output` under the requested filenames.
- [ ] Grade with LAB's grader (`run_eval`) or an exact copy: per-criterion calls, same prompt, same file parsing, the all-pass rule, and the judges you report.

**Things LAB doesn't have.** If you add any of these, report them as changes to the harness:
- middleware or hooks;
- context compaction;
- long-term memory;
- sub-agents;
- skill loading on demand (a `LoadSkill` tool);
- extra tools;
- retries on tool failure.

---

## 10. Worked example: our port to NexAU (`harness_lab/`)

Our evolution campaigns start from `harness_lab/`, a NexAU port of the reference harness. It shows what changes when the framework is not LAB's own loop:

| LAB | `harness_lab/` |
|---|---|
| The system prompt is assembled at run time | `systemprompt.md` is the **pre-assembled** text: preamble + finish note + the three skill manuals. |
| Tools are `TOOL_DEFINITIONS` plus `ToolExecutor` | One `tool_descriptions/<tool>.tool.yaml` (same name, description and schema) and one `tools/<tool>.py` per tool, using the same Podman sandbox. |
| Skill scripts are copied at run time | They are shipped under `workspace_seed/skills/<name>/scripts/` and copied into `/workspace` by the runner. |
| The `finish` latch | `stop_tools: [finish]`, with the same 2-refusal deliverable check. |
| 200 turns | `max_iterations: 200` |
| Context overflow = provider error | Same, plus a guard: NexAU stops 10,000 tokens below the gateway's advertised input limit. The GitHub Copilot gateway silently cut prompts that were too long instead of rejecting them, so without this guard the agent would keep running on a truncated history. |
| Grading with `run_eval` | Our adapter calls LAB's grader code with the configured judge(s). |

The rule we followed: copy every model-visible string exactly (system prompt, tool names, descriptions, schemas, result formats) and every behaviour the model can notice. Change only the plumbing.
