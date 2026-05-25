# Findings

## 1. Did the quality hypothesis hold?

Partly yes. DeepSeek V4-Pro matched or slightly exceeded Anthropic Sonnet in raw success rate on this 20-task Terminal-Bench 2.0 subset, while DeepSeek V4-Flash was slightly lower.

| Arm | Successes | Trials | Success rate | 95% Wilson CI |
|---|---:|---:|---:|---:|
| Anthropic Sonnet | 39 | 60 | 65.0% | 52.4%-75.8% |
| DeepSeek V4-Pro | 42 | 60 | 70.0% | 57.5%-80.1% |
| DeepSeek V4-Flash | 37 | 60 | 61.7% | 49.0%-72.9% |

Because the confidence intervals overlap, the correct conclusion is that DeepSeek Pro did not meaningfully diminish quality relative to Anthropic on this subset, not that it is conclusively better.

## 2. Did the speed hypothesis hold?

No for DeepSeek V4-Pro; roughly neutral for DeepSeek V4-Flash. Pro's median wall-clock time was 617.5s versus 255.7s for Anthropic and 262.7s for Flash. The slowdown was mostly in agent execution time: Pro's median agent-execution time was 387.5s versus 159.3s for Anthropic.

The new aggregate also shows that Pro used more agent turns and tool calls. Median agent turns were 17.0 for Anthropic, 30.5 for Pro, and 38.0 for Flash. Median tool calls were 10.5, 13.5, and 18.0, respectively.

## 3. What is the cost-per-resolved-task picture?

| Arm | Total cost | Successful trials | Cost / successful trial | Tasks solved at least once | Cost / resolved task |
|---|---:|---:|---:|---:|---:|
| Anthropic Sonnet | $37.30 | 39 | $0.956 | 15 | $2.486 |
| DeepSeek V4-Pro | $2.01 | 42 | $0.048 | 17 | $0.118 |
| DeepSeek V4-Flash | $1.10 | 37 | $0.030 | 16 | $0.069 |

DeepSeek Pro was about 20x cheaper per successful trial than Anthropic. Flash was about 32x cheaper per successful trial.

## 4. Where did the model swap break?

The swap did not break globally. DeepSeek Pro worked through Claude Code and produced the highest raw success rate. The breaks were task-specific:

- `schemelike-metacircular-eval`: Pro solved 3/3 while Anthropic and Flash solved 0/3. This was the strongest Pro-positive case and suggests Pro handled sustained symbolic/interpreter implementation better.
- `cancel-async-tasks`: Flash solved 3/3 while Anthropic solved 0/3 and Pro solved 1/3. This was the strongest Flash-positive case and maps well to compact async/concurrency repair.
- `build-cython-ext`: Anthropic solved 3/3 while Pro solved 2/3 and Flash solved 1/3. Anthropic appeared more exhaustive on scientific Python/Cython compatibility.
- `query-optimize`: both DeepSeek arms solved 2/3 while Anthropic solved 1/3. This is a hedge-fund-relevant database optimization divergence.
- `openssl-selfsigned-cert` and `password-recovery`: Flash underperformed, suggesting weaker environment discipline and exact-output persistence on some security/recovery tasks.

The new failure-mode labels show most failures were normal verifier failures or timeouts, not refusal or broad Anthropic-format/tool-call incompatibility.

| Arm               |   Success |   Produced wrong output / failed verifier |   Timed out |   Looped |   Refused-to-try / setup failure |   Ran-out-of-budget / agent process error |
|:------------------|----------:|------------------------------------------:|------------:|---------:|---------------------------------:|------------------------------------------:|
| Anthropic Sonnet  |        39 |                                        14 |           6 |        0 |                                0 |                                         1 |
| DeepSeek V4-Pro   |        42 |                                        13 |           4 |        1 |                                0 |                                         0 |
| DeepSeek V4-Flash |        37 |                                        14 |           6 |        2 |                                0 |                                         1 |

## 5. Production recommendation

Use DeepSeek V4-Pro when cost matters and latency is acceptable. Use DeepSeek V4-Flash for cheap first-pass attempts and broad exploration. Keep Anthropic Sonnet in the routing mix for latency-sensitive workflows and task classes where it remains more reliable. The best production strategy suggested by this benchmark is cost-aware routing rather than one universal backend: Flash first, Pro escalation for harder reasoning, and Anthropic for latency-sensitive or historically Anthropic-favored tasks.
