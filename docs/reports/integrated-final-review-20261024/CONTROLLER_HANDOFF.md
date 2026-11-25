# Integrated final report — controller handoff

**Milestone:** evidence synthesis and offline validation complete; human gate pending.

| Item | State |
|---|---|
| Intent | Integrate the historical closeout and later reviewed evidence without replacing their authority or changing benchmark state. |
| Repository / base | `nwags/cc-deepseek-benchmark`, live `main@79f790fdd9067e33a29e0409c15f8890068ff22d`; remote `main` rechecked unchanged at close. |
| Draft branch | `analysis/integrated-final-report-20261024`; no commit or push. |
| Completed | Integrated report; sixteen-claim evidence matrix; tested/not-tested matrix; all-sixteen-surface access matrix; exact 900/960 membership exports; cost, quality, failure, task/family tables; six safe evidence traces; nine-refusal ID index; source hashes and last-change SHAs; reproducible offline validator. |
| Verification | 1,189 offline assertions; 80 focused Python tests plus 12 cross-provider tests (one frozen-output-writing test deselected); 296 dashboard tests; repository syntax check; strict comprehensive-review output scan; strict secret scan. Final package validation and preservation record accompany the bundle. |
| Deviation | No shared dashboard URL or database credential. Local runtime started, but separate local HTTP attempts were refused; no rendered/interactive acceptance claimed. No committed full Phase 3 raw tree or Phase 3 combined CSV; reproduction uses manifest-bound committed review/reporting data and a retained canary fingerprint. |
| Risks / open items | Live dashboard/R2 and private source exports/inventory were not freshly checked. Mixed cost authority remains explicit. Kimi pricing provenance and outcome allocation remain qualified. Statistical superiority, exact estimator dispatch mechanism, and causal router effects are not established. |
| State | Existing tracked files and frozen outputs unchanged; only this additive report directory is new. Phase 1/2 frozen, Phase 3 closed; Kimi K3 remains its compatible addendum. Phase 4/5 inactive. |
| Next objective | Controller/human review of report claims and limitations; decide whether access limitations block the intended release. No release action is preauthorized by this handoff. |

## Read first

1. [Integrated report](INTEGRATED_FINAL_REPORT_DRAFT_20261024.md).
2. [Validation summary](validation/validation_summary.json).
3. [Evidence/claim matrix](validation/evidence_claim_matrix.csv).
4. [Tested/not-tested matrix](validation/tested_not_tested_matrix.csv).
5. [All 16 dashboard surfaces](validation/dashboard_surface_review.csv) and
   [recorded local HTTP access attempts](validation/dashboard_http_review.json).

## Review data

- `validation/phase3-core_derived_membership_manifest.json` and
  `validation/phase3-extended_derived_membership_manifest.json` export the exact
  source-selected trial sets. They are derived exports, not new scientific
  authority. `exact_reviewed_trial_membership.csv` contains both scopes with
  an explicit scope column (1,860 rows, intentionally including core rows in
  both scope exports).
- `validation/arm_comparison.csv` retains canonical arm/run identity, raw and
  clean counts, costs, relations, confidence, normalized state, and allocation
  restrictions. Aggregate ratios do not create per-trial billing.
- `validation/cost_chronology.csv` keeps historical, August 21, August 24, and
  August 25 arm values separate.
- `validation/failure_composition_by_arm.csv`, `task_profiles.csv`, and
  `task_family_profiles.csv` expose the joined analytical tables.
- `validation/refusal_trial_ids.csv` contains nine public trial IDs and safe
  provenance fields, without task payloads or transcript/refusal excerpts.
- `validation/evidence_traces.json` provides six deterministic illustrations:
  ordinary success, refusal, successful timeout, dominant Gemini Flash timeout,
  Haiku verifier failure, and incomplete residual. Full raw artifacts were not
  reread; the traces say so.
- `validation/source_inventory.csv` records public repository source paths,
  hashes, sizes, last-change commits, and pinned-baseline URLs. Inventory
  inclusion is not a claim that every historical document was substantively
  reviewed. The required guides, relevant release constraints, page manuals,
  and claim-bearing sources were inspected. The only repository `AGENTS.md`
  found at this baseline is the root file.

## Reproduce the offline analysis

Place this directory at its repository-relative location beneath `docs/reports/`
in a checkout of the pinned baseline. The validator uses Python's standard
library and needs no secrets, database, R2, provider API, model call, or paid
execution. It refuses a different HEAD or tracked source modifications. It
writes only this review directory's `validation/` outputs, replacing this
review's generated copies; it does not call historical generator entry points.

**Command 1 — reproduce report checks from the repository root**

```bash
python3 docs/reports/integrated-final-review-20261024/validate_report.py
```

The human-authored report and evidence/test matrices are not regenerated by
that command. The original reviewed snapshots remain authoritative. The
task-cluster bootstrap is explicitly exploratory, uses seed `20261024` and
20,000 resamples, and treats each of the 20 tasks as the resampling unit.

The executed test commands and observed outcomes are summarized in the test
matrix and retained logs. Tests ran on the review environment (Python 3.13.16
for pytest; Node 24.22.1), not the historical benchmark execution environment.
The standard-library report validator ran under Python 3.12.14.

## Scope and source firewall

The two requested private research leads were consulted only to guide source
investigation. Their text, personal recollections, private repo paths, and
unverified individual-attribution claims were not copied into the report or
validation data. Factual report claims are supported by the benchmark
repository or explicitly labeled as new offline derivations.

The bundle contains no private provider exports, account/project/API-key IDs,
credentials, task payloads, or copied hidden reasoning. Supporting artifact and
trial UUIDs already present in committed public evidence are retained for
traceability.

A local Next.js launch transiently regenerated its normal environment type
declaration. That generated tracked-file change was restored to HEAD; final
tracked-file preservation checks passed. No frozen result/report file was
rewritten. The historical cross-provider generator-writing test was excluded
before test execution; the initial dependency preparation was interrupted and
the safe test selection was run afterward.

## Release boundary

The package is a draft for controller/human review. It does not approve a
report release or mark full dashboard onboarding complete. Resolve access if
the controller requires a visual/interactive dashboard or fresh artifact audit
before release. Do not reapply Migration 009 or other migrations for that
purpose. Do not run acquisition/relay plans, paid sweeps, protected writes,
publication, merge, push, or Phase 4/5 work from this handoff.
