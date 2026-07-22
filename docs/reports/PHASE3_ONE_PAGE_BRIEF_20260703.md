# Phase 3 One-Page Brief — Claude Code Backend Benchmark

## Bottom line

Phase 3 now has **13 clean valid full-sweep model arms** across Anthropic, DeepSeek, OpenAI, Gemini, Grok/xAI, Kimi/Moonshot, Qwen/Alibaba, and GLM/Z.AI. Each valid arm ran **20 Terminal-Bench 2.0 tasks × 3 attempts = 60 trials** under the Claude Code harness.

`router-gpt-5.5` is the current quality leader. The main business finding, however, is that several lower-cost routed models remain highly competitive. `router-deepseek-flash` is the clearest quality/cost standout, and `router-glm-5.2` is also promising.

Haiku is **pending rerun**, not scored. Its full run was quarantined because the runtime API path failed with zero-token `ConnectionRefused` errors, which is infrastructure contamination rather than model behavior.

## Valid-only results

| Rank | Arm | Successes | Raw Pass | Qualified Pass | Cost |
|---:|---|---:|---:|---:|---:|
| 1 | `router-gpt-5.5` | 44 / 60 | 73.3% | 75.9% | $168.71 |
| 2 | `router-deepseek-flash` | 40 / 60 | 66.7% | 66.7% | $56.35 |
| 3 | `router-anthropic-opus` | 39 / 60 | 65.0% | 65.0% | $40.33 |
| 4 | `router-gpt-5.4` | 39 / 60 | 65.0% | 65.0% | $173.09 |
| 5 | `router-gemini-3.1-pro` | 38 / 60 | 63.3% | 63.3% | $38.10 |
| 6 | `router-glm-5.2` | 38 / 60 | 63.3% | 63.3% | $20.55 |
| 7 | `router-deepseek-pro` | 37 / 60 | 61.7% | 61.7% | $50.20 |
| 8 | `router-grok-build-0.1` | 36 / 60 | 60.0% | 60.0% | $38.15 |
| 9 | `router-glm-5.1` | 36 / 60 | 60.0% | 60.0% | $18.65 |
| 10 | `router-qwen-3.7-plus` | 33 / 60 | 55.0% | 55.0% | $20.43 |
| 11 | `router-kimi-k2.6` | 30 / 60 | 50.0% | 50.0% | $25.99 |
| 12 | `router-anthropic-sonnet` | 28 / 60 | 46.7% | 46.7% | $37.39 |
| 13 | `router-gemini-flash` | 13 / 60 | 21.7% | 22.4% | $23.67 |

## Key interpretation

The result is not simply “highest-cost frontier model wins.” GPT-5.5 leads quality, but DeepSeek Flash, GLM 5.2, Gemini 3.1 Pro, Anthropic Opus, GPT-5.4, and DeepSeek Pro form a competitive cluster. Cost, exception rate, and failure mode matter alongside raw pass rate.

The dashboard and final report should default to **valid-only full sweeps**, show excluded runs separately, and include raw pass rate, qualified pass rate, exception count, missing-cost count, and recorded cost.

## Excluded / quarantined runs

- Anthropic Opus old run: provider workspace API usage limit.
- Gemini 3.1 Pro old run: monthly spending cap / 429 `RESOURCE_EXHAUSTED`.
- Anthropic Haiku sanitized full run: runtime API-path failure with zero-token `ConnectionRefused` errors.

## Next step

Before rerunning Haiku, add a runtime watchdog for LiteLLM and sanitizer health so a dead API path fails fast instead of producing a long invalid run.
