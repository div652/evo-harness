# Batch 6 proposals (tasks 014 059 082 130 169 176 179 230)

## NEW names

None. Every stage, tag, hindsight value and error kind fit an existing taxonomy name.

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|

## Issues

- **What label_check means when the work matched neither label.** This happens when the declared label is wrong and the work is also not the stage the "Check the label" note suggested. Example: 082_T1 [79]-[87] was in-depth reading under "Read documents picked from the file listing", and the note suggested Screen. These stages were marked `none`. `ignored` was used only when the corrected label is the stage the note suggested. No run in this batch closed a stage and started the suggested one, so there are 0 `followed`.
- **Where label_check goes when a declared span is split.** The batch applied this three ways:
  - on the part that holds the stage_start (169_T0, 169_T2);
  - on the part where the suggested work was done (230_T2 [44]-[69] and [74]-[84], 179_T1 [62]-[81]);
  - on both parts (059_T2).

  One convention should be fixed at the merge.
- **The usual relabel.** The most common relabel was "Read documents picked from the file listing" to "Screen candidate matters by reading documents". Agents keep declaring the listing-read stage for reads that follow a keyword or scan lead. The note suggested Screen in every case, and every case was `ignored`.
- **Text in stage_end results that the logs drop.** Some stage_end results carry a system-appended list: "Matters that appeared in your search results but none of whose documents you have opened or listed". The compact logs truncate it, and only the raw trace shows it.
  - In 179_T1 the list named the portfolio-company matters, while the review text above it pointed to other series. The critic value is flagged-ignored, citing the list.
  - The critic values do not record whether a flag came from the review text or from this system list.
- **Mid-stage protocol notes.** Notes like "[Stage protocol] Stage check: this call looks like …" appear inside tool results (014_T0 [45], 059_T0 [29], 059_T2 [53], 230_T1 [68]). They are mentioned in notes only and do not count toward label_check.
- **Review-endorsed vs not-flagged.** These are close calls when a review praises or accepts the wrong decision without pushing it.
  - 230_T1 over-inclusion is marked review-endorsed: the screening review called the asset-purchase matters the only solid executed examples.
  - 169_T1 is marked not-flagged: the review named the excluded matters but asked only for the check the agent had already made.
- **Recurring pattern in 179, 230 and 130.** A store-wide extraction scan surfaces every needed matter. The agent then lists or reads a hand-picked subset, chosen by matter-number series or by its own summary. The review flags the unopened matters, mostly by example or by range, and the agent moves on. These runs get surfaced-not-opened with flagged-ignored.
- **A protocol detail from the batch's own runs.** The "Finish the run" stage must end at the finish call event, not at its result event.
