# Batch 13 proposals (tasks 240 241 243 247; all 12 runs failed)

All stages, tags and hindsight values fit the existing vocabulary. One new error kind.

| Kind | Name | Definition | Example | Why no existing name fits |
|---|---|---|---|---|
| error kind | NEW: under-inclusion | The agent opened and assessed a needed matter, but its answer leaves the matter out as not meeting the request. Usually it reads a qualifier more narrowly than the documents support, judges from the first lines of a document, or judges from a search that reached only part of the matter's files. Mirror of over-inclusion. | 241_T2 [34]-[35] (also 241_T0 [26]-[27]; 243_T2 [14]-[20]; 243_T0 [22]-[23]) | surfaced-not-opened requires the matter never to have been opened. hedged-answer is for a qualified conclusion, not for a matter dropped from the list. over-inclusion is the opposite direction. search-miss is for a matter that never surfaced. |

## Issues

- When a needed matter is excluded after being read (241_T0, 241_T2), the first error was placed at Write the response, where the exclusion is decided. This follows the 082_T1 precedent for over-inclusion. In 243_T2 the exclusion rests on in-matter greps that reached only emails, so the later error was placed at that "Search within a candidate matter's files" stage instead. The brief does not say which choice is right when a judgement rests on a search.
- In both 241 and 243, an answer that omits needed matters and also asserts an extra one got "answer over-inclusive" at the write stage, following the batch-2 Issue. The omission is carried by first_error and the extra matter by other_errors. Both errors then point at the same stage.
- In 243 the grep tool's content and files-with-matches hits were email (.eml) lines only, both store-wide and inside single matters. A matter whose evidence sits only in .docx files was never matched (e.g. 243_T2 [14]-[20]: an in-matter grep returned only email lines although the matter has a request-named document folder). This is likely why several runs miss matters. It is agent-observable only indirectly, because every hit is an email. A tag such as "hits from emails only" may be worth adding if other batches see it.
- 243_T0 [5]-[9]: in one parallel call, one store-wide grep ran alongside three reads of listing-top documents. By count the reads dominate, but the stage was labelled "Search file contents for request keywords" because the grep was the run's only store-wide step and it set the agent's candidate list. This extends the batch-1 convention for glob + grep openers.
- 241_T0 [2]-[3] is a full, uncapped shell `find` of every file (about 790K chars, no overflow). It was labelled "List files in the document store" with `huge output` and hindsight "target surfaced", because the listed file paths contain folder names that signal the request. "target in folder list only" covers only folder-name listings.
- Capped whole-store listings that happen to include a rubric matter (243_T0, 243_T1) got "target surfaced". The rubric matter is the listing-top matter the agent then read.
- 247 is three near-identical runs. Each one read only the listing-top matter and never searched.
