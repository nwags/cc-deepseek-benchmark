# Dashboard Failure and Trajectory Taxonomy — Group J1

**Status:** Contract/foundation complete; DR-101, DR-102, and DR-103 implementation remains in progress

## Purpose

J1 defines the stable contract for a future offline second-stage classification of the accepted Phase 3 comprehensive-review snapshot. It does not classify or regenerate the 960 reviewed trials, change the accepted review, alter raw benchmark truth, or integrate new classifications into dashboard pages.

The canonical registry is:

`configs/dashboard/failure_taxonomy_v1.json`

It is the one source for enum IDs, ordering, friendly labels, definitions, confidence vocabulary, normalization, provenance requirements, and conservative evidence rules. `apps/dashboard/src/lib/failure-taxonomy.ts` validates and exposes the same JSON to TypeScript. A future Python J2 generator will read the JSON directly rather than maintain another label table.

## Frozen source boundary

The only canonical input for the initial J2 generation is the checked-in snapshot at:

`results/manual_verification/comprehensive_review_20260731/`

The registry binds that source by manifest path and SHA-256, scope fingerprint, trial count, and the manifest-recorded hashes for `trial_review.csv` and `trial_evidence.jsonl`. Both input files contain the same 960-trial set. The completed read-only audit found manual evidence, transcript activity, verifier output excerpts, artifact inventories, exception evidence, Harbor result evidence, and trajectory-step observations for all 960 trials. CTRF tests are retained for 950/960, substantive trajectory steps for 909/960, complete evidence for 911/960, and incomplete evidence for 49/960. These coverage facts constrain what J2 may infer; they are not missing values to fill by rereading external storage.

`.review-cache` is local/ephemeral and is not a canonical input. The initial J2 run does not require Supabase or R2 rereads. J2 must fail closed if the bound manifest or input hashes differ.

Raw reward, raw outcome, exception fields, stored historical quality flags, current `ActivitySubtype`/`ExecutionValidity` classifications, and all accepted comprehensive-review files remain unchanged. The future output is a separate derived snapshot, suggested as `results/manual_verification/failure_taxonomy_20260813/`.

## Public axes

### Response path class — DR-101

- `synthetic_retry_empty_completion`
- `empty_completion_after_long_api_path_wait`
- `thinking_only_empty_completion`
- `empty_completion`
- `invalid_response_path`
- `unknown`
- `not_applicable`

This public interpretation does not replace existing analyzer fields. Existing `empty_completion_zero_usage` maps to `empty_completion`, because the public enum does not encode usage in the diagnosis. `suspect_noop_zero_token` and `suspect_noop_count` remain historical compatibility fields, not primary taxonomy values or causal evidence.

No response-path class attributes fault to a provider, LiteLLM, a router, the harness, or infrastructure unless retained evidence specifically supports that attribution.

The frozen review currently contains only four trials with `execution_validity=invalid_response_path`: two `synthetic_retry_empty_completion`, one `empty_completion_after_long_api_path_wait`, and one `thinking_only_empty_completion`. J1 records the broader stable public enum but does not reclassify those or any other trial.

### Verifier failure category — DR-102 primary

- `none`
- `verifier_environment_issue`
- `syntax_or_compile_error`
- `dependency_or_import_error`
- `wrong_file_or_path`
- `timeout_inside_verifier`
- `runtime_exception_in_solution`
- `test_assertion_failure`
- `missing_or_wrong_output`
- `no_meaningful_code_change`
- `partial_solution`
- `unclassified_failure`

This axis is independent from response-path, policy, and termination axes. `none` means that no verifier/task/submitted-solution failure category applies. It is appropriate for ordinary successes and for non-successful trials whose retained evidence places the event entirely on another axis—for example, a provider-policy refusal, invalid response path, or non-verifier timeout—without establishing a verifier/task/solution failure.

Specific categories require specific verifier, exception, result, or workspace evidence. `unclassified_failure` applies only after a verifier/task/solution failure is established but the evidence cannot select a more specific category. Raw outcome `failure` alone does not imply `unclassified_failure`. Likewise, generic timeout or termination evidence does not imply `timeout_inside_verifier`; retained evidence must place the timeout inside verifier execution.

### Assertion failure category — DR-102 secondary

- `none`
- `performance_threshold_failure`
- `numerical_or_data_mismatch`
- `missing_expected_file_or_content`
- `behavior_mismatch`
- `output_mismatch`
- `unclassified_assertion`

The secondary category applies only to a primary `test_assertion_failure`. Specific subtypes require sufficiently detailed verifier or CTRF evidence; otherwise the result is `unclassified_assertion`. When the primary category is not an assertion failure, the secondary value is `none`.

### Trajectory disposition — DR-103

- `successful_completion`
- `no_substantive_attempt`
- `early_abandonment`
- `partial_implementation`
- `plausible_but_incorrect_completion`
- `near_miss_cleanup_or_packaging_only`
- `near_miss_one_behavioral_defect`
- `repeated_unproductive_iteration`
- `timeout_after_meaningful_progress`
- `completed_work_with_verifier_or_infrastructure_issue`
- `indeterminate`

`successful_completion` is deliberate: the reviewed snapshot contains 562 successful trials, and an independent trajectory axis must represent ordinary success instead of forcing it into `indeterminate`. It is an ordinary-success fallback, not a raw-reward override: the raw benchmark outcome must be successful and retained evidence must not support a more specific anomalous trajectory disposition. When a successful trial has positive evidence for `timeout_after_meaningful_progress`, `completed_work_with_verifier_or_infrastructure_issue`, or another supported disposition, J2 must use that more specific supported disposition instead. This does not redefine raw benchmark success.

## Independence and ordering

Response path, verifier failure, assertion failure, policy, termination, and trajectory are independent axes. A classification on one axis does not automatically determine another. J2 must select the most specific diagnosis justified by retained evidence and the explicit eligibility rules.

All integer `order` fields in the registry are presentation/display order only. They are not classifier precedence. If J2 needs precedence rules, it must define and test them explicitly rather than infer them from registry ordering. In particular, trajectory classification checks for stronger positive anomalous evidence before using `successful_completion` as the ordinary-success fallback.

## Per-diagnosis output contract

Every trial will carry one diagnosis object per axis. Each diagnosis must include:

- `value`: the internal axis enum;
- `label`: the registry display label;
- `definition`: the registry definition;
- `confidence`: `high`, `medium`, or `low`, never a fabricated numeric score;
- `evidence_basis`: a non-empty list of specific retained facts supporting the diagnosis or fallback;
- `supporting_artifact_ids`: retained artifact IDs, with an explicit empty array when no artifact ID supports a conservative fallback;
- `manual_review_required`: an explicit boolean.

The future output manifest must bind the taxonomy registry and hash, comprehensive-review manifest and hash, scope fingerprint, both input hashes, classifier path/version/hash, output row count, and output hashes. This preserves reviewability without modifying the source snapshot.

## Conservative evidence sufficiency

- `no_substantive_attempt` requires complete or explicitly adequate absence-sensitive transcript, trajectory, artifact, result, and verifier coverage. Missing excerpts or unavailable artifacts cannot establish absence.
- `timeout_after_meaningful_progress` requires positive timeout evidence and separate evidence of meaningful progress. Runtime alone is insufficient.
- `completed_work_with_verifier_or_infrastructure_issue` requires both substantively completed work and specific verifier/environment evidence.
- `near_miss_one_behavioral_defect` requires specific verifier or CTRF evidence isolating one remaining defect and evidence that the rest is substantively complete.
- `near_miss_cleanup_or_packaging_only` requires evidence that substantive work is essentially complete and that only cleanup, packaging, placement, or delivery remains.
- `repeated_unproductive_iteration` requires observable repeated attempts without meaningful progress; a long runtime or high step count alone is insufficient.
- `partial_implementation` and `plausible_but_incorrect_completion` require positive evidence about the implementation. They cannot be derived solely from reward 0 or a generic failed outcome.
- Specific verifier categories require matching evidence. Use `unclassified_failure` only when a verifier/task/solution failure is established but remains nonspecific; raw benchmark failure alone establishes neither a specific verifier category nor `unclassified_failure`.
- `none` on the verifier axis may describe an independently explained non-success, and `timeout_inside_verifier` requires verifier-specific timeout evidence rather than generic timeout or termination evidence.
- Specific assertion categories require sufficiently detailed verifier/CTRF evidence; otherwise use `unclassified_assertion`.
- Incomplete, conflicting, or nonspecific trajectory evidence falls back to `indeterminate`; response-path uncertainty falls back to `unknown`.
- Hidden or private model reasoning is never required, retained, inferred, or displayed.

## J2 and later work

J2 will implement the offline classifier and create the separate manifest-bound 960-row derived snapshot. It must not modify `trial-analysis-core.ts`, the accepted comprehensive review, raw benchmark truth, or legacy compatibility fields. Dashboard filters, legends, counts, and evidence links come later and must consume the reviewed J2 output and this registry rather than recalculate classifications in the browser.
