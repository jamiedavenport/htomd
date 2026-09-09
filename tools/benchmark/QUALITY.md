# Proposed quality evaluation

Status: proposal only. No quality scores or human-reviewed reference labels have
been produced by this work. The existing speed results do not establish quality.

## Evaluate two different jobs

1. **Extract useful content from a whole page.** Give all six libraries identical
   complete snapshots with their documented defaults. Measure retention of the
   intended article/documentation content and exclusion of menus, promotions and
   unrelated material. This measures suitability for extraction; a general markup
   converter may retain navigation because that is its intended behavior.
2. **Convert relevant HTML faithfully to Markdown.** Give every library the same
   reviewer-selected HTML fragment containing the intended content. Measure text
   and formatting preservation. Fragments must come directly from the annotated
   HTML, not from htomd's output or selection algorithm.

Keep these scorecards separate. A library can be a good converter and a poor
main-content extractor. Use Markdown output where necessary, disclose every adapter
and option, and keep any later tuned configurations separate from default results.

## Establish an independent reference

All 115 current block inventories are `machine_draft`; none is human reviewed.
The 40 captured outputs test change detection, and the 20 curated regressions test
specific expectations. Neither constitutes a complete, independent quality reference.

Start with 20 development pages, for example 10 articles, six documentation pages
and four boundary cases, spread across domains. Use this pilot to settle the rubric
and identify ambiguous cases. Then apply the frozen rubric across all 115 snapshots.
Keep the existing 80 development / 35 held-out domain split: publish the held-out
scorecard as the primary result and development results separately. If a held-out
domain's failures inform changes to extraction behavior, replace that domain before
claiming a fresh held-out result, as required by the fixture instructions.

Reviewers should label the sanitised HTML without seeing converter outputs:

- Required content blocks/spans, optional acceptable content, and boilerplate.
- Intended reading order and repeated occurrences that really belong in the content.
- Expected structures: heading levels, lists/nesting, links/destinations, code text
  and whitespace, tables/cells, quotations and images/alternative text.
- Explicit metadata values and acceptable alternatives, including absent fields.
- Pages without an article, where the expected task/output must be stated first.

Use source identifiers and character/token spans so partially retained blocks can
receive partial credit. Store labels beside existing annotations with reviewer
identity, rubric version, snapshot hash and review status. Have two reviewers label
the pilot independently, then second-review a random subset plus all ambiguous cases
in the remaining corpus. Resolve disagreements and report their frequency.

## Score content, structure and metadata separately

| Dimension | Proposed measurement |
| --- | --- |
| Content retention | Recall: retained required source content / all required source content |
| Content cleanliness | Precision: retained acceptable source content / all emitted content, after removing Markdown syntax |
| Balanced extraction | Per-page F1 alongside precision and recall; never F1 alone |
| Reading order | Correct ordering of matched reference blocks, with omissions reported through recall |
| Formatting fidelity | Correct/applicable features for headings, lists, links, code, tables and other annotated structures |
| Metadata | Per-field correctness, missing values and unsupported fields reported separately |
| Severe failures | Missing main content, unexpected empty output, crashes, invented content, duplication, broken code or tables |

Match emitted content to annotated source occurrences; cap credit at the reference
occurrence count so duplicated paragraphs cannot increase recall. Optional content
can count as acceptable without making its absence a recall error. Audit ambiguous
alignments rather than treating a fuzzy text match as proof of correctness. Report
unmatched additions and duplicates explicitly. Normalise ordinary whitespace and
Markdown presentation differences, while preserving code whitespace, link targets,
heading levels and table structure.
Declare link base context per page and compare resolved destinations without making
network requests. Unsupported formatting still fails an applicable reference feature;
it must not disappear from the scoring denominator.

Compare parsed Markdown structure rather than exact Markdown strings: alternative
bullet characters or heading syntax can represent the same result. If structural
scoring needs an external Markdown parser, pin it in the isolated evaluation
environment only; the distributed htomd package remains dependency-free. Do not use
htomd's own renderer as the reference interpreter.

For metadata, use each library's public metadata API where supported. Record these
adapters and settings separately and measure their cost if reporting speed alongside
metadata quality. Unsupported metadata APIs are N/A, not zero scores. Do not attach
metadata quality from a different API to the existing conversion timings.

Define empty-reference and expected-empty cases during the pilot. Unexpected empty
output on a page with required content gets zero recall; expected emptiness on a
boundary case must not be treated as a failure. Surface failures in denominators
rather than silently dropping unsuccessful pages.

## Report enough detail to explain the outcome

Average per-page scores so large Wikipedia/Wiktionary pages do not dominate, then
show articles, documentation and boundary cases separately. Include domain-level
results, sample counts and paired per-page differences. Use uncertainty estimates
that resample domains together; domains share templates and are not independent
page samples. Treat small differences with overlapping uncertainty as ties.

Review anonymised, randomly ordered outputs for every severe failure and a stratified
sample of otherwise successful pages. Human review checks that automated metrics
match readable, useful output. Model assistance may prepare drafts or flag cases,
but the final references and comparative judgments need human review.

Publish separate extraction, conversion-fidelity and metadata scorecards, with speed,
RSS, installed size, implementation language and dependency counts alongside them.
Use the same evaluated subset and adapters for any speed/quality comparison; collect
new timings when inputs or APIs differ from the full-page performance benchmark.
Avoid a single weighted winner unless the weights are chosen before seeing results.

## Suggested first deliverable

A reviewed 20-page pilot, a frozen annotation rubric, deterministic scoring tests,
and a small report showing omissions, clutter and formatting errors side by side.
Only then expand annotation and publish quality rankings. Everything stays under
`tools`/test fixtures and outside the package distributions. No new page downloads
are required, and existing fixture provenance and licence requirements still apply.
This evaluates sanitised static HTML. It cannot establish quality on live pages,
JavaScript-rendered content or the removed scripts/styles and embedded media.
