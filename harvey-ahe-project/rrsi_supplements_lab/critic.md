# Domain guidance: Harvey LAB legal tasks (RRSI critic)

The harness drives a frozen policy model through legal document tasks
(Harvey LAB): it reads each task's source documents and writes deliverable
files that a judge grades against a per-criterion rubric. This evolution
line is law-domain-only, so LAW-GENERAL professional method ("read the
controlling provision before stating a conclusion", "cross-check computed
figures before finalizing", "cover every requested item") is legitimate and
NOT leakage; the line is crossed at TASK-specific facts, names, document or
file names, figures, or answers.

Existing safety mechanisms that must not be removed or weakened without a
working replacement: the `finish` tool and its deliverable checks (it is the
only stop tool), the `read` tool's handling of large documents, and every
tool's exception handling (a raised exception ends the trial). Text
addressed to the judge, padding of deliverables, or any attempt to read or
influence grading is GRADER GAMING.

(Adapted from the Harvey LAB critic brief of google-research/rrsi.)
