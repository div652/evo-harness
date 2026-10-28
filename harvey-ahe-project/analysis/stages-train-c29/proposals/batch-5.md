# Batch 5 proposals (round 2, campaign 29)

Tasks: 017 061 068 137 162 169 176 230 (24 runs: 6 pass, 18 fail; passes are 061_T1, 061_T2, 162_T2, 176_T0-T2).

## NEW names

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|
| critic value | NEW: review-endorsed | A stage review named the matter or document behind the error, but recommended or supported the erroneous decision (e.g. suggested a needed matter is outside the request), and the agent followed it | 230_T0 [81]-[86] (review at [53] called a needed portfolio matter's consents "non-real-estate lender consents"; the answer then excluded it) | `not-flagged` would hide that the review discussed the matter; `flagged-*` imply the review warned against the error. The brief's four values assume the critic is either silent or right. |

## Issues

- Declared "List files in the document store (attempt 2)" was used for whole-folder-name listings in most runs; relabelled "List matter folders" with `declared:` notes (all eight tasks). When attempt 2 was mainly file-name globs it was relabelled to a file-name search (162_T0 [8]-[25], 169_T0 [8]-[17]).
- Round-1 convention 3 (label a mixed parallel event by its store-wide keyword search) conflicts with round-2 rule 2 (keep the declared name when it fits). Where a declared listing stage also ran one store-wide name search I kept the declared name and tagged `mixed intents` (162_T1 [32]-[38], 162_T2 [22]-[28], 176_T2 [75]-[82]).
- Seven runs ended at the first store-wide extraction script with uncapped output (017_T1, 068_T0-T2, 137_T1, 137_T2, 169_T0), always the third stage, so `critic` is `no-review`. The reviews just before it had recommended a store-wide content search without warning about output size.
- Matters that were listed but never read (162_T0, 230_T0) are coded `under-inclusion` on the write stage, because the taxonomy counts a listing as opening the matter. The actual decision was made at the screening stage that did not read them, so `surfaced-not-opened` would place it more naturally. A kind like "listed-matter-not-read" may be worth adding.
- `critic_note` (coordinator rule): a flag that names the mechanism (e.g. the hardcoded candidate list, the three-way file-name filter, the unrerun scan) but not the matter is coded "(generic flag)" (017_T0, 017_T2, 162_T1, 230_T1). These flags were specific about the cause, so a third category ("mechanism flag") may be useful.
- The harness adds "[Stage protocol] Stage check" notices to normal tool results (061_T2 [18], 137_T0 [71], 176_T1 [49]-[69], 230_T0 [29]-[31]). They are not refusals, so they get no tag and are only mentioned in notes. Refused calls (137_T0 [81], 176_T1 [91]) are tagged `tool error`.
- 230_T2: the reviews at [51] and [133] pushed to drop a needed matter (lender consents on a portfolio transfer). The agent kept it as "borderline", and that criterion passed. This is the reverse of 230_T0, where the agent followed a similar suggestion.
- 169_T1: the one extra matter it asserted cannot be explained from the logs; the error is coded `over-inclusion` with no stated reason.
- 017: the add-back rate criteria fail because of the bucket composition, which is a mix of one missing deal and extra deals. They are folded into the over-inclusion error rather than given a separate miscount error.
