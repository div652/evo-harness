# Addendum for parallel batches (3-13): tasks where all three runs failed

Several batches run at the same time, so `taxonomy.md`, `changelog.md` and
`check.py` are FROZEN: read them, never edit them.

- Use existing stages, tags, hindsight values and error kinds wherever they
  fit (read their definitions and the Issues section of taxonomy.md).
- If none fits, invent a descriptive name and use it prefixed with `NEW: `
  (e.g. `"stage": "NEW: Re-read the request"`, `"kind": "NEW: some-kind"`).
- Record every NEW name in `proposals/batch-<N>.md` as a table row:
  kind (stage/tag/hindsight/error kind) | name | definition | example
  `<task>_T<k> [a]-[b]` | why no existing name fits. Add an "Issues" list.
- Reuse the same NEW name consistently within your batch.
- No stage or behaviour is judged good or bad a priori; describe what
  happened. Every failing run needs first_error.
- `check.py` will reject NEW names (they are not in taxonomy.md). Run it and
  confirm that the only errors it reports are about your NEW names.
- `divergence`: whether the three runs failed the same way, and at which
  stage.
