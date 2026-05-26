# Analysis

This Phase 2 analysis uses `results/phase2/combined.csv`, produced by:

```bash
uv run python scripts/aggregate_phase2.py
```

The current Phase 2 `combined.csv` has shape `300 x 51`. It includes the assignment Section 6.4-style metrics for success, timing, tokens, cost, agent turns, tool calls, Bash calls, edit/write calls, read/search calls, repeated Bash commands, observed model metadata, exception type, and rule-assisted failure mode.

Phase 1 remains frozen in `results/combined.csv`; it should be used only as the baseline comparator. Phase 2 scored results use `results/phase2/combined.csv` as the source of truth. Smoke and canary outputs are not part of the 300-trial scored Phase 2 matrix.

## 1. Data validation

| Item | Validation result | Comment |
| --- | --- | --- |
| `results/phase2/combined.csv` | 300 rows x 51 columns | matches 20 tasks x 3 attempts x 5 scored arms |
| Scored arms | 5 | Haiku, Sonnet, Opus, DeepSeek Pro, DeepSeek Flash |
| Trials per scored arm | Anthropic Haiku=60, Anthropic Sonnet=60, Anthropic Opus=60, DeepSeek V4-Pro=60, DeepSeek V4-Flash=60 | all scored arms have 60 trials |
| Smoke/canary outputs | `results/phase2/smoke/`, `results/phase2/canary/` if present | kept separate from full scored aggregate |

## 2. Quality

| Arm | Successes | Trials | Success % | Wilson CI low % | Wilson CI high % |
| --- | --- | --- | --- | --- | --- |
| Anthropic Haiku | 26 | 60 | 43.3 | 31.6 | 55.9 |
| Anthropic Sonnet | 40 | 60 | 66.7 | 54.1 | 77.3 |
| Anthropic Opus | 45 | 60 | 75 | 62.8 | 84.2 |
| DeepSeek V4-Pro | 39 | 60 | 65 | 52.4 | 75.8 |
| DeepSeek V4-Flash | 35 | 60 | 58.3 | 45.7 | 69.9 |

The Wilson intervals overlap across several neighboring arms. The safest interpretation is descriptive rather than leaderboard-style: Opus led this Phase 2 sweep, Sonnet and DeepSeek Pro were close, Flash remained competitive at very low cost, and Haiku was substantially weaker on this task mix.

### Per-task success rate

| Task | Anthropic Haiku | Anthropic Sonnet | Anthropic Opus | DeepSeek V4-Pro | DeepSeek V4-Flash |
| --- | --- | --- | --- | --- | --- |
| build-cython-ext | 33.3 | 100 | 100 | 100 | 100 |
| cancel-async-tasks | 33.3 | 0 | 33.3 | 66.7 | 66.7 |
| configure-git-webserver | 0 | 100 | 100 | 100 | 100 |
| custom-memory-heap-crash | 66.7 | 100 | 100 | 100 | 100 |
| fix-code-vulnerability | 100 | 100 | 100 | 100 | 100 |
| git-leak-recovery | 100 | 100 | 66.7 | 66.7 | 100 |
| llm-inference-batching-scheduler | 0 | 66.7 | 100 | 66.7 | 66.7 |
| model-extraction-relu-logits | 0 | 33.3 | 33.3 | 33.3 | 0 |
| modernize-scientific-stack | 100 | 100 | 100 | 66.7 | 66.7 |
| mteb-retrieve | 0 | 0 | 0 | 0 | 0 |
| multi-source-data-merger | 100 | 100 | 100 | 66.7 | 66.7 |
| nginx-request-logging | 100 | 100 | 100 | 100 | 100 |
| openssl-selfsigned-cert | 66.7 | 100 | 0 | 100 | 100 |
| password-recovery | 0 | 100 | 100 | 0 | 0 |
| polyglot-rust-c | 0 | 0 | 0 | 0 | 0 |
| portfolio-optimization | 100 | 100 | 100 | 100 | 66.7 |
| query-optimize | 33.3 | 33.3 | 66.7 | 66.7 | 33.3 |
| schemelike-metacircular-eval | 0 | 0 | 100 | 66.7 | 0 |
| sqlite-db-truncate | 33.3 | 100 | 100 | 100 | 100 |
| torch-pipeline-parallelism | 0 | 0 | 100 | 0 | 0 |

### Divergent tasks

| Task | Anthropic Haiku | Anthropic Sonnet | Anthropic Opus | DeepSeek V4-Pro | DeepSeek V4-Flash | Range | Why interesting |
| --- | --- | --- | --- | --- | --- | --- | --- |
| configure-git-webserver | 0 | 100 | 100 | 100 | 100 | 100 | Multi-service setup task; Haiku was the only arm to fail all attempts. |
| password-recovery | 0 | 100 | 100 | 0 | 0 | 100 | Exact-output forensic task; Anthropic higher-tier arms solved while DeepSeek/Haiku failed. |
| torch-pipeline-parallelism | 0 | 0 | 100 | 0 | 0 | 100 | Specialized ML systems task; Opus was the only full-success arm. |
| llm-inference-batching-scheduler | 0 | 66.7 | 100 | 66.7 | 66.7 | 100 | AI infrastructure scheduling task; Opus solved all attempts, Haiku none. |
| schemelike-metacircular-eval | 0 | 0 | 100 | 66.7 | 0 | 100 | Symbolic interpreter task; Opus and DeepSeek Pro were strongest. |
| openssl-selfsigned-cert | 66.7 | 100 | 0 | 100 | 100 | 100 | Dependency/environment-awareness task; Opus failed due to unavailable dependency assumption. |
| build-cython-ext | 33.3 | 100 | 100 | 100 | 100 | 66.7 | Compiled scientific Python migration; Haiku struggled while others solved. |
| sqlite-db-truncate | 33.3 | 100 | 100 | 100 | 100 | 66.7 | Database recovery/truncation; Haiku weak while others solved. |
| cancel-async-tasks | 33.3 | 0 | 33.3 | 66.7 | 66.7 | 66.7 | Async cancellation edge cases; DeepSeek arms outperformed Sonnet. |

## 3. Speed

| Arm | Median wall s | Mean wall s | Median agent exec s | Mean agent exec s |
| --- | --- | --- | --- | --- |
| Anthropic Haiku | 154.7 | 303.9 | 76.6 | 177.9 |
| Anthropic Sonnet | 259.3 | 490.6 | 145.4 | 382.7 |
| Anthropic Opus | 246.8 | 459 | 118 | 329.4 |
| DeepSeek V4-Pro | 566.6 | 688.2 | 409.8 | 559.3 |
| DeepSeek V4-Flash | 283.4 | 492.8 | 179.6 | 367.1 |

Haiku was fastest by median wall-clock time but had the lowest quality. Opus and Sonnet were similar in median wall-clock. DeepSeek Pro was slowest, and its slowdown was concentrated in the agent/model execution phase. DeepSeek Flash was closer to Anthropic speed than Pro.

### Success/failure speed split

| Arm | Outcome | Trials | Median seconds | Mean seconds | Total cost $ |
| --- | --- | --- | --- | --- | --- |
| Anthropic Haiku | Failed | 34 | 337.1 | 370.4 | 10.8602 |
| Anthropic Haiku | Succeeded | 26 | 104.2 | 216.8 | 3.4504 |
| Anthropic Opus | Failed | 15 | 422 | 416.3 | 8.7317 |
| Anthropic Opus | Succeeded | 45 | 228.8 | 473.2 | 42.1965 |
| Anthropic Sonnet | Failed | 20 | 633.9 | 864.8 | 10.1513 |
| Anthropic Sonnet | Succeeded | 40 | 135.3 | 303.5 | 18.2116 |
| DeepSeek V4-Flash | Failed | 25 | 815.5 | 739.2 | 0.3003 |
| DeepSeek V4-Flash | Succeeded | 35 | 245.2 | 316.9 | 0.4158 |
| DeepSeek V4-Pro | Failed | 21 | 938.8 | 910.3 | 0.5831 |
| DeepSeek V4-Pro | Succeeded | 39 | 367.5 | 568.6 | 1.1296 |

Failed runs are often slower because they loop, reach timeout, or discover verifier issues late. This means raw wall-clock medians should be interpreted together with the success/failure split.

## 4. Cost

| Arm | Total cost $ | Cost / successful trial $ | Tasks solved >=1 | Cost / resolved task $ |
| --- | --- | --- | --- | --- |
| Anthropic Haiku | 14.3106 | 0.5504 | 12 | 1.1926 |
| Anthropic Sonnet | 28.3629 | 0.7091 | 15 | 1.8909 |
| Anthropic Opus | 50.9282 | 1.1317 | 17 | 2.9958 |
| DeepSeek V4-Pro | 1.7127 | 0.0439 | 16 | 0.1070 |
| DeepSeek V4-Flash | 0.7161 | 0.0205 | 14 | 0.0512 |

DeepSeek remains the clearest economic result. DeepSeek Pro was close to Sonnet on quality at a tiny fraction of the cost, and DeepSeek Flash was even cheaper while remaining moderately competitive. Haiku was cheaper than Sonnet/Opus in absolute terms, but its lower success rate makes its cost-per-success less compelling than the raw spend suggests.

## 5. Agent turns, tool calls, and failure modes

| Arm | Median agent turns | Median tool calls | Median Bash calls | Mean agent turns | Mean tool calls |
| --- | --- | --- | --- | --- | --- |
| Anthropic Haiku | 11 | 12 | 7.5 | 21.8 | 22.5 |
| Anthropic Sonnet | 9 | 11 | 6.5 | 15.5 | 19.4 |
| Anthropic Opus | 12 | 10.5 | 8 | 18.9 | 18.5 |
| DeepSeek V4-Pro | 12 | 14.5 | 7.5 | 16.1 | 24 |
| DeepSeek V4-Flash | 11 | 15.5 | 7.5 | 14.4 | 20.6 |

Tool-call volume is a property of the whole Claude Code loop, not just the backend model. Higher tool-call counts did not automatically produce higher quality. DeepSeek arms tended to use more tools, while Opus achieved the highest quality with relatively modest median turn/tool counts.

### Failure modes

| Arm | Success | Produced wrong output | Timed out | Looped | Refused-to-try | Ran out of budget |
| --- | --- | --- | --- | --- | --- | --- |
| Anthropic Haiku | 26 | 23 | 0 | 9 | 2 | 0 |
| Anthropic Sonnet | 40 | 14 | 6 | 0 | 0 | 0 |
| Anthropic Opus | 45 | 14 | 1 | 0 | 0 | 0 |
| DeepSeek V4-Pro | 39 | 10 | 11 | 0 | 0 | 0 |
| DeepSeek V4-Flash | 35 | 10 | 14 | 1 | 0 | 0 |

Most failures were verifier failures (`produced-wrong-output`) or timeouts. DeepSeek Pro and Flash had more timeout behavior than the Anthropic higher-tier arms. Haiku showed several loop-classified failures and two refused/setup-style failures.

### Exception counts

| Arm | AgentTimeoutError | NonZeroAgentExitCodeError | RuntimeError | none |
| --- | --- | --- | --- | --- |
| Anthropic Haiku | 1 | 0 | 0 | 59 |
| Anthropic Sonnet | 5 | 2 | 0 | 53 |
| Anthropic Opus | 3 | 0 | 1 | 56 |
| DeepSeek V4-Pro | 9 | 3 | 0 | 48 |
| DeepSeek V4-Flash | 5 | 9 | 0 | 46 |

## 6. Observed model metadata

| Arm | Observed model | Trials |
| --- | --- | --- |
| Anthropic Haiku | claude-haiku-4-5-20251001 | 60 |
| Anthropic Opus | claude-opus-4-7 | 59 |
| Anthropic Opus | missing | 1 |
| Anthropic Sonnet | claude-sonnet-4-6 | 60 |
| DeepSeek V4-Flash | deepseek-v4-flash | 55 |
| DeepSeek V4-Flash | missing | 5 |
| DeepSeek V4-Pro | deepseek-v4-pro[1m] | 57 |
| DeepSeek V4-Pro | missing | 3 |

Missing observed-model rows correspond to exception trials that did not produce normal model transcript metadata. They are best treated as missing log metadata rather than evidence that a different model was used.

## 7. Qualitative transcript review of divergent tasks


### 7.1 `schemelike-metacircular-eval`: Opus and DeepSeek Pro advantage on symbolic interpreter work

Outcome: Haiku 0/3, Sonnet 0/3, Opus 3/3, DeepSeek Pro 2/3, DeepSeek Flash 0/3.

This was one of the most diagnostic symbolic-programming tasks. The task requires writing `eval.scm`, a metacircular evaluator for a Scheme-like interpreter. Opus solved all three attempts. DeepSeek Pro solved two attempts and nearly solved another, with a failed verifier showing 60 of 63 interpreter tests passing before timeout. Sonnet and Flash failed all attempts, mostly through timeout or missing final output, while Haiku's failures were loop-classified. This looks like a capability-plus-trajectory issue, not an Anthropic-compatible API issue.

Hedge-fund workflow alignment: low to medium directly, but relevant by analogy to strategy DSLs, rule engines, internal research languages, and query/interpreter-like systems.

### 7.2 `cancel-async-tasks`: DeepSeek advantage on async cancellation edge cases

Outcome: Haiku 1/3, Sonnet 0/3, Opus 1/3, DeepSeek Pro 2/3, DeepSeek Flash 2/3.

This task asks for bounded async task execution plus correct cancellation behavior. The divergence suggests that the DeepSeek arms were more likely to find a working operational pattern for cancellation and cleanup. The failure pattern is consistent with a classic async gotcha: a superficially correct semaphore/gather implementation can still create too many queued tasks or fail to drain cleanup correctly.

Hedge-fund workflow alignment: high. Async cancellation, bounded concurrency, and cleanup under interruption map directly to market-data ingestion, websocket consumers, streaming analytics, order-routing services, and batch orchestration.

### 7.3 `openssl-selfsigned-cert`: Opus dependency-assumption failure

Outcome: Haiku 2/3, Sonnet 3/3, Opus 0/3, DeepSeek Pro 3/3, DeepSeek Flash 3/3.

This was one of the clearest Phase 2 surprises. Opus was strongest overall but failed all three attempts on this task. The verifier output showed that certificate artifacts were present and several structural tests passed, but the generated `check_cert.py` imported `cryptography`, which was not installed in the container. This is an environment-awareness and dependency-assumption failure, not a generic reasoning-depth failure.

Hedge-fund workflow alignment: medium to high. Internal certificates, TLS, service identity, and platform security are relevant to hedge-fund infrastructure.

### 7.4 `password-recovery`: Anthropic Opus/Sonnet advantage on forensic exactness

Outcome: Haiku 0/3, Sonnet 3/3, Opus 3/3, DeepSeek Pro 0/3, DeepSeek Flash 0/3.

This task rewards exact recovery and exact output formatting. Sonnet and Opus solved all attempts. Haiku often failed to produce the recovery file or produced incorrect candidate lists. DeepSeek Pro timed out or wrote partial/incorrect candidates. DeepSeek Flash included a particularly informative exact-output failure: it wrote the correct password content with a `PASSWORD=` prefix when the verifier expected the raw password string.

Hedge-fund workflow alignment: medium. This resembles incident response, credential recovery, file forensics, and security operations.

### 7.5 `torch-pipeline-parallelism`: Opus-only success on specialized ML systems work

Outcome: Haiku 0/3, Sonnet 0/3, Opus 3/3, DeepSeek Pro 0/3, DeepSeek Flash 0/3.

This task was a major Phase 2 differentiator. In Phase 1 all arms struggled with it. In Phase 2, Opus solved all three attempts while every other scored arm failed all attempts. It likely measures a mix of PyTorch knowledge, systems design, and careful hidden-test adherence.

Hedge-fund workflow alignment: medium to high for ML infrastructure teams, but specialized.

### 7.6 `llm-inference-batching-scheduler`: Opus robustness on scheduling/optimization

Outcome: Haiku 0/3, Sonnet 2/3, Opus 3/3, DeepSeek Pro 2/3, DeepSeek Flash 2/3.

This task is highly relevant to AI infrastructure. Opus solved all attempts. Sonnet, DeepSeek Pro, and DeepSeek Flash each solved two attempts. Haiku solved none. The task rewards correct schema/coverage and performance-aware scheduling.

Hedge-fund workflow alignment: high. Batched inference scheduling is directly relevant to AI-native research platforms, internal LLM services, and cost/latency control.

## 8. Patterns from the qualitative review

1. **Opus was the strongest overall Phase 2 model and uniquely solved some hard tasks.** `torch-pipeline-parallelism` and `schemelike-metacircular-eval` were the most striking examples.
2. **DeepSeek Pro remained close to Sonnet quality at far lower cost but slower latency.** Its strongest results were on sustained reasoning and several infrastructure tasks, though it timed out more often.
3. **Flash remained economically attractive.** It was weaker than Pro/Sonnet/Opus overall but very cheap and surprisingly competitive on compact operational fixes.
4. **Haiku was fast but materially weaker.** Its failures on service orchestration, compiled scientific Python, and scheduling tasks suggest it should be used with escalation.
5. **Exact-output and dependency-awareness failures matter.** Some failures were not conceptual failures but mismatches against hidden verifier contracts or container dependency constraints.

## 9. Phase 2 conclusion

Phase 2 supports a differentiated backend strategy rather than a single universal replacement. Opus is the highest-quality option in this run. Sonnet remains a strong balanced control. DeepSeek Pro is close to Sonnet quality at dramatically lower cost but with much slower runtime. DeepSeek Flash is extremely cheap and useful for low-cost exploration or suitable task classes. Haiku is fast, but the quality drop is large on difficult terminal-engineering tasks. The next natural research step is Phase 3 router-mediated Claude Code provider expansion followed by later agent-harness and plan-execute studies.
