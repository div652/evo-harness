# Proposals: batch 2 (round 2, campaign 29)

Tasks: 011 028 032 057 104 126 155 198 (24 runs: 4 pass, 20 fail).

## NEW names

None. Every stage, tag, hindsight value and error kind is from the frozen
taxonomy.md.

| kind | name | definition | example | why no existing name fits |
|---|---|---|---|---|
| (none) | | | | |

## Issues

1. **Declared names that did not fit (relabelled, `declared:` in the note).**
   - "List files in the document store (attempt 2/3)" was the declared name for
     a folder count or folder-name listing in most runs → labelled "List matter
     folders" (e.g. 104_T1 [8]-[13], 011_T0 [8]-[13]).
   - "Read a chosen matter's documents in depth" was declared for reads that
     compared several candidates → "Screen candidate matters by reading
     documents" (104_T0 [31]-[41], 155_T0 [52]-[87], 011_T1 [55]-[83]).
   - "Search within a candidate matter's files" was declared for store-wide
     scripts → "Scan document text with an extraction script" (104_T0
     [42]-[45], 032_T0 [57]-[62], 198_T0 [66]-[73]).
   - "Screen candidate matters" (attempts 2-4) was declared for snippet scripts
     over named agreements → "Search within a candidate matter's files"
     (155_T2 [77]-[90]).
   - Declared spans with two intents were split at a tool-call boundary
     (e.g. 198_T0 [28]-[46] into file-name search / scan / screen; 126_T2
     [34]-[86] into six rows).
2. **Calls refused by the stage protocol.** A call sent while no stage was
   open ("No stage is open") was put in the stage that the agent then
   reopened. A refused `stage_start` for writing (previous stage still open)
   stays in the open stage. Both carry `tool error`. Stage-check warnings
   ("this call looks like ...") were not refusals and are untagged.
3. **Critic values.** Nearly every review repeats "about 60 surfaced matters
   never opened". I counted that boilerplate as a (generic) flag only for
   surfaced-not-opened and under-inclusion errors. For proof-document errors
   I counted only flags about unopened or unverified source documents. Each
   error has a `critic_note` that starts with "(generic flag)" or
   "(specific flag)" when its value is flagged-*. Specific flags were ignored
   in 104_T2, 198_T0, 057_T1, 011_T0/T1, 126_T0/T1 and 155_T0. The one
   specific flag that was acted on (198_T1) only led to relabelling.
4. **Mixed write-stage outcomes.** Most failing answers both omit needed
   matters and assert extra ones. Following the batch-2 precedent (206_T1),
   such write stages get "answer over-inclusive" and the omission sits in
   first_error/other_errors. A combined hindsight value (omits and adds)
   would make this visible at the stage level.
5. **Kind boundaries used.**
   - Proof-document failures where the required document appeared in a
     store-wide hit list or file-name search (not a listing of that matter)
     were classed as listed-document-not-opened (011_T0, 011_T2). This
     stretches the definition, which says "a listing of a matter it was
     working on".
   - A required document that was read but not cited (011_T0, a closing
     memo) was classed as missing-identifier.
   - A standalone agreement cited but called unexecuted (155_T1) was classed
     as misstated-facts.
   - Range scans that timed out and left partial hit files the agent treated
     as complete (126_T0) were classed as search-miss. Hit files that were
     only viewed through `head` and a threshold filter (011_T1) were classed
     as over-narrow-filter.
6. **Patterns with no tag.**
   - Sibling matters of one client (adjacent numbers) listed in place of the
     needed one (126 all runs, 155_T0).
   - Background `&` jobs used to avoid the 60 s limit (126_T2, 155_T1).
   - Writing or checking at `response.md` while the deliverable is
     `output/response.md`. This happens often and is tagged only
     `file not found` when a script failed.
7. **Context overflow from the first store-wide script** (104_T1 about 4.7M
   characters, 198_T2 about 5.4M characters). In 104_T1 the review just
   before had recommended a store-wide search "without a cap".
