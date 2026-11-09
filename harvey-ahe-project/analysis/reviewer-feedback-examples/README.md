# Reviewer feedback examples (stage harness, training runs only)

Five runs from the stage harness's training campaigns, rendered in full. They show what the end-of-stage reviewer told the agent at the moment of its first error, and what the agent did next. Every run is on a training task; the annotations come from the catalogs in `../stages-train-c29`, `-c30` and `-c31`.

| File | Scenario | Round | Outcome |
|---|---|---|---|
| `1-specific-flag-ignored_c30_063_T2.md` | Reviewer named the exact dropped matter and why; agent moved on to its own picks | r2 | fail, 8/11 |
| `2-generic-warning-ignored_c30_052_T0.md` | Reviewer warned "about 55 others unopened" without naming the needed ones; agent wrote next | r2 | fail, 11/23 |
| `3-flag-partly-fixed_c31_072_T1.md` | Reviewer named three weak inclusions; agent added a verification stage, dropped a different weak one, kept the three | r3 | fail, 3/4 |
| `4-review-followed-pass_c29_056_T0.md` | Reviewer flagged the capped listing and named unlisted candidates; agent reopened with goals that copy the recommendation | r1 | **pass, 2/2** |
| `4b-same-task-flag-ignored-fail_c29_056_T1.md` | Same task as 4: reviewer twice flagged the wrong headline matter; agent only re-read its file | r1 | fail, 0/2 |

Each file starts with a short header giving the task, the needed matters, the annotated first error, the key review (quoted) and what the agent did next, with step numbers and `[n]` event indices to jump to. The full trajectory follows. Rendered with `scripts/stage/timeline.py`.

The agent's own reasoning is not available: these campaigns ran before the reasoning-summary fix (campaign 34).
