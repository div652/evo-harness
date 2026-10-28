---
name: candidate-dossier-workflow
description: >-
  Use for corpus-wide, all/any, comparative, ranking, latest/earliest, or
  superlative matter research. Provides a bounded candidate ledger, source-role
  selection, one-candidate-at-a-time reading, and pre-draft set reconciliation.
---

# Candidate dossier workflow

Use this procedure when the answer depends on finding or comparing candidates
across matters. Do not use it for a task confined to explicitly named files.
The goal is a complete, supportable answer set, not maximum document volume.

## 1. Translate the request into gates

Before searching, write a compact scratch note containing:

- the requested output cardinality: one selected answer, top N, or every
  qualifying matter;
- each required qualifier as a separate conjunctive gate;
- the governing date/status rule and tie rule;
- the evidence roles needed to prove a row, such as authoritative primary
  instrument, execution or current-status source, issue-specific proof, and any
  requested identifier or document name.

Do not add unstated scope restrictions. Do not collapse multiple qualifiers into
one broad label. A keyword hit opens a candidate; it never proves a gate.

## 2. Create the ledger before deep reads

After the direct matter-directory census and the first bounded semantic or
filename search, immediately create `/workspace/candidate-ledger.md`. Add every
plausible distinct matter cluster surfaced so far before running another broad
search or choosing a preferred read batch.

Use one row per candidate with these fields:

```text
candidate | why surfaced | gate 1 | gate 2 | other gates | primary path |
status/proof path | unread high-signal paths | disposition | confidence
```

Allowed dispositions are `unresolved`, `include`, and `exclude: reason`.
Start every row as `unresolved`. Keep false positives and exclusions visible;
do not delete rows. Bind every fact to the explicit source path returned by the
read tool.

## 3. Build a bounded dossier queue

For each unresolved row, enumerate that matter locally and choose documents by
evidence role rather than lexicographic order or convenience:

1. final, executed, signed, filed, operative, or current primary document;
2. closing, consummation, dismissal, certificate, final checklist, or current
   status evidence;
3. the issue-specific memorandum, pleading, schedule, disclosure, or proof
   document requested by the user;
4. contradictory, superseding, later-dated, or amendment evidence.

Prefer authoritative and later sources over drafts, preliminary summaries, and
ancillary documents. If a surfaced high-signal path is not read, record why it
cannot affect a requested gate. A stale or future-tense status source cannot
close a row while later closing/disposition evidence remains unread.

## 4. Resolve candidates, not batches

Work on one candidate at a time. Request at most two or three long documents in
one assistant turn. After each turn, update the ledger before reading more.

For every read result:

- `status: deferred` means no evidence was obtained. Retry that exact path on a
  later turn.
- `complete: false` means the document remains open. Follow `next_offset` until
  the dispositive section is reached, or record a source-grounded reason the
  remainder cannot change any gate.
- Never classify from a document head, filename, failed search, or absent term
  in an unread range.
- Keep title-page identity, parties, date, version/status, decisive finding,
  and source path together in the same row.

Close a row only after every requested gate has an explicit `yes`, `no`, or
`unknown` supported by the right evidence role. `Unknown` remains unresolved;
it is not negative evidence.

## 5. Run recall and precision challenges

Before drafting, freeze broad discovery and perform these checks against the
ledger:

### Recall challenge

- Did each distinct surfaced matter cluster receive a row?
- Did every plausible row receive matter-local enumeration and source review?
- Are any deferred reads, relevant `next_offset` values, or unread high-signal
  paths still capable of changing a disposition?
- Are generically named files, alternate pleadings, amendments, and final-status
  files represented where the requested concept could be proved there?

### Precision challenge

- Does every included row independently satisfy every user-supplied qualifier?
- Is each inclusion based on the authoritative/current source rather than a
  draft, proposal, adjacent concept, or stale status?
- Did the analysis invent a transaction-type, practice-area, execution, or
  status gate not stated by the user?
- Do excluded rows have a source-supported disqualifier rather than an inference
  from silence?

Reopen only the exact path or range needed to repair a failed challenge.

## 6. Reconcile evidence roles and answer cardinality

For each included row, ensure the ledger names every distinct evidence role the
user asks to identify. Overlapping sources are not interchangeable: a primary
instrument, current status memo, pleading, closing proof, or disclosure source
may each satisfy a different requirement.

Then compute the requested final set from the closed ledger:

- rerun ranking and aggregation after the final row changes;
- preserve all ties required by the request;
- compare the count of included rows with the count of answer rows;
- for a singular latest, earliest, largest, or selected answer, keep comparator
  details in the internal ledger and state only the selected answer positively
  unless comparisons were requested.

## 7. Draft and verify

Draft from the ledger, not from memory of tool output. Carry requested matter
identifiers, exact proof-document names or paths, dates, and gate findings into
the requested output. After drafting, compare each instruction requirement and
each included ledger row to a specific location in the deliverable.

Before finish, confirm:

- no unresolved row can change the answer set;
- no included row lacks evidence for a required gate or evidence role;
- no supported included row is absent from an all-matters answer;
- singular or top-N cardinality is respected;
- every requested source or identifier appears in the final extracted text;
- all deliverables exist in `/workspace/output` and have been previewed.

Stop researching once these checks pass. Do not resume broad reads after the
complete deliverable has been written and verified.
