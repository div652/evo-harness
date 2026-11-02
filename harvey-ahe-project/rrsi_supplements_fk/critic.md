# Domain guidance: Harvey LAB firm-knowledge tasks (RRSI critic)

The harness drives a frozen policy model through Harvey LAB firm-knowledge
tasks: it searches one shared store of a law firm's matter documents and
writes an answer file, `response.md`, that a judge grades against a
per-criterion rubric. This evolution line is law-domain-only, so LAW-GENERAL
professional method ("enumerate every candidate matter before concluding",
"verify each finding against its source document", "cover every requested
item") is legitimate and NOT leakage; the line is crossed at TASK-specific
facts, matter, client or party names, folder or file names in the store,
figures, or answers.

Existing safety mechanisms that must not be removed or weakened without a
working replacement: the `finish` tool and its deliverable checks (it is the
only stop tool), the `read` tool's handling of large documents, and every
tool's exception handling (a raised exception ends the trial). Text
addressed to the judge, padding of deliverables, or any attempt to read or
influence grading is GRADER GAMING.

(Adapted from the Harvey LAB critic brief of google-research/rrsi.)
