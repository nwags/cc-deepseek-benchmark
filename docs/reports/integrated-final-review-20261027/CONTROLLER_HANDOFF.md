# Integrated research report - revised controller handoff

**Date:** October 27, 2026. **State:** revised draft for review.

Evidence baseline: `nwags/cc-deepseek-benchmark`, live main checked at
`79f790fdd9067e33a29e0409c15f8890068ff22d`. Local work remains on
`analysis/integrated-final-report-20261024`; no commit or push. This additive
October 27 directory preserves the October 24 package unchanged.

Start with [the revised manuscript](INTEGRATED_FINAL_REPORT_REVISED_20261027.md)
and [the revised PDF](output/pdf/CLAUDE_CODE_BACKEND_BENCHMARK_REVISED_REVIEW_20261027.pdf).
[Revision notes](REVISIONS_AND_REVIEW_NOTES.md) map all seven user concerns to
the changes and record website alignment work after the report gate.

## Evidence and validation

- Exact 900/960 reviewed populations and their original manifest authority are
  preserved. Headline results remain 515/562 raw and 499/543 clean successes.
- Source precision remains in CSV/JSON evidence. Human-facing costs in the
  manuscript and figures are rounded to cents. The mixed-evidence selected
  extended sum displays as $343.45; this is not an exact invoice total.
- New configuration/token analysis exposes seven retained Claude Code versions,
  shared task revision, differing tool restrictions, 868/960 thinking-event
  coverage, source-specific cache/output usage, and historical output/outcome
  medians. It creates no reasoning/final-answer token split or hidden-content
  export.
- The seven figures have PNG/SVG assets and a source-data manifest. The PDF is
  generated from the same manuscript; its rendered-page assessment is recorded
  separately from automated checks.
- Current outputs: `validation_summary.json` (base reproduction),
  `revision_analysis_summary.json` (new metadata analysis),
  `presentation_validation.json` (manuscript/figure/PDF checks), and
  `visual_review.json` (rendered-page assessment).
- The 23-claim matrix and tested/not-tested matrix are exported from the current
  manuscript. Source hashes and pinned URLs are in `source_inventory.csv` and
  `source_reference_map.json`.
- Original October 24 focused checks (80 Python + 12 cross-provider; 296
  dashboard tests) are retained under `validation/prior_review/`. They are not
  represented as newly rerun for this editorial revision.

The original full-sweep raw tree and Phase 3 combined CSV remain absent from the
committed checkout. Reproduction uses manifest-bound committed review/reporting
data. Original private provider exports, live DB/R2 inventory, and remote raw
artifacts were not reacquired. All 16 live dashboard surfaces remain unavailable;
the current revision preserves the previous access record and does not claim
new rendered acceptance or completed dashboard onboarding.

## Reproduce safely

Use a checkout of the pinned baseline with this directory at its repository
location. The base validator refuses a changed HEAD or tracked-source changes.
All scripts below write only this additive review directory. No historical
generator entry point, provider API, model call, or database connection is used.

1. `python3 docs/reports/integrated-final-review-20261027/validate_report.py`
2. `python3 docs/reports/integrated-final-review-20261027/analyze_revision.py`
3. `python3 docs/reports/integrated-final-review-20261027/build_figures.py`
4. `python3 docs/reports/integrated-final-review-20261027/build_pdf.py`
5. `python3 docs/reports/integrated-final-review-20261027/validate_presentation.py`

The first two scripts use Python's standard library. Figure generation requires
matplotlib/numpy; PDF generation uses pandoc, reportlab, Pillow, and DejaVu fonts;
presentation checks additionally use pypdf and pdfplumber. Exact review-runtime
versions and executed validation results accompany the package. A standalone
copy can be read without those tools; reproduction requires the repository at
the pinned commit and, for preservation checks, the original October 24 review.

## Review and release boundary

Review the definitions, configuration qualifications, cost authority, token
scope, task/failure counterexamples, and challenge/mitigation table. Decide
whether live dashboard/R2 access limits block the intended release. The Markdown
controls if a reading copy ever differs. Approval of a final manuscript should
precede regeneration of the final PDF and alignment of website statements and
download links.

Phase 1/2 remain frozen; Phase 3 remains closed; Kimi K3 remains a compatible
addendum. No paid sweep, provider probe, migration, protected DB/R2 write,
Phase 4/5 activation, publication, commit, merge, or push was performed. The
two private research leads supplied no public recollections or attribution
claims. All factual additions use public committed evidence or explicitly
labeled offline derivation.
