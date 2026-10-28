# Brief: round-2 annotation of stage-harness training runs (campaign 29)

Folder: `/home/agarwaldi/AHE_Harvey_cao/harvey-ahe-project/analysis/stages-train-c29/`.
Follow `../stages-train/BRIEF.md` (rules 1-7, first-error definition, output
format) and `../stages-train/BRIEF_PARALLEL.md` (frozen vocabulary, `NEW:`
names, proposals file), with the differences below. Use only this folder,
`../stages-train/` (round-1 catalog, for reference) and the raw traces named
in the log headers. Never open anything under `/home/agarwaldi/archive/` or
other `analysis/` files: they hold test-set material.

## What is different in these runs
The agent ran under the stage-protocol harness: before any work it called
`stage_start(stage, goal)` and closed each stage with
`stage_end(goal_reached, summary)`. `stage_end` returned an independent
critic's review; the log shows it as `stage_end result: ... Independent
reviewer: goal reached = yes|partly|no | Reviewer flags: ... | Reviewer
recommendation: ...`. Reopened stages show "attempt N".

## Rules added for this round
1. Segmentation: use the agent's declared stages as the default boundaries.
   A stage runs from its `stage_start` event to its `stage_end` event
   (inclusive). `finish` is its own stage "Finish the run".
2. Labels: keep the declared stage name when it correctly describes what the
   agent did inside it (check against taxonomy.md definitions). If it does
   not, label the span with the correct taxonomy stage and put
   `declared: <name>` at the start of the note. If the work inside one
   declared span clearly had two intents, you may split it at a tool-call
   boundary. If no taxonomy stage fits, use a `NEW:` stage (proposals file).
3. Every failing run gets `first_error` (and `other_errors`) as before, with
   one extra field `critic`: 
   - `flagged-ignored`: the stage_end review of that stage (or the next
     review before the error became final) named this problem and the agent
     moved on without fixing it;
   - `flagged-fixed-partly`: flagged, the agent reopened or acted, but the
     error remained;
   - `not-flagged`: reviews in reach did not name it;
   - `no-review`: the run ended (e.g. context overflow) before a review.
4. Hindsight values, error kinds and tags: reuse round-1 names in
   taxonomy.md; add `NEW:` names only when none fits, and list them in
   `proposals/batch-<N>.md` with a reason.
5. `divergence` (per task) as before. For mixed tasks, name the stage where
   passing and failing runs split and whether the critic's review at that
   stage differed.

Validate with `python3 check.py <your tasks>`; the only errors allowed are
about your `NEW:` names. Write only `annotations/<your tasks>.json/.md` and
`proposals/batch-<N>.md`. Use a private scratch folder if you need scripts
(`/tmp/c29-batch-<N>/`), never a shared one.
