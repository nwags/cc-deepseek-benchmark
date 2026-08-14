# Frozen J2 failure and trajectory taxonomy

Snapshot: `failure_taxonomy_20260813`

Classifier: `failure-taxonomy-classifier-v1.1.0`

Generator: `failure-taxonomy-generator-v1.1.0`

Frozen input scope: `960` reviewed trials.

Manual-review queue: `243` trials.

This is the frozen, offline J2 derived failure and trajectory taxonomy snapshot. Its source is the manifest-bound checked-in comprehensive review. It is derived evidence, not raw benchmark truth. Raw reward, raw outcome, exception, policy, termination, and activity remain independent source axes and are not replaced by this snapshot.

Legacy suspected no-op terminology is retained only for compatibility; it is not a primary diagnosis in this taxonomy. No hidden or private model reasoning is retained, required, inferred, or displayed. These categories do not make causal attributions to a provider, router, or harness.

Some taxonomy values intentionally have zero population because the classifier uses conservative evidence requirements and explicit fallback states. Medium-confidence refinements and other diagnoses marked for manual review remain reviewable through retained supporting artifact IDs rather than copied verifier or transcript excerpts.

Dashboard consumers must validate and consume this manifest-bound snapshot, join it to reviewed trials by `trial_id`, and fail closed on a manifest or input mismatch. They must not reclassify trials in the browser.

`trial_failure_taxonomy.jsonl` contains one row per frozen trial. `taxonomy_counts.json` contains complete enum counts, cross-tabs, diagnostics, and representative IDs. `review_queue.csv` contains the union of trials with at least one diagnosis requiring manual review. `failure_taxonomy_manifest.json` binds the frozen inputs, producer implementations, and all other snapshot outputs.
