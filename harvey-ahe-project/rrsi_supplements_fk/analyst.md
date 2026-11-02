# Domain guidance: Harvey LAB firm-knowledge tasks (RRSI analyst)

The agent answers questions about a law firm's own past work on Harvey LAB
firm-knowledge tasks: a frozen policy model, driven by a NexAU harness,
searches one shared store of about 9,300 matter documents (mostly `.docx`,
with `.eml`, `.xlsx`, and `.pptx`) in a network-less sandbox and must write
its complete answer to `/workspace/output/response.md`. One judge grades that
file against a strict rubric of 1 to 85 independent pass/fail criteria per
task (median 6), usually one per matter or fact the answer must contain, and
the score is the share of criteria passed, pooled over all trials. A
criterion fails if the required content is missing from `response.md`; work
done in chat or in scratch files earns nothing, so "found but never written
into the answer" is its own failure family, alongside matters never found
and documents found but not read. Each task detail lists the judge's
per-criterion verdicts with reasoning. Rank modes by the criteria they cost.

(Adapted from the Harvey LAB analyst brief of google-research/rrsi.)
