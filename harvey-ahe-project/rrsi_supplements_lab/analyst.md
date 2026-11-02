# Domain guidance: Harvey LAB legal tasks (RRSI analyst)

The agent performs professional LEGAL work across 25 practice areas
(contract review, drafting, and redlining; M&A and capital markets;
governance, funds, IP, litigation support, and more) on Harvey LAB: a
frozen policy model, driven by a NexAU harness, reads each task's folder of
source documents (mostly `.docx`, with `.eml` and `.xlsx`) in a network-less
sandbox and must write DELIVERABLE FILES to `/workspace/output` under the
requested names, almost always `.docx`. One judge grades the deliverables
against a strict rubric of 23 to 100 independent pass/fail criteria per
task, and the score is the share of criteria passed, pooled over all trials.
A criterion fails if the required content is missing from the DELIVERABLE
FILE; work done in chat or in scratch files earns nothing, so "computed but
never written into the deliverable" is its own failure family. Each task
detail lists the judge's per-criterion verdicts with reasoning. Rank modes
by the criteria they cost.

(Adapted from the Harvey LAB analyst brief of google-research/rrsi.)
