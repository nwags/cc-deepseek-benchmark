# Kimi K3 Addendum Summary — 2026-07-22

## Status

Kimi K3 was added as a post-Phase-3 addendum arm on the Phase-3-compatible router harness.

- Branch: `kimi-k3-addendum`
- Arm: `router-kimi-k3`
- Logical mode: full sweep
- GitHub Actions run: `29944035055`
- Result path: `results/phase3/raw/arm-router-kimi-k3/2026-07-22__17-51-05/result.json`
- Artifact: `benchmark-router-kimi-k3-full-29944035055`

## Full-sweep outcome

- Trials: 60
- Successes: 47
- Raw success rate: 78.33%
- Failures: 13
- Exceptions: 11

Exception breakdown:

| Exception Type | Count |
|---|---:|
| AgentTimeoutError | 10 |
| NonZeroAgentExitCodeError | 1 |

Outcome breakdown:

| Outcome Class | Count |
|---|---:|
| Clean success | 44 |
| Exception with success signal | 3 |
| Clean failure | 5 |
| Exception failure | 8 |

## Task-level summary

| Task | Successes | Trials | Exceptions |
|---|---:|---:|---:|
| build-cython-ext | 3 | 3 | 0 |
| cancel-async-tasks | 3 | 3 | 2 |
| configure-git-webserver | 2 | 3 | 0 |
| custom-memory-heap-crash | 2 | 3 | 1 |
| fix-code-vulnerability | 3 | 3 | 0 |
| git-leak-recovery | 3 | 3 | 0 |
| llm-inference-batching-scheduler | 1 | 3 | 1 |
| model-extraction-relu-logits | 2 | 3 | 1 |
| modernize-scientific-stack | 3 | 3 | 0 |
| mteb-retrieve | 3 | 3 | 0 |
| multi-source-data-merger | 3 | 3 | 0 |
| nginx-request-logging | 3 | 3 | 0 |
| openssl-selfsigned-cert | 3 | 3 | 0 |
| password-recovery | 3 | 3 | 0 |
| polyglot-rust-c | 0 | 3 | 1 |
| portfolio-optimization | 3 | 3 | 0 |
| query-optimize | 2 | 3 | 0 |
| schemelike-metacircular-eval | 0 | 3 | 3 |
| sqlite-db-truncate | 3 | 3 | 0 |
| torch-pipeline-parallelism | 2 | 3 | 2 |

## Cost accounting

Kimi K3 artifacts contained token metadata and partial observed cost metadata. Ten timeout trials had token metadata but missing observed `cost_usd`, so official cost recomputation is required.

Cost recomputation artifact:

- `results/phase3/reporting/kimi_k3_full_cost_recompute_20260722.tsv`

Summary:

| Cost Field | Amount |
|---|---:|
| Trial observed non-NA sum | $25.207213 |
| Official K3 estimate, assuming `n_input_tokens` includes cache hits | $26.570403 |
| Official K3 estimate, assuming `n_input_tokens` excludes cache hits | $129.497763 |
| Missing observed trial costs | 10 |

Working interpretation:

- Use the official includes-cache recomputation as the primary working estimate.
- Preserve the excludes-cache recomputation as an upper-bound interpretation until Harbor/Claude Code token semantics are fully settled.
- Preserve observed artifact costs separately because observed cost does not cleanly match official Kimi K3 pricing.

## Interpretation

Kimi K3 appears highly competitive on raw benchmark quality in this addendum run:

- 47/60 raw successes.
- 44 clean successes.
- 3 timeout trials still had success signals.

However, the arm also showed meaningful timeout behavior:

- 10 AgentTimeoutError trials.
- 8 exception failures.
- 10 missing observed-cost trials.

The run should be reported as a Phase-3-compatible addendum, not as a formal Phase 4 result.
