# Dashboard failure taxonomy J2 snapshot

Date: 2026-08-14

Status: J2B canonical offline snapshot frozen; J2C manifest-bound dashboard consumption implemented but not manually/visually accepted; representative/manual evidence review remains pending in J2D.

## Provenance and source boundary

J2A commit `bc95b52a` established the accepted deterministic classifier and preview identity. J2B freezes those accepted classification bytes at:

`results/manual_verification/failure_taxonomy_20260813/`

The only classification inputs are the J1 registry at `configs/dashboard/failure_taxonomy_v1.json` and the manifest-bound checked-in comprehensive review at `results/manual_verification/comprehensive_review_20260731/`. The canonical manifest binds the registry, comprehensive-review manifest, scope fingerprint, both 960-row inputs, classifier and generator implementations, and every non-manifest output. No Supabase, R2, `.review-cache`, network, provider, benchmark, or migration input participates.

The snapshot is derived evidence, not replacement benchmark truth. Raw reward, raw outcome, exception, policy, termination, activity, and historical quality fields remain independent and unchanged. Legacy suspected no-op fields remain compatibility data only. No hidden/private reasoning is retained or required, and the taxonomy does not infer a provider, router, or harness cause from these categories.

## Accepted snapshot identity

The classification-bearing outputs preserve the reviewed J2A.1 bytes:

| Output | SHA-256 |
|---|---|
| `trial_failure_taxonomy.jsonl` | `ccb4b9cbcc524d34336d4669abbb30c29b741cb03e7f76a9cb21c7fdd2b2eda1` |
| `taxonomy_counts.json` | `e1284625f3e48e2dcb69a569acb0e73ff326410ffd8b9bc8878cfe5b8863e9cd` |
| `review_queue.csv` | `aeb8eab2037ce5dd11bb0ef94cda4e0c28013b9c2d887aecdf129d77ea78e883` |

The JSONL contains exactly 960 frozen trial IDs. The review queue is the exact 243-trial union where at least one diagnosis requires manual review.

## Accepted distributions

- Response path: 922 `not_applicable`, 34 `unknown`, two `synthetic_retry_empty_completion`, one `empty_completion_after_long_api_path_wait`, and one `thinking_only_empty_completion`.
- Verifier failure: 760 `none`, 162 `test_assertion_failure`, 33 `missing_or_wrong_output`, and five `dependency_or_import_error`.
- Assertion failure: 798 `none`, 160 `unclassified_assertion`, and two `missing_expected_file_or_content`.
- Trajectory: 543 `successful_completion`, 174 `timeout_after_meaningful_progress`, 37 `no_substantive_attempt`, and 206 `indeterminate`.
- The 37 no-substantive-attempt diagnoses comprise 10 high-confidence and 27 medium-confidence cases.
- Nineteen successful raw outcomes retain the stronger `timeout_after_meaningful_progress` disposition. The snapshot contains four response-path anomalies and zero behavioral near misses.

Every unlisted registry value has zero population. Those zeroes are intentional: J2 uses conservative evidence eligibility and fallback rules rather than forcing a diagnosis. The five dependency/import refinements and two missing-file/content refinements are medium-confidence, manual-review evidence refinements. All five dependency/import cases are the audited `openssl-selfsigned-cert` trials.

## Producer and consumption policy

The canonical producer uses classifier version `failure-taxonomy-classifier-v1.1.0`, generator version `failure-taxonomy-generator-v1.1.0`, and manifest schema `failure-taxonomy-manifest-v1`. Preview mode remains available only for explicit output directories outside the repository. Canonical mode can write only the fixed snapshot directory and refuses a populated target; it has no force or replacement option.

Dashboard consumers must validate this manifest-bound snapshot, join by exact `trial_id`, and fail closed on manifest, hash, scope, row-count, or trial-set disagreement. They must not rerun the classifier in the browser.

## J2C dashboard consumption

Implemented 2026-08-14, pending manual/visual acceptance.

The server-only J2C loader validates the canonical manifest schema and identity; registry, comprehensive-review manifest, source-input, classifier, generator, and output hashes; output byte and row counts; the frozen scope fingerprint; the exact 960-trial set shared by the taxonomy, reviewed CSV, and reviewed evidence JSONL; the 16-arm extended population; axis distributions; and the exact 243-trial manual-review union. Supporting artifact IDs must be UUIDs retained for the same reviewed trial. Any disagreement produces an explicit invalid or unavailable state with no taxonomy rows and no database, R2, or live-analysis substitute.

J2C.4 additionally pins the raw canonical manifest bytes to accepted J2B SHA-256 `71e1c0fbee99d07fe18512902ed62c3fa2eb752d9e08c68c3d75a1dc1a4e3088` before parsing any taxonomy row, and pins the three classification-bearing output identities as defense in depth. A self-consistent alternate output/manifest set is therefore rejected even through the deployment/test directory override. Next production output tracing is rooted at the repository and explicitly includes only the registry, five canonical J2 files, three comprehensive-review inputs, and two producer sources for `/trial-quality` and trial-detail routes; Turbopack's repository root remains a separate compile-time requirement for the canonical registry import.

The join is a unique exact-`trial_id` map lookup. Arm, task, and raw-outcome fields are checked after that join only as identity-integrity assertions; they are never fallback join keys. A dashboard trial outside the frozen 960-row scope displays a separate `unavailable` state, which is not the `response_path_class=not_applicable` diagnosis.

`/trial-quality` now provides compact response-path, verifier, assertion, and trajectory columns; canonical registry-value filters; registry-derived labels, definitions, and help text; deterministic server pagination; compact snapshot provenance; and exact trial-detail links. Trial detail renders all four labels and definitions, confidence, manual-review requirement, structured evidence facts, and exact retained artifact-ID links. The browser neither receives nor executes classifier logic, and hidden/private reasoning is not required, retained, inferred, or displayed.

J2C is an implementation milestone only. DR-101, DR-102, and DR-103 remain implementation-in-progress until J2D representative/manual evidence review and the required manual/visual acceptance are completed.
