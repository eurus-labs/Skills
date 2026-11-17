# Reviewer task

Check the exact rendered draft against source and return findings or a verdict. You judge; you do not
rewrite the draft.

## Inputs

The task contract from [`workflow.md`](workflow.md#the-task-contract): the draft revision and the sections
to review, the scope, source access, the analyses, the grounding record, and the mechanical reports.
Copy `target_id`, `draft_revision` and the hash fields from the review queue in `prose-report.json`, as
[`prose-rules.md`](prose-rules.md) says.

## Do

1. Read the cited source for each section, not only the citation. A citation that resolves does not show
   that the paragraph is right.
2. Apply the review criteria in [`prose-rules.md`](prose-rules.md#content-review-criteria-for-manual-sections)
   to every substantive section. Also assess the whole draft: topic coverage, navigation, cross-page
   consistency and usefulness to its audience.
3. Run the readability measurement named in [`prose-generation.md`](prose-generation.md) and judge the
   passages it flags.
4. Return one review row per section in the shape
   [`schemas.md`](schemas.md#prose-reviewjsonl--review_version-2) defines, with the verdict, findings and
   bound hashes. Give each finding a stable ID, its location, why it matters, and a concrete correction.
5. Record `review_mode` truthfully: `independent` only if you ran in a context separate from the Writer's,
   otherwise `self_review`.

## Return

The rows and a short summary of what you inspected, to the Coordinator, who writes them to
`prose-review.jsonl`. When the evidence cannot settle a reading, return `unresolved` rather than
`confirmed`.

## Never

- Confirm a section you wrote, or one whose content changed after you read it.
- Confirm because a mechanical check passed. Mechanical checks cover format and consistency only.
- Edit the draft, the analyses or the docs directory.
