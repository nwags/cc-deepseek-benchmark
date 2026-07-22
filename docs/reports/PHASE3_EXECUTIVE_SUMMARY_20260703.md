# Phase 3 Executive Summary — Claude Code Backend Benchmark

## Headline findings

Phase 3 expanded the Claude Code backend benchmark from the original Anthropic/DeepSeek comparison into a broader routed-model evaluation across Anthropic, DeepSeek, OpenAI, Gemini, Grok/xAI, Kimi/Moonshot, Qwen/Alibaba, and GLM/Z.AI. The clean valid-only Phase 3 result set currently contains 13 completed full-sweep arms: 20 Terminal-Bench 2.0 tasks × 3 attempts = 60 trials per arm.

The strongest observed quality result so far is `router-gpt-5.5`, with 44/60 raw successes and 44/58 qualified successes after excluding two suspect no-op trials. Strong second-tier results cluster tightly around 63–67% raw pass rate: DeepSeek Flash, Anthropic Opus, GPT-5.4, Gemini 3.1 Pro, GLM 5.2, and DeepSeek Pro.

The most important business finding is that the best non-frontier-cost options remain highly competitive. DeepSeek Flash reached 40/60, ahead of every valid arm except GPT-5.5, while costing far less than the OpenAI GPT-5.4/5.5 arms. GLM 5.2 and Gemini 3.1 Pro were also competitive with the higher-cost frontier arms.

Haiku is not included in the valid table yet. The Haiku sanitized full run was quarantined because the Claude Code runtime path lost API connectivity during the long full sweep, yielding zero-token `ConnectionRefused` failures. That is infrastructure contamination, not a model-quality result. Haiku should be rerun after adding a runtime-service watchdog.

## Valid-only results table

| Arm | Successes / Trials | Raw Pass Rate | Qualified Pass Rate | Recorded Cost | Notes |
|---|---:|---:|---:|---:|---|
| `router-gpt-5.5` | 44 / 60 | 73.3% | 75.9% | $168.71 | Best quality; two suspect no-op trials excluded from qualified rate. |
| `router-deepseek-flash` | 40 / 60 | 66.7% | 66.7% | $56.35 | Strong quality/cost result; best non-OpenAI valid arm by raw pass rate. |
| `router-anthropic-opus` | 39 / 60 | 65.0% | 65.0% | $40.33 | Strong result after rerun; earlier provider-limit run excluded. |
| `router-gpt-5.4` | 39 / 60 | 65.0% | 65.0% | $173.09 | Strong quality, but highest recorded cost tier. |
| `router-gemini-3.1-pro` | 38 / 60 | 63.3% | 63.3% | $38.10 | Competitive after rerun; earlier monthly-cap run excluded. |
| `router-glm-5.2` | 38 / 60 | 63.3% | 63.3% | $20.55 | Strong value result; close to Gemini 3.1 Pro and GPT-5.4. |
| `router-deepseek-pro` | 37 / 60 | 61.7% | 61.7% | $50.20 | Competitive, but no longer clearly ahead of Flash in Phase 3. |
| `router-grok-build-0.1` | 36 / 60 | 60.0% | 60.0% | $38.15 | Mid-pack quality. |
| `router-glm-5.1` | 36 / 60 | 60.0% | 60.0% | $18.65 | Strong low-cost mid-pack result. |
| `router-qwen-3.7-plus` | 33 / 60 | 55.0% | 55.0% | $20.43 | Below the 60% cluster but usable. |
| `router-kimi-k2.6` | 30 / 60 | 50.0% | 50.0% | $25.99 | Lower quality in this harness/task set. |
| `router-anthropic-sonnet` | 28 / 60 | 46.7% | 46.7% | $37.39 | Phase 3 result underperformed Phase 1 Sonnet baseline; needs artifact-level interpretation. |
| `router-gemini-flash` | 13 / 60 | 21.7% | 22.4% | $23.67 | Many exceptions; not competitive in this configuration. |

## Interpretation

The result pattern is no longer a simple “frontier model wins” story. GPT-5.5 is the quality leader, but several lower-cost routed providers are close enough to matter operationally. DeepSeek Flash is the clearest quality/cost standout so far. GLM 5.2 also looks promising because it landed in the same quality band as Gemini 3.1 Pro and GPT-5.4 at substantially lower recorded cost.

The artifact review shows that raw pass rate alone is not enough. Some arms have many exception failures, some have normal verifier failures, and a small number of suspect no-op trials required qualified-rate accounting. The dashboard and report should therefore emphasize valid-only results, exception counts, missing-cost counts, and qualified pass rate alongside raw pass rate.

## Excluded or quarantined runs

Three full-run exclusions are currently loaded:

1. Anthropic Opus old run: excluded due Anthropic workspace API usage limit.
2. Gemini 3.1 Pro old run: excluded due Gemini monthly spending cap / 429 `RESOURCE_EXHAUSTED`.
3. Anthropic Haiku sanitized full run: excluded due runtime API-path failure; Claude Code produced zero-token `ConnectionRefused` results through the sanitizer/LiteLLM path.

## Recommended next actions

Before rerunning Haiku, add a runtime watchdog that continuously checks LiteLLM and sanitizer health during long runs and fails fast if the API path dies. After Haiku rerun succeeds and is ingested, update this summary and make Phase 3 the new baseline for subsequent phases.
