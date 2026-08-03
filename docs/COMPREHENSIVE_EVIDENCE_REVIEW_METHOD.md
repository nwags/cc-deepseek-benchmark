# Comprehensive Evidence Review Method

This method produces a local derived review of the valid Phase 3 full-suite corpus and compatible Kimi K3 addendum. It does not change Supabase, R2, raw benchmark results, stored quality flags, validity records, pass-rate denominators, or historical reports.

## Source-of-truth boundaries

- Supabase remains the metadata source of truth for runs, trials, raw rewards, token/cost fields, validity/quarantine records, task attempts, and artifact identifiers.
- Immutable R2 objects remain the evidence source of truth. The generator performs bounded reads and never writes, replaces, or normalizes source objects.
- `results/manual_verification/comprehensive_review_20260731/` is a derived review layer. Its classifications are reproducible interpretations, not revised benchmark scores.
- The dashboard reads generated local files server-side. Browser clients do not access Supabase or R2 for the comprehensive-review page.

## Scope discovery

`scripts/generate_comprehensive_evidence_review.py` first discovers all `phase3-full-20` arm runs whose suite and logical mode are `full`. For provenance, `run_review.csv` retains complete, incomplete, invalid, quarantined, selected, and unselected candidates.

A scored-review run must:

1. cover every required suite task;
2. contain exactly three attempts per required task;
3. have no matching invalid/quarantine record; and
4. be the latest deterministic valid complete run for its arm.

This rule includes compatible Kimi K3 full-suite addenda without double-counting superseded runs. The metadata-only mode prints exact run labels, trial count, task count, and artifact count without reading R2 or writing local outputs.

The database transaction is explicitly read only. Full analysis requires read-only R2 credentials and writes only local derived outputs. Its resumable operational checkpoint lives under ignored `.review-cache/`, outside the review result directory.

## Artifact reading bounds

The default JSONL/structured read cap is 8 MiB per transcript or trajectory and can be configured up to a 32 MiB absolute limit. Supporting limits are 2 MiB each for verifier stdout and CTRF, and 1 MiB each for result, configuration, and exception evidence. The normal maximum retained bytes per trial is therefore 23 MiB; the absolute supported override is 71 MiB.

For JSONL transcripts:

- response bytes are read through a hard bounded body reader, then complete retained JSONL bytes are parsed line by line; the implementation does not claim true record-at-a-time streaming;
- each response body is read only to the requested cap plus one detection byte and then closed, including when an endpoint ignores `Range`;
- larger objects use newline-aligned head and tail ranges;
- only approved facts are retained: visible-content presence, tool name, definite workspace-change flag, terminal/stop/API status, API duration, usage components, thinking-event metadata count, synthetic retry, and refusal markers;
- bounded sanitized visible excerpts and tool names/workspace-change flags may be retained for the targeted manual packet; full assistant text, tool inputs, task content, configuration secrets, and hidden reasoning text are not persisted in checkpoints or outputs.

For trajectory, result, configuration, and CTRF JSON, the whole document must fit before parsing. Trajectory reasoning fields and secret configuration values—including primitive strings nested in arrays—are recursively redacted. Oversized or malformed structured documents become incomplete; they are never split into lines and treated as empty evidence.

The Python reader probes a remote range before deciding whether a full or head/tail read is possible. A verified remote `Content-Range` total takes precedence over stored `size_bytes`; tail offsets use that remote total. Stored/remote agreement is reported separately as `size_metadata_status`. A conflict prevents complete-evidence status even if all remote bytes were obtained. Completely read objects with expected SHA-256 metadata are verified against their immutable bytes.

Every read reports one of `complete`, `head_tail_only`, `truncated`, `unavailable`, or `malformed`. Positive evidence from retained head/tail records is usable, but absence-sensitive claims require complete transcript and trajectory evidence.

## Fact extraction

Extraction precedes classification. Independent facts include:

- database reward presence/value and independently parsed Harbor result reward presence/value;
- result-side exception, status, and termination fields plus database/result consistency;
- exception presence, type, and trusted markers;
- visible assistant events, tool calls, and definite workspace-changing calls;
- trajectory step count and explicitly substantive steps;
- final-result presence and emptiness;
- terminal reason, stop reason, API-error state, API duration, and total runtime;
- thinking-event metadata count, synthetic retry, and explicit refusal/category;
- verifier execution state, failure headline, and failure detail;
- per-artifact read completeness, canonical completeness, R2 indexing, read availability, analyzed-artifact integrity, and size-metadata consistency;
- separately sourced and sanitized database exception-summary presence and trusted markers;
- database telemetry presence/value and transcript usage records.

Step identifiers, timestamps, UUIDs, source labels, and other metadata alone do not count as substantive activity. File size is only a read-planning fact, never a behavioral classifier.

## Classification precedence

The rules are intentionally conservative:

1. Explicit provider-policy refusal sets policy disposition to `provider_policy_refusal` and execution validity to `policy_blocked`. If activity preceded the refusal, activity remains `substantive_agent_activity`; otherwise the activity subtype is `provider_policy_refusal`.
2. Timeout after meaningful activity becomes `timeout_after_meaningful_activity`. A timeout before retained meaningful activity keeps `termination_subtype=timeout`, but its activity and execution-validity axes remain unknown unless a separate trusted setup/transport marker is present.
3. Only trusted connection, authentication, rate-limit, service, network, transport, or setup markers produce `setup_or_transport_exception`. Other exceptions become `unclassified_exception`; `exception_after_substantive_activity` remains independently visible.
4. Meaningful visible/tool/structured activity outranks every empty-completion label.
5. A positive reward with complete no-activity evidence becomes `questionable_success_no_activity`.
6. Synthetic retry, thinking-only, long API-path, and zero-usage empty-completion labels require an explicitly empty final result and complete absence-sensitive evidence. These complete-evidence response failures use `execution_validity=invalid_response_path`; `invalid_transport_or_setup` is reserved for trusted setup/transport evidence.
7. Incomplete, malformed, duplicate, or head/tail-only evidence produces `activity_unknown` for absence claims.

Failure detail is separately classified from termination. CTRF status and bounded failure diagnostics supplement verifier stdout. Compile and wrong-output labels require specific evidence; generic “expected/got” text is not overclaimed as wrong output. A positive-reward timeout can therefore have verifier failure subtype `none` while termination subtype remains `timeout`.

## Telemetry normalization

Presence is never collapsed into numeric zero. Numeric strings are normalized, while null remains missing. Transcript components are tracked independently:

- uncached input;
- cache-read input;
- cache-creation input;
- output;
- cost;
- record identifier; and
- record mode: final aggregate, cumulative, or per-message.

Final aggregate usage outranks per-message records. When multiple terminal aggregate records exist, the last retained terminal aggregate wins; multi-model entries within one terminal aggregate are combined. Duplicate records are not double-counted. Cumulative records use the greatest retained cumulative total; unique per-message records are summed only when no aggregate exists. A transcript that terminates without a final aggregate is reported as partial telemetry rather than a decisive mismatch.

Database `input_tokens` is reconciled against transcript uncached input plus cache-read input plus cache-creation input. Database `cache_tokens` is reconciled against transcript cache-read input. Statuses distinguish:

- `consistent`;
- `database_missing_transcript_present`;
- `database_zero_transcript_nonzero`;
- `nonzero_mismatch`;
- `zero_usage_empty_completion`;
- `partial`;
- `incomplete_evidence`; and
- `unknown`.

The Fable refusal controls therefore report database-zero/transcript-nonzero, while GPT/Gemini empty controls with null database fields and explicit transcript zero report database missing, not database zero.

## Calibration controls

Compact synthetic tests reproduce the verified signatures without committing transcripts:

- a Kimi K3 substantive failure with assistant/tool activity after the former 512 KiB prefix boundary and verifier-detected extraneous output artifacts;
- a Kimi K3 substantive success with cache-inclusive token reconciliation;
- GPT synthetic-retry empty completion;
- Gemini long API-path empty completion;
- Gemini thinking-only empty completion;
- Fable policy refusal with explicit database zero and nonzero transcript usage;
- refusal and transport exceptions after prior activity;
- timeout after meaningful activity;
- positive reward with no activity;
- null reward and missing-versus-zero telemetry;
- tail-only and oversized evidence;
- ignored `Range`, UTF-8 partial-line boundaries, pretty trajectory JSON, metadata-only trajectory, duplicate artifacts, secret redaction, and displayed-URI sanitization.

The local sanitized calibration packet can be used for regression validation, but its large transcripts are never copied into Git.

The same committed redaction vectors run against the TypeScript preview redactor and Python generator redactor. They cover case variants; colon/equal assignments; quoted and unquoted values; empty or ambiguous assignments; 20–24-character credential-shaped values; repeated assignments; punctuation and line boundaries; shell/export and JSON-like fragments; nested arrays; multiline exception summaries; password-recovery excerpts; bearer and provider keys; cookie, session, password, token, credential, and signed-URL fields; URL userinfo; and secret query parameters. A `signed_url` assignment is removed as one complete value. Ordinary prose that merely mentions a password is retained. Redaction never alters immutable raw-download bytes.

Source-level parsing is not the security boundary. One shared recursive Python final-sink sanitizer is applied immediately before manual evidence is retained and again by every CSV/JSONL serializer. The TypeScript dashboard uses the equivalent final display sink for excerpts, evidence notes, exceptions, labels, and displayed paths/URIs. An independent strict scanner parses JSONL/JSON/CSV values and fails on non-redacted password assignments, supported credential patterns, or retained hidden-reasoning content; it reports filenames and rule names only, never candidate values.

## Confidence

- `high`: all classification-critical reads and canonical evidence are complete, unambiguous, and parse cleanly.
- `medium`: decisive positive evidence exists, but a non-absence-critical read is bounded or the selected artifact set is otherwise weakened.
- `low`: some required evidence is unavailable/malformed, artifact selection is ambiguous, or only incomplete evidence supports the diagnosis.
- `unknown`: all classification-critical evidence is unavailable.

Complete artifacts do not imply substantive execution. Conversely, positive tool evidence in a bounded segment can establish that activity occurred while remaining insufficient to establish what did not occur elsewhere.

## Manual-review queue, priorities, and controls

The queue includes every policy refusal, empty/thinking-only completion, synthetic retry, setup/transport exception, timeout, positive-reward exception, questionable success, activity-unknown case, telemetry/integrity mismatch, missing evidence case, verifier/environment failure, high-cost failure, low-confidence classification, and trial supporting a headline-level task disagreement.

Analyzer and generator priorities are combined without overwriting the analyzer decision: `high` outranks `medium`, which outranks `low`. Policy refusals, empty/thinking-only completions, synthetic retries, setup/transport exceptions, questionable successes, activity-unknown cases, positive-reward exceptions, unclassified exceptions, verifier/environment failures, and low/unknown-confidence cases are high priority. Timeouts, ordinary telemetry/integrity discrepancies, high-cost failures, task disagreements, and incomplete absence-sensitive evidence are at least medium priority.

Ordinary controls require substantive agent activity, no exception or timeout, no policy refusal, complete high-confidence evidence, and consistent telemetry. Separate deterministic strata cover timeouts, clean substantive telemetry mismatches, positive-reward exception or timeout terminations, and incomplete evidence. Diagnostic control strata may overlap when a positive-reward trial also timed out. Sampling uses a stable hash of trial ID and does not depend on database row order.

Task disagreement rows contain separate arm-specific raw, activity, policy, timeout, setup/transport, and verifier summaries. Their category is one of `capability_difference`, `policy_access_difference`, `timeout_reliability_difference`, `setup_or_transport_difference`, `verifier_environment_difference`, `mixed`, or `unresolved`; a combined counter is never presented as an explanation.

For dashboard filtering, the cached server-side snapshot index joins each disagreement's manifest-bound supporting trial IDs back to `trial_review.csv`. This produces exact per-arm `success`, `failure`, and `not_recorded` counts, so outcome filters do not infer failures from a count-only “N successes” label.

## Outputs

The generator writes:

- `run_review.csv`
- `trial_review.csv`
- `trial_evidence.jsonl`
- `review_queue.csv`
- `manual_control_sample.csv`
- `task_disagreement_review.csv`
- `arm_review_summary.csv`
- `review_coverage.json`
- `targeted_evidence_packet.csv`
- `targeted_evidence_bundle.jsonl`
- `targeted_evidence_bundle_manifest.json`
- `review_manifest.json`
- `README.md`

`review_manifest.json` binds schema/analyzer/generator versions, current analyzer and generator source hashes, generation timestamp, selected run IDs, a deterministic scope fingerprint, row counts, byte counts, and SHA-256 for every other output. The dashboard accepts only the exact output filename whitelist, rejects absolute/traversal names, validates every bound file before display, and reports unavailable, stale, or mixed-output states explicitly.

The ignored operational checkpoint stores only sanitized derived rows plus analyzer/generator versions, source hashes, and input fingerprints so interrupted reviews can resume without caching raw artifacts. It is never written under `results/`. Cold v1.3.1 generation does not reuse an earlier checkpoint. Output ordering is deterministic.

`targeted_evidence_packet.csv` is the safe index. `targeted_evidence_bundle.jsonl` contains one sanitized evidence record per selected trial: identity/classification, analyzer version, bounded visible activity excerpts, tool/workspace-change facts, bounded verifier output, structured CTRF names/status/failure messages, exception and approved result fields, artifact ID/type/read/completeness/hash status, evidence reasons, confidence, and explicit overlap strata. It includes every policy refusal, empty/synthetic/thinking-only case, positive-reward exception/timeout, canonical 7/9 case, audited v1.1.1 setup/transport and verifier/environment reclassification, extraneous-output case when reasonable, and revised ordinary control. Its own manifest binds index/bundle row counts, sizes, and SHA-256. Neither bundle contains configuration secrets or hidden reasoning.

The scope fingerprint binds the selected run IDs; every trial ID; every artifact ID, type, stored SHA-256, stored size, and R2-indexed flag; analyzer and generator source hashes; configured byte/time limits; generator options; and relevant selected-run metadata/configuration fingerprints. It proves which database metadata inventory, code, and configured reader behavior produced the derived snapshot. It does not prove unread object contents beyond stored metadata and any per-object digest actually verified during a complete analyzed read, nor does it attest to excluded runs or mutable external state after generation.

## Snapshot and live analysis

The manifest-validated generated snapshot is primary for every reviewed trial. Review files are loaded and indexed once per dashboard server process instead of reparsing `trial_review.csv` on each request. Bounded live R2 reanalysis is an optional, in-memory-cached comparison. If its axes differ from the snapshot, the trial page warns about the difference while keeping the validated snapshot primary until regeneration.

## Limitations and future reporting

- Router absence defaults to unknown. `not_retained` requires explicit run metadata or a documented retention contract.
- Definite workspace-change detection is conservative, especially for arbitrary shell commands.
- Verifier text can identify common failure details but cannot always distinguish model, environment, or verifier defects without manual review.
- Bounded reads deliberately trade exhaustive oversized-artifact inspection for predictable cost and safety.
- Provider-policy rules and retained telemetry can change; analyzer version must accompany every derived row.
- Raw reward remains the historical end-to-end result.

Future aggregate views may separately show raw end-to-end pass rate, execution-qualified pass rate, and inference-conditioned capability rate. This implementation does not calculate or substitute those rates.
