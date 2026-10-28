# Brief: round-3 annotation of round-2 stage-harness training runs (campaign 30)

Folder: `/home/agarwaldi/AHE_Harvey_cao/harvey-ahe-project/analysis/stages-train-c30/`.
Follow `../stages-train-c29/BRIEF.md` (round 2), which points to
`../stages-train/BRIEF.md` and `../stages-train/BRIEF_PARALLEL.md`; read all
three. Differences for this round are below. Use only this folder,
`../stages-train/`, `../stages-train-c29/` (earlier rounds, for reference)
and the raw traces named in log headers. Never open anything under
`/home/agarwaldi/archive/` or other `analysis/` files (test-set material).

## What is different in these runs (harness_stage_r2)
- `stage_start` results may contain "Check the label: runs often declared
  this stage while doing other work ... that is the stage X: close this
  stage and start that one" (shown in the log).
- The critic was told to flag a failure only with specific evidence, and not
  to recommend actions that lead into another stage's known failures.

## Rules (in addition to round 2)
1. Segmentation and labels: as round 2 (declared spans by default; relabel
   with `declared: <name>` at the start of the note when wrong; split
   two-intent spans; `NEW:` stage only if nothing fits).
2. Every error (first and later) gets `critic` and `critic_note`:
   - `critic` one of: flagged-ignored, flagged-fixed-partly, not-flagged,
     no-review, review-endorsed (definitions in taxonomy.md, section
     "Critic values");
   - `critic_note` starts with "(specific flag)" when the review named the
     matter, document or exact cause, "(generic flag)" for stock warnings,
     and is a short reason otherwise.
3. Calls refused by the stage protocol: tag `tool error` on the stage they
   are placed in (a refused stage_start "still open" stays in the open
   stage; a call refused with "No stage is open" goes to the next stage).
4. New for this round, per stage: add `"label_check": "followed" |
   "ignored" | "none"` when the stage_start result carried a "Check the
   label" note — `followed` if the agent closed the stage and started the
   suggested one before doing the work it describes, `ignored` if it did that
   work under the declared label, `none` if no note was shown or it did not
   apply.
5. `divergence` (per task) as before; for mixed tasks name the stage where
   passing and failing runs split and whether the critic's review there
   differed.

Validate with `python3 check.py <your tasks>`; only errors about your `NEW:`
names may remain. Write only `annotations/<your tasks>.json/.md` and
`proposals/batch-<N>.md`. Use a private scratch folder
(`/tmp/c30-batch-<N>/`), never a shared one.
