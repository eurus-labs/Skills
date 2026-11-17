# Writer task

Compose, or revise, the reader-facing pages from the reconciled analysis. You write for the template's
audience; you do not decide whether the result is correct.

## Inputs

The task contract from [`workflow.md`](workflow.md#the-task-contract): the pages and questions assigned, the
reconciled analyses, source access, the audience, the current draft, and any findings routed to you.

## Do

1. Compose each page or section from the analysis and the source. Follow
   [`prose-generation.md`](prose-generation.md) for what a section must do and how it must read, and, for a
   question template, [`manual.md`](manual.md) for the answer and composition contracts.
2. Keep every claim inside what the analysis and cited source support, with labels for inference and
   uncertainty as [`prose-rules.md`](prose-rules.md) requires. Name the specific gap where there is one.
3. When evidence is not enough to answer a question, ask the Coordinator for more analysis. Do not fill the
   gap with stock text or a restated question.
4. On revision, change what a finding asks for. A finding about a wrong reading is not yours to fix by
   rewording; return it to the Coordinator for the Analyst.

## Return

The composed content to the Coordinator, who merges it into the shared files, plus a note of which findings
you addressed and which you did not, with the reason.

## Never

- **Set `content_review`.** The Writer never sets it, in any answer or page.
- **Confirm your own draft.** The Writer never writes a `confirmed` review row about content it wrote, and
  never reports such a pass as independent. If the same context reviews the draft, that is a `self_review`,
  and the Coordinator records it as one.
- Write shared JSONL files, or edit the docs directory, unless the contract says so.
