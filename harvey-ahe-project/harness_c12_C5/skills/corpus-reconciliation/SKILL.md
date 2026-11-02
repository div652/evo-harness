---
name: corpus-reconciliation
description: >-
  Required for repository-wide legal research that asks for all qualifying
  items, a count or breakdown, a most/least/recent/oldest item, or one proof
  document per result. Provides a candidate ledger and reconciliation protocol
  to prevent keyword-only omissions and unsupported inclusions.
---

# Corpus reconciliation

Use this procedure when the answer depends on a set or ranking across matters.
The goal is not to read every file. It is to account for every plausible matter
and fully read the decisive evidence for each plausible candidate.

## 1. Translate the request into anchored gates

Before searching, write `/workspace/review_state.md` with one row per possible
eligibility restriction:

| Gate | Exact supporting words from request | Meaning used | Evidence needed | Ambiguous? |
|---|---|---|---|---|

Cover population, time, role or practice when supported by the request, event
or status, substantive feature, ranking, and requested proof document. Apply
these rules:

- A restriction may exclude a candidate only if its row quotes or faithfully
  paraphrases user wording in context. Do not add engagement-purpose,
  client-side, principal-practice, matter-label, direct-instrument, completion,
  or current-status requirements merely because they would make proof cleaner.
- Classify population wording instead of applying a universal rule. Language
  locating evidence in the repository (for example, material "in our files")
  ordinarily tells where to search. Language framing firm credentials, naming a
  practice/team/portfolio, asking what "we" handled or closed, or identifying
  what the matters themselves are may define role or primary-matter scope.
  Engagement, opening, billing, closing, and transaction-summary records are
  relevant evidence for that boundary.
- Match the requested relationship exactly. A matter merely mentioning or
  diligencing another transaction, proceeding, issue, or instrument is not
  necessarily a matter of that type. Include incidental or secondary work only
  when the request uses an involvement, relationship, or any-capacity standard
  broad enough to cover it.
- Preserve every modifier in the request: do not broaden a gate into "related
  to," and do not narrow it into a preferred document type or proof convention.
- Keep eligibility, ranking, and proof-output duties separate. A requested
  document "evidencing" a fact need not be the instrument that created the fact
  unless the request says so.
- For genuine ambiguity, write both plausible meanings and a `boundary test`.
  Find at least one candidate included under only one meaning, read its best
  role/purpose evidence, and show whether the count or winner changes. Choose
  the meaning that best fits the request as a whole; disclose a material
  unresolved ambiguity rather than defaulting to maximal recall or precision.

If the request is singular or superlative, define both eligibility and ranking.
A large value or recent date cannot make an ineligible matter the winner.

## 2. Build a recall-first candidate register

Inventory matter folders completely. Search with multiple independent signals:
folder and filename variants, task concepts and synonyms, direct instrument
names, status/closing terms, role/practice evidence, and known entity variants.
A keyword hit creates a candidate; it does not prove inclusion. A missing hit
is not proof of exclusion.

Maintain this compact table in `review_state.md`:

| Matter | Why surfaced | Population/role evidence | Other gate evidence | Execution/status evidence | Proof file for requested claim | Unread high-signal files | Read state | Disposition/reason |
|---|---|---|---|---|---|---|---|---|

Use `unread`, `partial`, `read`, or `unreadable` for read state. Keep candidates
that arise from later or broader searches; merge them into the same register.
Do not let the first search define the universe. An `exclude` reason must name a
failed anchored gate, not merely a matter label, missing preferred file, or
lower evidentiary rank. Engagement purpose or matter identity may be used only
when the contextual population analysis in step 1 establishes that gate.

For a very large corpus, first account for every folder using cheap metadata and
opening/engagement records, then deeply review only plausible rows. Record why
a row is excluded; do not manufacture certainty where available records do not
resolve it.

## 3. Read by candidate and gate, not by isolated hit

For every plausible row, inventory that matter's files and choose evidence
separately for each gate and requested output field. There is no single
universally strongest file:

- engagement/opening, billing, closing, and transaction-summary records can
  prove a requested credentials, practice, portfolio, role, or matter-identity
  gate; they must not create one absent contextual support from step 1;
- executed/final instruments and filings ordinarily prove adopted terms and
  exact language;
- signed certificates, closing/post-closing records, filed records, executed
  collateral instruments, and direct counterparty or agency records can prove
  execution, status, and the existence of a referenced operative feature;
- purpose-built definition, covenant, issues, or transaction analyses may most
  directly answer the requested field, but must be reconciled with operative or
  status evidence rather than assumed adopted.

Match proof strength to the exact claim. When the primary instrument is absent,
specific contemporaneous executed or final records may establish that an
operative feature existed or an event occurred. They do not establish unseen
exact language or every term. Record those confidence limits; do not convert the
missing primary copy into a new eligibility gate. Conversely, an unsigned
summary, filename, draft, proposal, or generic phrase hit is only a lead unless
corroborated by execution or final-status evidence.

Preserve complementary proof. When an inventoried purpose-built analysis or
closing record directly addresses a requested field, read and disposition it
rather than citing only the operative instrument. A lower-authority source may
be the best explanation of one gate while an executed record establishes
another. Before excluding or selecting proof, resolve every listed unread high-
signal file that could change the gate or better answer the requested field.
Distinguish execution from a document labeled "execution" by checking signatures
and corroborating status records. Distinguish an operative term from a proposal
or unconsummated draft.

### Partial-read recovery

A truncated or partial result is not a completed read and cannot support a
negative finding. Before inclusion, exclusion, or ranking depends on such a
file:

1. search that file for the operative concept and synonyms, relevant headings,
   execution/status terms, defined terms, and cross-references;
2. read bounded text around every material hit and any referenced section;
3. reconcile the result with final/executed, closing/post-closing, opening, and
   purpose-built records already inventoried for that candidate; and
4. record the follow-up paths, queries, and result in the candidate row.

If bounded follow-up still cannot resolve the gate, mark it `unresolved`; never
infer absence from the visible prefix. After each read batch, update the
candidate row. Never postpone all reconciliation until drafting.

## 4. Apply gates consistently

Disposition every candidate as `include`, `exclude`, or `unresolved`, with a
source-based reason. Apply the same test to inclusions and exclusions. Keep
separate fields for concepts that can be conflated, such as transaction value
versus asset/appraisal value, cash versus total consideration, document date
versus matter opening date, and negotiated language versus adopted language.

For ranking questions, compare the proposed winner against every other eligible
row. For exhaustive questions, the final answer count must equal the number of
included rows. For "one document per item" requests, every included row must
map to a read proof file; no proof file may merely be inferred from its name.

## 5. Reconcile before drafting and before finish

Run these checks twice: once before drafting and once against the completed
answer.

- Every restrictive gate maps back to the request-gate table and contextual
  population analysis. Delete any gate based only on a preferred proof form or
  another unstated condition. Do not delete a role, practice, portfolio, or
  matter-identity gate merely because repository documents supply its proof.
- If plausible population readings yield different sets or winners, the
  boundary test is complete: at least one changed candidate's role/purpose
  evidence was read, both outcomes were compared, and the selected meaning or
  unresolved ambiguity is recorded.
- Every surfaced matter has a disposition; no positive search result was
  silently dropped.
- Every inclusion satisfies every anchored gate with read evidence. Every
  exclusion names a failed anchored gate and applies the same test; absence of a
  preferred primary instrument is not itself a failure when claim-sufficient
  corroborated evidence exists.
- Compare the candidate set before and after final reconciliation. For every
  removed row, reopen its best supporting source and verify the removal reason;
  do not allow a stricter proof test for exclusions than for inclusions.
- Every requested row, total, denominator, and ranking ties back to the register.
- Every cited supporting document was opened and is the strongest proof for the
  requested claim; complementary purpose-built or status proof is not discarded
  merely because an operative instrument also exists.
- No consequential decision relies on an unresolved partial read or an unread
  high-signal file.
- The number of items affirmatively presented as qualifying matches the user's
  requested cardinality. For a singular or superlative answer, keep eligible
  comparators in scratch unless comparison discussion was requested; do not
  label a runner-up as an additional answer.
- Material names, dates, amounts, roles, status, and quotations are rechecked
  against source files. Exact quotations and detailed terms require a source
  that contains them; corroborated existence evidence supports only that more
  limited claim.

When full resolution is impossible within the available evidence or budget,
state the exact unresolved scope instead of presenting a heuristic sample as a
complete set. Keep the scratch ledger outside `/workspace/output`; only the
requested deliverables belong in output.
