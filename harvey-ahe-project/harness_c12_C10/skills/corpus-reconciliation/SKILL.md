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
- Match the requested relationship exactly. For each plausible candidate label
  the relationship `direct`, `responsive`, `peripheral`, or `uncertain`, and cite
  the source proving that relationship. `Direct` means the engagement performs
  the requested transaction, role, event, or legal work; `responsive` means the
  engagement itself acts in response to it where the request includes such a
  capacity. A mention, diligence reference, commercial effect, timing concern,
  or substantive advice about another party's activity is `peripheral` unless
  the request expressly makes that relationship sufficient. Broad phrases such
  as "involved" or "in any capacity" remove side restrictions; they do not turn
  relevance to a separate engagement into participation in the requested class.
  Treat an uncommon but plausible capacity as `uncertain` and run the boundary
  test rather than forcing it into either category.
- Preserve every modifier in the request: do not broaden a gate into "related
  to," and do not narrow it into a preferred document type or proof convention.
- Identify the **requested object** before assigning lifecycle significance: is
  the user asking for matters, transactions, agreements, provisions, events,
  drafting work, or precedent documents? Transaction state and document state
  are separate evidence fields, not automatic eligibility gates. An executed
  document from a terminated transaction can still be a responsive precedent;
  a bound policy can be responsive even if its transaction did not close; and a
  draft can evidence drafting or negotiation when that is the requested object.
  Conversely, none of those facts proves a closed deal or an operative term when
  that is what the request actually asks for.
- Add a lifecycle restriction only when the request, read as a whole, requires
  that state for the requested object. Do not infer consummation, inception,
  current operation, original-formation counsel, or an executed-copy requirement
  from one conversational verb. Keep separate fields for transaction/event
  state, document state, and the narrower claim each source can prove.
- Test the unit of analysis named by the request. Decide whether each gate
  applies to a matter, transaction, agreement, provision, party role, or event;
  do not let a matter's purpose substitute for the requested agreement-level
  test, or a document mention substitute for the requested matter relationship.
- For genuine ambiguity, write both plausible meanings and a `boundary test`.
  Find at least one candidate included under only one meaning, read its best
  role, purpose, and status evidence, and show whether the count or winner
  changes. Choose the meaning that best fits the request as a whole and disclose
  a material unresolved ambiguity rather than silently maximizing recall or
  precision.

Before searching, audit every proposed gate:

1. Point to the request words and context that make the gate necessary; one verb
   or a preferred proof form is not enough by itself.
2. Record the requested object and unit of analysis. Keep transaction/event state
   and document state in separate columns and state what each source proves.
3. Write one plausible positive and one plausible negative boundary case. Revise
   a gate that would decide either case from matter label, document status, or
   transaction status unrelated to the requested object.
4. Before drafting, repeat this audit against inclusions and exclusions. New
   evidence may change whether a gate is proved; it may not silently create,
   delete, broaden, or narrow the gate itself.

If the request is singular or superlative, define both eligibility and ranking.
A large value or recent date cannot make an ineligible matter the winner. If the
request asks how often or for a percentage, build the denominator independently:
first enumerate every population member without using the target feature, keep
negative rows, then classify each row `yes`, `no`, or `unresolved` for that
feature. Never derive the denominator from feature hits.

## 2. Build a monotonic lead union and candidate register

Inventory matter folders completely. Search with multiple independent channels:
exact and near-exact filename phrases from the request, concept synonyms,
content hits, direct instrument names, status/closing terms, role/practice or
engagement evidence, and known entity variants. A keyword hit creates a lead;
it does not prove inclusion. A missing hit is not proof of exclusion.

Append every search channel's returned paths to `/workspace/lead_union.txt`, one
path per line, then deduplicate without deleting earlier paths. This file is a
coverage log, not an eligibility list. For every path, extract its matter folder
when one is present and ensure that matter receives a row in `review_state.md`.
A later regex, classifier, shortlist, or generated file may prioritize leads but
must never replace this union. If output is truncated, paginate or narrow until
complete before calling that channel reconciled.

Maintain this compact table in `review_state.md`:

| Matter | Lead paths/channels | Population/relationship gate | Other request gates | Transaction/event state | Document state | Claim each source proves | Contrary evidence | Unread high-signal files | Read state | Disposition/reason |
|---|---|---|---|---|---|---|---|---|---|---|---|

In the two gate columns, record each gate as `pass`, `fail`, or `uncertain` plus
an exact read source; do not replace separate gates with a narrative conclusion.
Use `unread`, `partial`, `read`, or `unreadable` for read state. Keep candidates
that arise from later or broader searches in the same register. Every lead-union
matter must have `include`, `exclude`, or `unresolved`. `Include` requires a
source-backed pass for every anchored eligibility gate. `Exclude` requires a
source-backed failure of at least one gate. Otherwise use `unresolved`; a strong
proof document, overall relevance, or evidence quantity cannot cure a failed or
unknown category gate. An exclusion reason cannot rely merely on a matter label,
a missing preferred file, or a narrower heuristic's failure to match.

Treat a lead as high-signal when its path directly names the requested object,
combines the requested subject with a material date or status, is a purpose-built
analysis, primary instrument, engagement record, or closing/status record, or
could change a rank or proof choice. Open it or record a source-backed reason it
cannot affect any gate. Do not infer that another file in the same matter is an
adequate substitute.

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

For ranking questions, compare the proposed winner or cutoff against every
eligible row. A requested top N means N rank positions, not an unconditional
N-row cap. If multiple items share the Nth rank under the requested metric,
present every co-ranked cutoff item as a principal result unless the user gives
a secondary tie-break; never invent alphabetical, chronological, or other
sorting solely to force N rows. With no cutoff tie, present exactly N. For
exhaustive questions, the final answer count must equal the number of included
rows. For "one document per item" requests, every included row must map to a
read proof file; no proof file may merely be inferred from its name.

## 5. Reconcile before drafting and before finish

Run these checks twice: once before drafting and once against the completed
answer.

- Every restrictive gate maps back to the request-gate table, requested object,
  and contextual population analysis. Delete any gate based only on a preferred
  proof form, matter label, or transaction/document status unrelated to that
  object. Do not delete a role, practice, portfolio, lifecycle, or matter-identity
  gate when the request actually supplies it.
- Re-run the gate audit. Any gate changed after initial framing must cite the
  request context that authorizes the change and new evidence at that gate's
  unit of analysis; stronger substantive proof alone cannot broaden population
  scope. For every affirmative row, state the transaction/event state, document
  state, and exact claim each source supports without substituting one for
  another.
- If plausible population readings yield different sets or winners, the
  boundary test is complete: at least one changed candidate's role, purpose, and
  status evidence was read, both outcomes were compared, and the selected
  meaning or unresolved ambiguity is recorded.
- Diff the deduplicated matter folders in `lead_union.txt` against the register.
  The difference must be empty: every surfaced matter has a sourced disposition,
  and no later shortlist or regex silently dropped an earlier lead.
- Make a compact gate matrix for every affirmative result: one cell per anchored
  gate, with `pass` and an exact read source or `not applicable`. Evidence of
  importance, detailed terms, or an operative document cannot substitute for a
  population or relationship pass. Every exclusion names a source-backed failed
  gate and applies the same test; absence of a preferred primary instrument is
  not itself a failure when claim-sufficient corroborated evidence exists.
- Compare the candidate set before and after final reconciliation. For every
  removed row and every late `exclude` to `include` reversal, reopen the exact
  source for each affected gate and write why the prior reason was wrong. If the
  change relies on proposed, anticipated, referenced, or merely related conduct,
  keep it unresolved unless the request makes that state or relationship pass.
  Do not allow a stricter proof test for exclusions than for inclusions.
- Every requested row, total, denominator, and ranking ties back to the register.
  For prevalence work, the denominator ledger was created independently of the
  feature search, retains negative rows, and its `yes + no + unresolved` count
  equals the full population count.
- Every cited supporting document was opened and is the strongest proof for the
  requested claim; complementary purpose-built or status proof is not discarded
  merely because an operative instrument also exists.
- No consequential decision relies on an unresolved partial read or an unread
  high-signal file.
- The principal displayed set matches the requested rank depth: exactly N when
  the Nth rank is unique, and all co-ranked cutoff items when tied unless the
  user supplied a tie-break. For an untied singular or superlative answer, keep
  eligible comparators in scratch unless comparison discussion was requested;
  do not label a runner-up as an additional answer.
- Material names, dates, amounts, roles, status, and quotations are rechecked
  against source files. Exact quotations and detailed terms require a source
  that contains them; corroborated existence evidence supports only that more
  limited claim.

When full resolution is impossible within the available evidence or budget,
state the exact unresolved scope instead of presenting a heuristic sample as a
complete set. Keep the scratch ledger outside `/workspace/output`; only the
requested deliverables belong in output.
