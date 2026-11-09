# Feedback replay: does the way feedback is presented change what the agent does next?

A reusable dataset and harness for replaying **one model step** right after the stage reviewer's feedback, with that feedback changed in some way.

Training runs only: stage harness r2 and r3 (campaigns 30 and 31), 80 tasks × 3 trials each, so 480 runs. Nothing from validation or test.

## The dataset: `dataset/items.jsonl`

One line per run (480 lines). Main fields:

| Field | Meaning |
|---|---|
| `id` | `r2-063-T2` (round, task, trial) |
| `run_all_pass`, `n_reviews` | run outcome; number of reviews in the run |
| `selection` | the annotator model's choice of the run's **first strict-feedback review**: `review_idx`, `strict_item` (the feedback), `implied_action` |
| `has_strict` | false in the 3 runs with no strict review |
| `review_idx`, `stage_end_idx`, `stage_end_call_id` | trace event of the review, and of its `stage_end` call |
| `timeline_step` | tool-call number of that `stage_end`, the same numbering as `scripts/stage/timeline.py` and `../reviewer-feedback-examples/` |
| `model_call` | the model call that **received** the review (`call-NNNN` in the run's `runtime/.../model_calls/`): its request ends with the review |
| `review_no`, `stage_label`, `verdict`, `review_text` | position of the review in the run, its stage, the reviewer's verdict, the full review |
| `request_copy`, `request_sha256` | gzipped copy of that exact request (`dataset/requests/<id>.request.json.gz`) and its hash; replays check the hash |
| `original_next` | what the model actually did next in the recorded run (its tool calls or message) |
| `original_followed` | annotator judgement of whether the agent carried out the implied action over its next two stages: `yes` / `partly` / `no` |
| `first_error_flag` | for the 237 failing runs whose first error the reviewer flagged (from `../feedback-uptake`): the same fields for **that** review (`review_idx`, `timeline_step`, `model_call`, `review_text`, `request_copy`, `request_sha256`, `original_next`) plus the flag quote, error kind and reviewer outcome |
| `is_first_error_flag` | whether the first strict review is also the first-error flag (only 5 runs) |

**Two targets:**
- **`first_strict`** (477 items): mostly early reviews. The median tool-call step is 6, and half are the run's first review, about the capped file listing or the file-name search. The agent already followed most of these (313 yes, 146 partly, 18 no).
- **`first_error`** (237 items): the review that flagged the run's first error. The median step is 35, and the agent didn't act on it in the recorded run.

**"Strict feedback"** means a flag or recommendation that names a concrete problem with specific evidence (a matter, document, call, filter or exact cause) *and* clearly implies a corrective action. The annotator model is `claude-opus-5-5`, at temperature 0.

`dataset/requests/` is about 84 MB and is not in git. The requests are also in the campaign folders (`model_call_dir`); `build_dataset.py` recreates the copies.

## Replaying a variant

1. Add a function to `VARIANTS` in `replay.py`. It maps the review text to the new text. The current ones are `control` (unchanged) and `wrapped` (`[VERIFIER FEEDBACK]\n…\n[\VERIFIER FEEDBACK]`).
2. Replay:
   ```bash
   python3 analysis/feedback-replay/replay.py --target first_error --variant <name> --samples 2
   ```
   It resends the exact recorded request with only the review text changed, plus `reasoning: {summary: auto}` (pass `--no-summaries` to send it without). The model is `gpt-5.6-luna` via CAO, using the run's own prompt-cache key. The result is the model's next step and its reasoning summary, under `replays/<target>/<variant>/`.
3. Judge it blind:
   ```bash
   python3 analysis/feedback-replay/judge.py --target first_error --arm <name>
   ```
   An annotator sees the feedback and the next step only, not the arm, and labels whether the step commits to acting on the feedback (`yes` / `partly` / `no`).
4. Compare:
   ```bash
   python3 analysis/feedback-replay/summarize.py --target first_error --arms original control <name>
   ```
   This gives a paired comparison over items, with a bootstrap confidence interval.

Always compare against `control`. The model's next step varies from sample to sample, so a single replay can differ from the recorded run even with no change at all.

`run_all.sh` runs the whole `control` vs `wrapped` experiment for both targets.

**Limits:**
- One replayed step usually yields only the agent's next stage goal. It measures what the agent *commits to*, not what it then does.
- Changing the transcript mid-run is not the same as running the harness with the change from the start: earlier reviews in the replayed context are unchanged.
