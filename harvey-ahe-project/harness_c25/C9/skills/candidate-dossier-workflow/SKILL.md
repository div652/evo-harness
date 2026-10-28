---
name: candidate-dossier-workflow
description: >-
  Use for corpus-wide, all/any, comparative, ranking, latest/earliest, or
  superlative matter research. Provides an auditable candidate ledger,
  source-role review, bounded dossier reading, and answer-set reconciliation.
---

# Candidate dossier workflow

Use this procedure when the answer depends on finding or comparing candidates
across matters. Do not use it for a task confined to explicitly named files.
The goal is a complete, supportable answer set, not maximum document volume.

## 1. Translate the request into gates

Before searching, write a compact scratch note containing:

- requested output cardinality: one selected answer, top N, or every qualifying
  matter;
- each user-supplied qualifier as a separate conjunctive gate;
- governing date/status and tie rules, if the user supplied them;
- evidence roles needed to prove each gate, such as authoritative primary
  instrument, execution or current-status source, issue-specific proof, and any
  requested identifier or document name.

Do not add a transaction type, status, date, practice area, or other restriction
that the user did not state. Evidence quality and legal qualification are
separate: preferring a final source does not create an executed-only gate. A
keyword hit opens a candidate; it never proves a gate.

## 2. Maintain one auditable candidate table

After the direct matter-directory census and first bounded semantic or filename
search, create the scratch file at the exact absolute path
`/workspace/candidate-ledger.md`. Do not use a relative path, because relative
`write` calls create graded output files.

For each corpus-rooted `glob` or `grep` whose returned roots are legally
plausible candidate matters requiring candidate-local source review, set
`candidate_discovery: true` on every page of that search. This flag creates a
review obligation; it does not prove a gate. Keep it false for the neutral
matter-directory census, an all-files inventory, local matter inventory, and
searches expected to contain mostly incidental references. Never prepopulate the
candidate table with every census root merely to satisfy reconciliation. The
framework maintains a set difference between designated roots and ledger rows.

Use a markdown pipe table with one separate row per legally plausible matter.
Begin the `candidate` cell with the exact matter-root directory returned by the
designated search so reconciliation is deterministic:

```text
candidate | why surfaced | gate findings | decisive source paths |
unread/action | qualification | output status
```

Use these state values consistently:

- `qualification`: `unresolved`, `qualifies`, or `exclude: <source-grounded
  failed gate>`;
- `output status`: `pending`, `report`, or `comparator`.

Start each new row as `unresolved` and `pending`. `Unknown`, `TBD`, unread, a
failed search, and absence of reviewed proof all remain unresolved; none is a
negative finding. Keep false positives and exclusions visible rather than
deleting them. Never combine plausible matters into an `other matters`, range,
or similar aggregate row.

After every page marked `candidate_discovery: true`, merge each returned matter
root into this table before another broad search or preferred read batch. Every
designated root must receive a matter-local inventory and at least one completed
candidate-local source read before `qualifies` or `exclude`; a filename alone
cannot close it. If a search returns mostly incidental references, keep that
search undesignated and use its paths to form a narrower designated search whose
roots are genuinely plausible. The framework reminder reports missing
designated roots, broad discovery that advanced without changed ledger content,
and rows that still contain open-state markers.

## 3. Build a bounded, source-bound dossier queue

For each unresolved row, enumerate that matter locally and choose documents by
evidence role rather than lexicographic order or convenience:

1. final, executed, signed, filed, operative, or current primary document;
2. closing, consummation, dismissal, certificate, final checklist, or current
   status evidence when status is a requested gate;
3. issue-specific memorandum, pleading, schedule, disclosure, or proof source;
4. contradictory, superseding, later-dated, or amendment evidence.

Record exact paths in the same row before reading. Prefer authoritative and
later sources over drafts, preliminary summaries, and ancillary documents. If a
surfaced high-signal path is not read, put the exact remaining action in
`unread/action`; do not rationalize it away from memory. A stale or future-tense
status source cannot resolve a status gate while later disposition evidence is
known but unread.

## 4. Resolve rows, not batches

Work on one candidate at a time. Request at most two or three long documents in
one assistant turn. After each turn, update that candidate's row before opening
another dossier.

For every read result:

- `status: deferred` means no evidence was obtained. Keep the exact path in
  `unread/action` and retry it on a later turn.
- `complete: false` means the source remains open. Follow `next_offset` until
  the dispositive section is reached, or record a source-grounded reason why
  the remainder cannot change a user-supplied gate.
- Never classify from a filename, document head, raw XML/search snippet, failed
  search, or absent term in an unread range. Such observations can open rows,
  not close them.
- Keep candidate identity, parties, date, version/status, decisive finding, and
  source path together in the same row. Bind facts to the `source` header, not
  batched request order.

Set `qualification` to `qualifies` only after every user gate has a supported
yes. Set `exclude` only when an authoritative candidate-local source supports a
no on a user gate. Anything else stays unresolved.

## 5. Challenge recall and precision

Before drafting, freeze broad discovery and audit the table.

### Recall

- Did each legally plausible cluster from every discovery pass receive its own
  row?
- Did each row receive matter-local enumeration and source review?
- Can a deferred range, unread high-signal path, amendment, generic filename,
  alternate pleading, or final-status source still change a disposition?
- Did a narrow extension, capitalization, filename, or issue-term search return
  zero or time out? If so, run one independent recall route across supported
  formats or bounded matter groups before treating discovery as complete.
- For prevalence or denominator questions, did you first close the requested
  population independently and then test every member for the issue, rather
  than defining the population from issue-term hits?

### Precision

- Does every `qualifies` row independently satisfy every user gate?
- Does each finding come from the appropriate candidate-local evidence role,
  not a nearby matter, wrong metric, draft, adjacent concept, or stale status?
- Did the analysis invent an unstated inclusion gate?
- Does each exclusion identify an actual failed gate and decisive source rather
  than silence or lack of review?

Reopen only the exact path or range needed to repair a failed challenge. Update
the table immediately after the repair.

## 6. Run one independent closure audit

After your own recall and precision checks, but before drafting, call
`sub-agent-candidate-reviewer` exactly once. Its message must contain:

- the requested cardinality and each user-supplied gate;
- the evidence roles needed to prove those gates;
- the exact ledger path `/workspace/candidate-ledger.md`;
- the discovery routes completed, including important no-matches or timeouts;
- a request to identify omitted plausible roots, unsupported exclusions or
  inclusions, incomplete proof roles, and cardinality leakage.

The reviewer is read-only and returns discrepancies, not legal decisions. For
each returned root, independently open the cited candidate-local source or
needed range. Add or reopen the row when the source can change a gate; otherwise
record the candidate-local source and failed gate supporting closure. Do not
close a discrepancy from the reviewer's prose alone. Do not call the reviewer
before a ledger exists, recall it repeatedly, or delegate drafting. This step is
only for corpus-wide selection; skip it for explicitly named-file work.

## 7. Compute qualification and output sets separately

Qualification answers whether a row satisfies the user predicates. Output
status answers whether that row belongs in the requested external answer.
Keeping these separate prevents comparator leakage.

- For an all-matters request, mark every `qualifies` row as `report`.
- For a singular latest, earliest, largest, or selected answer, rank all
  qualifying rows, mark only the winner (and required ties) `report`, and mark
  other qualifying rows `comparator`.
- For top N, mark exactly N rows plus required ties `report`; other qualifying
  rows are comparators.
- Rerun ranking and aggregation after the last row changes. Use source dates and
  requested metrics, never folder order, identifiers, or another matter's
  value.

Comparator details remain internal unless the user requested the comparison.
Do not describe a comparator positively in the deliverable as another external
answer.

## 8. Draft and verify

Draft only from rows marked `report`, not from memory of tool output. Carry the
requested identifiers, exact proof-document names or paths, dates, and gate
findings into the deliverable. A document-package request needs a file-level
manifest: preserve every selected-matter file as an individual required item,
not merely one path per broad evidence role.

Before finish, confirm:

- no row contains unresolved, unknown, pending, TBD, or an answer-changing
  unread action;
- every broad discovery pass was reconciled into changed ledger content;
- every reviewer discrepancy was independently checked and resolved in the
  ledger;
- every `report` row has evidence for each gate and requested evidence role;
- every supported `report` row appears in an all-matters answer;
- only `report` rows appear as positive answers for singular or top-N requests;
- every requested source, identifier, section, and file-level item appears in
  the final extracted text or package;
- all deliverables exist in `/workspace/output` and have been previewed.

Stop researching once these checks pass. Do not resume broad reads after the
complete deliverable has been written and verified.
