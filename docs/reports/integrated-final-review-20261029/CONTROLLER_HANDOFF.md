# Integrated report and website alignment - review handoff

Completion date: October 30, 2026. State: ready for controller/human review;
not approved for publication. The manuscript and PDF remain the unchanged
October 27 revised review draft. Website preparation began October 29.

## Intent and repository state

Complete the seven requested report improvements and prepare the corresponding
personal-website update, preserving historical evidence and release gates.
This additive directory completes the website portion of the review; it does
not supersede the manuscript's scientific authority.

| Repository | Local branch | Live main, verified October 30 |
|---|---|---|
| `nwags/cc-deepseek-benchmark` | `analysis/integrated-final-report-20261024` | `79f790fdd9067e33a29e0409c15f8890068ff22d` |
| `nwags/nwags.github.io` | `review/benchmark-report-alignment-20261029` | `83fd7cbe047c06de3f1fd057d4f7a9627c712992` |

Both local HEADs equal their inspected live-main baselines. All report work is
additive and uncommitted; the website has seven modified and sixteen new files.
No commit, push, pull request, merge, or publication was performed.

## Completed

The revised report contains an abstract, introduction with practical findings,
methods and architecture, results, discussion and recommendations, challenges
and mitigations, and a conclusion. It introduces project terminology before
using it and retains detailed authority/claim/test/access matrices in appendices.

Seven figures show architecture, quality/runtime, failure composition,
quality/cost, task families, source-scoped cache evidence, and historical
token-versus-spend shares. Displayed USD values are rounded to cents; analytical
files preserve source precision. Token analysis separates cache/input/output
counters, event metadata, and unsupported reasoning/final-answer token splits.
The PDF contains 28 pages and matches the preserved review-package fingerprint.

The unpublished website candidate now includes:

- A summary with definitions, methods, failure taxonomy, token findings,
  task-family counterexamples, uncertainty, and a static 16-arm results table.
- The full research paper in HTML, the exact manuscript/PDF, all seven figures,
  downloadable analytical tables, and source fingerprints.
- Cents formatting in the summary and static/interactive frontier views.
- Separate evidence markers for provider bills, retained-usage reconstructions,
  estimates, and lower bounds; keyboard-accessible evidence details.
- Consistent Kimi display labels/colors without changing canonical provider IDs.
- Homepage, Documents, and web-resume wording/links aligned with the draft.
- Working section anchors, scrollable wide tables/charts, and full-size figure
  links; summary and paper content do not depend on JavaScript.

## Verification

`validation/website_validation.json` records the current 525 passing automated
checks. All 176 scientific fields across all sixteen arms match the pinned
August 25 V4 authority, with zero mismatches. Checks include exact source and
report hashes, all local links/anchors, cents formatting, analytical ZIP bytes,
figure decoding, deterministic generation, syntax, and whitespace checks.

`validation/browser_review.json` records actual rendered browser inspection of
the summary, paper, chart, and PDF. Desktop content fits the available width;
375px and 768px embedded viewports show no page-wide horizontal overflow.
Wide tables/charts scroll in their own panels. All sixteen chart points and
rows load; a keyboard-focused GPT-5.5 point exposes billing confidence and
allocation limits, with its tooltip contained in the mobile viewport. The PDF
link opens the browser's PDF viewer, showing page 1 of 28 and the Abstract.
These are embedded-width checks, not physical-device/touch certification.

The October 27 report's prior all-page rendered-PDF review is retained without
pretending it was newly repeated. Earlier 92 Python and 296 dashboard tests
remain dated historical checks; no benchmark application code changed here.
`validation/secret_scan.log` records the current repository secret scan.
Package fingerprints, privacy/secret checks, overlay verification, and archive
integrity are recorded separately by the package builder.

## Deviation and remaining limits

No scientific result or PDF text changed in this completion step. The only
validator edit updates its completion date. The October 27 notes saying that
website edits had not yet been made remain accurate for that date; this
handoff supplies the later website-preparation state.

All sixteen live benchmark dashboard surfaces, the live DB/R2 inventory,
original private provider exports, and the full remote raw-artifact chain
remain unverified. No access restriction was bypassed. Reproduction uses
committed, manifest-bound review evidence. Private recollections were not
introduced into the public website or report.

## Review and next objective

Review the revised paper and the website overlay together. Accept or revise
the manuscript and decide whether the documented live-evidence access gaps
are acceptable for release. An approved final manuscript must generate its
final PDF; website artifact pins, dates, labels, and links must then be updated
and checked against those final bytes before a separately authorized release.
The current candidate deliberately retains its review-draft status.

Phase 1/2 remain frozen, Phase 3 remains closed, and Kimi K3 remains a
Phase-3-compatible addendum. There were no paid runs, provider probes,
migrations, protected DB/R2 writes, or Phase 4/5 activation.

## Package use

The combined ZIP contains the preserved earlier report packages under
`benchmark-additions/`, the current additive review under the same prefix,
and the 23 changed/new website files under `website-overlay/`.
`website-tracked-changes.patch` covers the seven tracked website edits;
the overlay is the complete candidate for all 23 files. Its new files are
not represented by that tracked-only patch.

Inspect or copy the overlay into a separate checkout of the exact website
baseline above. The package itself does not apply, commit, or publish it.
For reproduction, place the report additions at their repository-relative
paths in a benchmark checkout pinned to its stated baseline, then run the
read-only validator with the selected website checkout as `--site-root`.
The website README and preserved report handoff provide the generator commands.
