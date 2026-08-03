# Artifact Evidence and Trial Diagnosis

This guide explains how to investigate Phase 3 benchmark evidence without changing historical rewards, pass rates, denominators, quality flags, or stored artifacts. The dashboard diagnoses described here are read-only, derived interpretations. They support manual review; they are not replacements for the immutable Harbor result.

## Evidence levels

Harbor evidence has two directory and database scopes.

```text
run-root/
├── config.json
├── run.lock
├── job.log
├── result.json
└── task-attempt/
    ├── config.json
    ├── trial.log
    ├── agent/
    │   ├── claude-code.txt
    │   └── trajectory.json
    ├── exception.txt              # only when explicitly retained
    ├── verifier/
    │   ├── test-stdout.txt
    │   ├── ctrf.json
    │   └── reward.txt
    └── result.json
```

The common run-root set is `config`, `lock`, `log`, and `result`. The canonical normal-trial set is:

```text
agent_transcript
config
log
result
trajectory
verifier_ctrf
verifier_reward
verifier_stdout
```

That is an 8/8 trial. If an explicit `exception` artifact is attached, the expected set becomes 9/9. An `exception_type` field does not guarantee that an `exception.txt` artifact was retained, so the dashboard reports that discrepancy rather than inventing evidence.

Router logs and router-log slices are a separate observability scope. They are not part of the historical canonical eight-artifact contract.

## Generation lifecycle

The typical trial evidence lifecycle is:

```text
config
  ↓
trial.log: environment and agent setup
  ↓
claude-code.txt: visible CLI/model/tool stream
  ↓
trajectory.json: structured behavior
  ↓
optional exception.txt branch
  ↓
verifier/test-stdout.txt
  ↓
verifier/ctrf.json
  ↓
verifier/reward.txt
  ↓
trial result.json
```

Claude Code communicates with a provider through a router in Phase 3. Router/provider evidence therefore forms a parallel observability lane between Claude Code and the provider. Historical LiteLLM logs were not retained for every request window, but absence alone is not proof of non-retention. The default is `unknown`; `not_retained` is used only when run metadata or an explicit historical retention contract proves it. Router status never reduces canonical Harbor completeness.

## Recommended reading order

1. `result.json` — establish the recorded outcome, termination, telemetry, and exception metadata.
2. `claude-code.txt` — determine whether visible assistant content, tool calls, retries, or refusal markers exist.
3. `verifier/test-stdout.txt` — understand why the final workspace passed or failed.
4. `trajectory.json` — cross-check structured activity and empty steps.
5. `config.json` — audit task, route alias, timeouts, tools, environment, and verifier settings.
6. `trial.log` — inspect setup, execution timing, and harness/infrastructure context.
7. `exception.txt`, when present — identify abnormal termination or policy refusal.
8. `ctrf.json` and `reward.txt` — confirm structured tests and the raw score.
9. Router evidence, when retained — examine request routing, latency, retries, or provider response metadata.

Claude Code transcript subtype `success` means the CLI terminated without a surfaced process or API exception. It does not mean the benchmark passed, and it does not prove useful agent work occurred. Similarly, complete artifacts prove retention completeness, not substantive execution.

## Evidence triangles

Use three overlapping evidence triangles rather than relying on one file:

| Question | Evidence triangle |
|---|---|
| Outcome | Harbor result → reward → verifier |
| Activity | Claude Code transcript → trajectory → verifier result |
| Infrastructure | Configuration → trial log → exception/router evidence |

A strong diagnosis makes all three internally consistent or explicitly documents the mismatch.

## Quick triage routine

1. Record raw reward without altering it.
2. Check whether the trial and run are valid, invalid, or quarantined under existing metadata.
3. Check canonical artifact completeness, R2 indexing, R2 read availability, object integrity, and stored/remote size consistency separately.
4. Check router observability separately.
5. Look for explicit provider-policy refusal markers before classifying a no-activity failure as transport invalid.
6. Count visible assistant events and tool calls. Thinking-event counts may be recorded, but hidden thinking/reasoning text is neither retained by the analyzer nor shown.
7. Compare transcript-reported usage with database/result telemetry. Preserve field presence separately from numeric zero, and include uncached, cache-read, and cache-creation input in the transcript total.
8. Read verifier stdout to determine the final workspace failure.
9. Audit task commit, model alias, resolved model metadata, Claude Code version, route endpoint, timeout multipliers, disallowed tools, and verifier configuration.
10. Lower confidence when required reads are unavailable, malformed, truncated, or head-and-tail only. Never infer absence from an uninspected middle segment.

## Bounded reader and display safety

Artifact analysis is server-side and type aware:

- JSONL response bytes are read through a hard bounded body reader up to an 8 MiB default cap, configurable to a 32 MiB absolute per-artifact bound, and then parsed as JSONL. This is not record-at-a-time network streaming. A response is stopped after the byte cap even if it ignores `Range`.
- Larger JSONL streams use newline-aligned bounded head and tail segments. Positive events found there remain evidence; absence-sensitive conclusions become unknown because the middle was not inspected.
- Trajectory JSON is parsed as one complete document when it fits. Oversized or malformed trajectory JSON becomes incomplete rather than being line-parsed or treated as empty.
- Result, configuration, and CTRF JSON are parsed only inside their type-specific complete-read limits. Verifier and exception text have separate bounds.
- One deterministic artifact per required type is read, with duplicate types marked ambiguous. The default per-trial retained-byte ceiling is 23 MiB; the absolute supported override remains bounded at 71 MiB.

Both the dashboard live reader and generator prefer a verified remote `Content-Range` total over stored `size_bytes`, use that remote total for tail offsets, and report conflicts as `size_metadata_status`. Malformed range metadata is not treated as a verified total, and an ignored `Range` response is still hard-capped. A size conflict cannot produce complete evidence. For completely read analyzed objects with an expected digest, SHA-256 is verified. URI presence is only indexing evidence; it is never described as read availability or integrity.

Database `exception_summary` is a separate metadata source. It is recursively/free-text redacted before retention, contributes only trusted refusal, timeout, and transport markers to those diagnoses, and is fingerprinted so a changed summary invalidates live and checkpoint caches. A generic summary proves only that an exception was recorded; it cannot establish a setup/transport failure.

Configuration previews recursively redact API keys, auth tokens and headers, access/secret keys, database URLs, signed URL values, URL userinfo, secret query parameters, and credential-shaped environment values, including primitive strings inside nested arrays. Exception summaries, tooltips, artifact detail, trial, run, and live-run free text use the same secret redaction. Every retained excerpt, CTRF name/message, exception/result string, evidence reason, label, and displayed path/URI is sanitized again at the final output/display sink; source-level redaction alone is not trusted. Password/passwd assignments cover quoted, unquoted, repeated, shell/export, JSON-like, empty/ambiguous, punctuation-delimited, and nested-array forms while ordinary unassigned password prose remains visible. Safe host, port, path, model/deployment, timeout, and version context remains visible. These transformations apply only to display and derived output; immutable raw-download response bytes are unchanged.

## Classification matrix

These labels are derived and conservative.

| Activity subtype | Evidence signature | Execution interpretation |
|---|---|---|
| `substantive_agent_activity` | Visible assistant content, tools, or a substantive structured step | Substantive |
| `empty_completion_zero_usage` | Empty result, no visible content, no tools, zero usage | Invalid response path; no transport cause is inferred |
| `empty_completion_after_long_api_path_wait` | Complete no-activity evidence and an empty result after a long retained API-path duration | Invalid response path; does not assign latency to the provider alone |
| `thinking_only_empty_completion` | Thinking-event metadata but no visible output or tools | Invalid response path; never display thinking content |
| `synthetic_retry_empty_completion` | Claude Code emitted its empty-response retry prompt and the retry remained empty | Invalid response path |
| `provider_policy_refusal` | Explicit refusal marker/category, commonly with API-error termination | Policy blocked, not transport invalid; policy remains visible even after prior activity |
| `setup_or_transport_exception` | Trusted setup/transport exception, including cases with prior activity | Invalid transport/setup; prior activity remains an independent fact |
| `timeout_after_meaningful_activity` | Timeout after visible messages or tools | Substantive attempt that timed out |
| `telemetry_missing_activity_present` | Substantive activity and transcript usage, but database usage is missing/zero | Substantive; telemetry inconsistent |
| `questionable_success_no_activity` | Positive reward but no visible activity | Questionable; manual review required |
| `activity_unknown` | Evidence unavailable or insufficient | Unknown |

An exception without a trusted policy, timeout, connection, authentication, rate-limit, service, network, transport, or setup marker is `unclassified_exception`, not setup/transport. `exception_after_substantive_activity` records whether meaningful activity preceded it.

Other useful outcomes include substantive failure, verifier/environment failure, telemetry mismatch, and unknown. These are expressed through the separate raw-outcome, execution-validity, telemetry, evidence, and exception fields rather than collapsed into one overloaded status.

Failure detail is separately derived as `missing_required_output`, `compile_failure`, `test_assertion_failure`, `wrong_output`, `extraneous_output_artifacts`, `verifier_or_environment_failure`, `policy_refusal`, `timeout`, or `unknown_failure`. Termination subtype is a different axis. CTRF supplements verifier stdout conservatively; generic expected/actual wording is not enough to overclaim wrong output or compilation failure. A failure subtype never replaces the raw reward.

## Separate interpretation axes

The trial page deliberately separates:

- **Raw outcome:** direct success/failure from the stored reward, or `not_recorded` when reward is null.
- **Execution validity:** substantive, invalid response path, invalid transport/setup, policy blocked, questionable, or unknown. Invalid transport/setup requires trusted transport or setup evidence.
- **Policy disposition:** no refusal detected, provider-policy refusal, or unknown.
- **Activity subtype:** the conservative behavior signature listed above.
- **Evidence completeness:** canonical files expected versus present.
- **Storage completeness:** canonical files indexed in R2 versus expected.
- **R2 read availability:** whether selected analysis objects were actually readable within bounds.
- **Analyzed-artifact integrity:** verified, not verifiable, partial, unavailable, or mismatched SHA-256 state for only the bounded objects the analyzer actually read. It is not a claim about every canonical object.
- **Size metadata consistency:** stored-versus-remote size agreement for the analyzed objects, independent from indexing and digest integrity.
- **Size metadata:** stored and remote totals consistent, partial/unknown, or conflicting.
- **Result consistency:** database reward versus independently parsed allow-listed Harbor result reward. Database reward remains the raw source of truth.
- **Telemetry status:** consistent, database missing with transcript present, database zero with transcript nonzero, nonzero mismatch, zero-usage empty completion, partial, incomplete evidence, or unknown.
- **Router observability:** retained, not retained, or unknown.

These axes support three different reporting views:

1. **Raw benchmark interpretation** uses every stored reward and preserves the historical denominator.
2. **Execution-qualified interpretation** may separately identify attempts without substantive execution, but must state its rule and denominator.
3. **Inference-conditioned interpretation** may exclude provider-policy blocks or requests that never reached usable inference. It must not silently replace raw results.

## Known pattern examples

The following generalized examples are encoded in deterministic tests without copying private or hidden reasoning:

- A frontier-model route returned two empty completions. Each trial retained all eight canonical artifacts, recorded no tools or workspace changes, and included a Claude Code synthetic retry that was also empty. This maps to `synthetic_retry_empty_completion`.
- A fast-model route returned an empty completion after a long end-to-end API-path wait with no tools and explicit zero transcript usage. This maps to `empty_completion_after_long_api_path_wait`; without retained router timing, it is not called a provider-only wait.
- Another trial from that route emitted thinking-token event metadata but no visible assistant content or tools. This maps to `thinking_only_empty_completion`. Only the event count may be shown.
- A provider route explicitly emitted `model_refusal_no_fallback` with a cyber refusal category and API-error terminal state. This maps to `provider_policy_refusal`. Its database token fields were explicit zero while the transcript reported nonzero uncached, cache-read, cache-creation, and output usage, so telemetry is independently `database_zero_transcript_nonzero`.
- A Kimi K3 near miss performed visible assistant work and five tool calls, produced the requested source plus generated binaries, and failed because the verifier expected only the source file. Cache-inclusive transcript input exactly reconciled with database input. This is high-confidence `substantive_agent_activity` with `extraneous_output_artifacts`, not an empty or telemetry-missing attempt.

These examples show why “reward 0,” “no activity,” and “zero database tokens” cannot be treated as one failure mode.

## Configuration and comparability

The trial page extracts only supported, non-secret facts from bounded evidence previews:

- task repository, commit, checksum when recorded, and path;
- requested model alias and resolved model metadata when available;
- Claude Code version;
- router endpoint or deployment identifier when recorded;
- timeout multipliers;
- disallowed tools;
- verifier enablement/configuration; and
- run timestamp.

Authentication tokens, API keys, credentials, and secret environment values are omitted. A route port or deployment difference is comparability context, not automatic proof of unfairness. Requested model aliases also do not, by themselves, prove the provider-resolved backend.

## Automated-analysis limits

- Analysis uses bounded server-side typed reads. No browser receives R2 credentials or directly reads R2.
- Required reads that are missing, malformed, truncated, head-and-tail only, or duplicated reduce confidence.
- Hidden reasoning is neither interpreted nor displayed. Thinking-event counts are metadata only.
- File size is never sufficient for classification; it can only be a supporting hint.
- Shell workspace-change detection is intentionally conservative and cannot prove every side effect.
- Artifact completeness does not prove substantive model work.
- Absence of router evidence defaults to unknown. Proven historical non-retention remains separate from request and canonical-artifact status.
- A verifier failure can reflect the model solution, environment, or verifier; human review remains necessary.
- Derived labels never mutate raw rewards, stored quality flags, run validity, or benchmark denominators.
- The manifest-validated generated snapshot is primary for reviewed trials. Optional cached live reanalysis is visibly separate, and differences produce a warning rather than silently replacing the snapshot.
- Shared TypeScript/Python redaction vectors cover mixed-case secret assignments, nested arrays, multiline exception summaries, signed URLs, URL userinfo, bearer/provider keys, and common cookie/session/password/credential fields. A strict parsed-output audit independently rejects remaining password assignments, supported credential patterns, and hidden-reasoning content without logging candidate values. Redaction affects previews and derived outputs only; immutable download bytes are unchanged.

The reusable corpus process and generated output contract are documented in [COMPREHENSIVE_EVIDENCE_REVIEW_METHOD.md](COMPREHENSIVE_EVIDENCE_REVIEW_METHOD.md). Aggregate raw, execution-qualified, and inference-conditioned rates are possible future views; this implementation deliberately does not alter or replace existing aggregate rates.
