# Dashboard failure taxonomy J2 snapshot

Date: 2026-08-16

Status: J2B canonical offline snapshot frozen; J2C manifest-bound dashboard consumption implemented; J2D representative/manual evidence and visual review accepted 2026-08-16. DR-101, DR-102, and DR-103 are complete.

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

Implemented 2026-08-14 and manually/visually accepted through J2D on 2026-08-16.

The server-only J2C loader validates the canonical manifest schema and identity; registry, comprehensive-review manifest, source-input, classifier, generator, and output hashes; output byte and row counts; the frozen scope fingerprint; the exact 960-trial set shared by the taxonomy, reviewed CSV, and reviewed evidence JSONL; the 16-arm extended population; axis distributions; and the exact 243-trial manual-review union. Supporting artifact IDs must be UUIDs retained for the same reviewed trial. Any disagreement produces an explicit invalid or unavailable state with no taxonomy rows and no database, R2, or live-analysis substitute.

J2C.4 additionally pins the raw canonical manifest bytes to accepted J2B SHA-256 `71e1c0fbee99d07fe18512902ed62c3fa2eb752d9e08c68c3d75a1dc1a4e3088` before parsing any taxonomy row, and pins the three classification-bearing output identities as defense in depth. A self-consistent alternate output/manifest set is therefore rejected even through the deployment/test directory override. Next production output tracing is rooted at the repository and explicitly includes only the registry, five canonical J2 files, three comprehensive-review inputs, and two producer sources for `/trial-quality` and trial-detail routes. Dashboard compile-time consumption uses the byte-identical app-local generated mirror at `apps/dashboard/src/generated/failure_taxonomy_v1.json`; focused tests pin its canonical SHA-256, byte equality, and parsed equality while the server snapshot loader continues to validate the repository-level canonical registry independently.

The join is a unique exact-`trial_id` map lookup. Arm, task, and raw-outcome fields are checked after that join only as identity-integrity assertions; they are never fallback join keys. A dashboard trial outside the frozen 960-row scope displays a separate `unavailable` state, which is not the `response_path_class=not_applicable` diagnosis.

`/trial-quality` now provides compact response-path, verifier, assertion, and trajectory columns; canonical registry-value filters; registry-derived labels, definitions, and help text; deterministic server pagination; compact snapshot provenance; and exact trial-detail links. Trial detail renders all four labels and definitions, confidence, manual-review requirement, structured evidence facts, and exact retained artifact-ID links. The browser neither receives nor executes classifier logic, and hidden/private reasoning is not required, retained, inferred, or displayed.

## J2D representative/manual acceptance

Accepted 2026-08-16.

The deterministic review packet verified the complete 960-trial frozen population and exact 243-trial manual-review union. Representative evidence review covered all four response-path anomalies, all five dependency/import refinements, both missing-expected-file/content cases, the successful timeout-after-progress control and its full 19-trial raw-success population, deterministic high- and medium-confidence no-substantive-attempt controls, an ordinary successful completion, an indeterminate trial, and a real dashboard trial outside the frozen J2 scope. Supporting artifact IDs were checked against the same-trial retained comprehensive evidence without fetching remote artifact bytes.

Trial Quality's manifest status, provenance, registry-derived four-axis labels and exact filters, compact rows, confidence/review indicators, and responsive table passed visual review. The representative in-scope detail pages passed review for definitions, structured evidence facts, artifact links, confidence, manual-review status, and the independence of raw outcome from the four derived axes. The real out-of-scope control correctly displayed J2 as unavailable rather than `response_path_class=not_applicable`; it retained the explicit boundary that no database, live-artifact, or browser-side classification substitutes for frozen J2.

The review found one adjacent wording ambiguity: the separate Quick diagnosis surface called its operational evidence layer a “live fallback,” which could be mistaken for a replacement for unavailable J2. The bounded correction relabeled it “operational live analysis” and stated that it is separate from frozen J2 and does not fill or replace an unavailable J2 diagnosis. The post-fix out-of-scope recapture passed with no new containment, wrapping, or layout issue.

Final acceptance used the existing production-mode dashboard because Next 16 Turbopack development mode separately exhibited approximately 50-second application-code renders and React Client Manifest errors. Local production acceptance observations were approximately 1.50 seconds for `/`, 0.80 seconds for filtered `/trial-quality`, 2.24 seconds for a representative detail, 0.52 seconds for the successful-timeout detail, 4.07 seconds for the initial out-of-scope detail, and 1.78 seconds for its post-fix recapture. These are local observations on representative hardware, not performance guarantees. This separate development-workflow issue did not block J2D acceptance and was corrected after acceptance as recorded below.

J2 remains frozen, manifest-bound derived evidence rather than raw benchmark truth. Dashboard consumption joins only by exact `trial_id`; raw outcome, policy, termination, and activity remain independent source axes; no category makes a provider/router causal attribution; trials outside the 960-trial scope remain explicitly unavailable; and no live or database classification fills or replaces the frozen taxonomy. With J2D accepted, DR-101, DR-102, and DR-103 are complete.

## Next 16 Turbopack development correction

The post-acceptance regression was isolated to incompatible compile-time filesystem and package-resolution boundaries, not J2 classification semantics: widening `turbopack.root` to the repository admitted the canonical registry above the dashboard package but made Next 16.2.9 Turbopack resolve app dependencies from a root with no npm dependency tree. Webpack development mode was the successful control. The correction retains the repository-level registry as canonical, compiles from its exact generated app-local mirror, removes the broad Turbopack root, and keeps repository-rooted production output tracing separate and narrowly enumerated. A single bounded Turbopack verification then returned HTTP 200 for `/` in 3.34 seconds and filtered `/trial-quality` in 3.83 seconds without `MODULE_NOT_FOUND` or React Client Manifest errors. These are local development observations, not performance guarantees; production J2 acceptance and DR-101/102/103 remain unchanged.
