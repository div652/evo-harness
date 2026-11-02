# Brief: round-4 annotation of round-3 stage-harness training runs (campaign 31)

Folder: `/home/agarwaldi/AHE_Harvey_cao/harvey-ahe-project/analysis/stages-train-c31/`.
Follow `../stages-train-c30/BRIEF.md` (round 3), which points to the round-2
and round-1 briefs; read all of them. Differences for this round are below.
Use only this folder, the earlier catalogs `../stages-train*/` (for
reference) and the raw traces named in log headers. Never open anything under
`/home/agarwaldi/archive/` or other `analysis/` files (test-set material).

## What is different in these runs (harness_stage_r3)
- `stage_start` may show "Policy for this stage" rules and "Check the label"
  notes (only the latter appears in the logs).
- `stage_end` results may contain: "Label: these calls looked like '<X>'
  work …" (a classifier judged the calls to belong to stage X), "Reviewer
  suggests a new step: '<name>' …", "This stage has been opened N times …",
  and "Matters that appeared in your search results but none of whose
  documents you have opened or listed: …". These lines are in the logs.
- The agent often declared its own stages: `stage_start(stage="new",
  new_stage_name=...)`, shown in logs as stage "new".

## Rules (in addition to round 3)
1. Segmentation, labels, `critic`, `critic_note`, `tool error` tag: as in
   round 3.
2. `label_check` per stage: as in round 3, and also count the end-of-stage
   "Label: these calls looked like '<X>'" note: `followed` if the agent's next
   stage for that kind of work was declared X, `ignored` if it kept the old
   label for the same work.
3. Agent-defined stages (declared "new"): add the field
   `"agent_new": "<the agent's new_stage_name>"` to that stage. Then:
   - if an existing taxonomy stage describes what its calls do, label the
     span with that stage and start the note with
     `declared: new: <agent's name>`;
   - if none fits, label it `NEW: <descriptive, generic, benchmark-level
     name of what the calls do>` and list it in your proposals file with the
     agent's name, the runs where it occurs and their outcomes. Name by
     function, never by the agent's wording or task content, so the same
     step in different runs gets the same NEW name.
4. Error kinds, hindsight values, tags: reuse round-3 names; `NEW:` only if
   nothing fits (proposals file).
5. `divergence`: as before; for mixed tasks name the split stage and whether
   the critic's review there differed, and whether a policy rule, label note
   or new stage played a role.

Validate with `python3 check.py <your tasks>`; only errors about `NEW:` names
may remain. Write only `annotations/<your tasks>.json/.md` and
`proposals/batch-<N>.md`. Use a private scratch folder
(`/tmp/c31-batch-<N>/`), never a shared one.
