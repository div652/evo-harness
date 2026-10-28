# Batch 9 proposals (tasks 003 046 072 104 148 184 199 241)

## NEW names

None. Existing stages, tags, hindsight values, error kinds and critic values covered all 24 runs.

## Issues

- **label_check conventions used across the batch.**
  - `ignored` when the span did the suggested stage's work under the declared label. This usually means the span is relabelled to the suggested stage with `declared: …`; the common case is "Read documents picked from the file listing" relabelled to Screen.
  - `followed` was never observed: in 24 runs no agent closed a stage in response to a "Check the label" note.
  - Opener: a whole-store glob paired with a find/ls of matter-folder names keeps "List files in the document store" with `mixed intents` and gets `ignored`. A glob with only extension or file counts gets `none`.
  - Where a declared span was split, label_check sits on the row that holds the stage_start (or on the part that did the suggested work, 046/072).
- **Label notes show no effect.** label_check per task (ignored / stages): 003 5/43, 046 8/35, 072 13/46, 104 7/34, 148 10/43, 184 8/41, 199 9/46, 241 5/38.
- **Judgement visible before writing.** stage_end summaries now state include/exclude decisions before any write (072_T2 [103], [111]; 104_T1 [51]). Convention 1 still puts judgement errors on the write stage, and `why` names the stage where the decision first shows.
- **Over-inclusion after the first error.** When an answer misses the needed matter and also asserts a non-qualifying matter it would have picked anyway, the extra matter is a later over-inclusion error on the write stage (104_T1, 104_T2, 148, 184, 241, 046).
- **review-endorsed vs flagged-ignored.**
  - review-endorsed is used where a review named the wrong matter and the agent followed it: 104_T1 (the write review recommended leading with an executed transaction matter), 072_T0 and 046_T1.
  - flagged-ignored is used where later reviews then questioned the matter.
  - Reviews that say "do not add or drop matters" work against fixing an omission (241, 003) but were too generic to count as endorsement.
- **Stretched kinds.**
  - 046_T0 uses listed-document-not-opened for documents seen only in a store-wide file-name dump, not in a listing of the matter.
  - 104_T2 uses over-narrow-filter for a display cap: the scan covered the needed matter, but only the first 260 of 7,934 output lines were printed, and the next scan was narrowed from the visible part.
  - 184 uses search-miss although the needed matters appeared deep inside 130-210K-character file-name sweeps.
- **Hindsight gaps.**
  - 148's log header names no rubric matter, so markers are missing; its appearances were found by grepping the raw traces.
  - In 003, stages that touch only a matter the precision criterion allows (but which the header does not list) got `none`, not `decoy opened`.
- **Protocol "Stage check" warnings** appended to results that still came back are not tagged `tool error` (046_T2 [12], 072_T2 [61] [85], 184_T1 [37] [55], 184_T2 [84]). Only refused calls get the tag.
- **Relabels and splits.**
  - Snippet scripts over named candidate lists declared as Scan became "Search within a candidate matter's files" (199_T1, 199_T2, 241_T2).
  - A per-matter keyword filter of file names over 140 search-derived candidates became "Search file names for request keywords" (104_T1 [47]-[52]).
  - Splits: 046_T1 [67]; 072_T2 [23], [60], [64]; 148_T0 [71]; 148_T1 [63], [79]; 184_T1 [64]; 184_T2 [64], [66]; 199_T1 [15]-[22], [37]-[45]; 104_T2 [63]-[78] at [67].
