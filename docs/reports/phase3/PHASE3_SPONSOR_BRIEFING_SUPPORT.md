# Phase 3 Sponsor Briefing Support

This is the working support document for the Phase 3 router/canary briefing. It is markdown-first and slide-ready, but it is not the slide deck.

## Slide 1 candidate: executive summary / so what?

**Headline:** Phase 3 has moved from a three-arm Claude Code benchmark into a multi-provider router benchmark harness with canary-verified routing, contamination controls, and cost forecasting.

- **Impact:** 13 current router arms are canary-green and ready for funded smoke testing.
- **Breadth:** Passing arms now span 8 provider families: anthropic, dashscope-qwen, deepseek, google-gemini, moonshot-kimi, openai, xai, zai-glm.
- **Risk reduction:** Early failures were mostly provider access, model-route, quota, or tool-mode issues, not benchmark-quality failures.
- **Contamination mitigation:** Router arms deny `WebSearch`, `WebFetch`, `EnterPlanMode`, `ExitPlanMode`, and `AskUserQuestion` where applicable.
- **Cost discipline:** The next stage should be a funded smoke layer before approving full sweeps. Canary-scaled estimate for 5-task smoke is **$44.72**, with a conservative 2x reserve of **$89.44**.
- **Full-sweep planning:** Canary-scaled estimate for 20 tasks × 3 attempts is **$536.64**, with a 1.5x reserve of **$804.97**.
- **Expanded evaluation:** Canary-scaled estimate for 25 tasks × 3 attempts is **$670.80**, with a 1.5x reserve of **$1,006.21**.

## Fast navigation

### Evidence and ledgers

- Canary evidence report: [`docs/reports/phase3/PHASE3_CANARY_EVIDENCE.md`](../../../docs/reports/phase3/PHASE3_CANARY_EVIDENCE.md)
- Canary ledger CSV: [`results/phase3/supplemental/canary_ledger.csv`](../../../results/phase3/supplemental/canary_ledger.csv)
- Canary ledger JSON: [`results/phase3/supplemental/canary_ledger.json`](../../../results/phase3/supplemental/canary_ledger.json)
- Cost forecast CSV: [`results/phase3/supplemental/phase3_cost_forecast_canary_scaled.csv`](../../../results/phase3/supplemental/phase3_cost_forecast_canary_scaled.csv)
- Cost forecast summary JSON: [`results/phase3/supplemental/phase3_cost_forecast_summary.json`](../../../results/phase3/supplemental/phase3_cost_forecast_summary.json)

### Figures

- Canary cost by arm: [`figures/phase3/canary_cost_by_arm.png`](../../../figures/phase3/canary_cost_by_arm.png)
- Canary status counts: [`figures/phase3/canary_status_counts.png`](../../../figures/phase3/canary_status_counts.png)

### Core configuration and support docs

- LiteLLM router example config: [`configs/router/litellm.config.yaml.example`](../../../configs/router/litellm.config.yaml.example)
- Router arm configs: [`configs/arms/`](../../../configs/arms/)
- Canary evidence extraction script: [`scripts/extract_phase3_canary_evidence.py`](../../../scripts/extract_phase3_canary_evidence.py)
- Findings log: [`docs/PHASE3_ROUTER_FINDINGS.md`](../../../docs/PHASE3_ROUTER_FINDINGS.md)
- Contamination notes: [`BENCHMARK_CONTAMINATION.md`](../../../BENCHMARK_CONTAMINATION.md)
- Runbook: [`RUNBOOK.md`](../../../RUNBOOK.md)
- Artifact policy: [`ARTIFACT_POLICY.md`](../../../ARTIFACT_POLICY.md)

## Architecture summary

~~~mermaid
flowchart LR
    Sponsor[Sponsor questions] --> Plan[Phase 3 model-arm plan]
    Plan --> ArmConfigs[configs/arms/*.yaml]
    ArmConfigs --> Runner[scripts/run_arm.sh]
    Runner --> Harbor[Harbor + Terminal-Bench 2.0]
    Harbor --> ClaudeCode[Claude Code agent harness]
    ClaudeCode --> LiteLLM[LiteLLM router]
    LiteLLM --> Providers[Anthropic / DeepSeek / Gemini / OpenAI / xAI / Moonshot / DashScope / Z.AI]
    Harbor --> Results[results/phase3/canary/...]
    Results --> Audit[scripts/audit_tool_usage.py]
    Results --> Evidence[scripts/extract_phase3_canary_evidence.py]
    Evidence --> Ledger[canary_ledger.csv/json]
    Evidence --> Report[PHASE3_CANARY_EVIDENCE.md]
    Evidence --> Figures[figures/phase3/*.png]
~~~

## What was done in Phase 3 so far

1. Added a router-mediated benchmark layer using LiteLLM while keeping Claude Code as the fixed agent harness.
2. Added canary-first execution so provider/model/config issues are detected before paid smoke or full sweeps.
3. Added stronger contamination controls by denying web fetch/search and plan/ask-user tools where applicable.
4. Resolved provider-specific routing and model-access issues:
   - Gemini route corrections and no-plan tool mitigation.
   - OpenAI router route validation.
   - Qwen Singapore endpoint and model-access normalization.
   - xAI Grok model selection and funding/access recovery.
   - Moonshot Kimi model update and temperature/max-token behavior discovery.
   - Z.AI GLM model update and funding/access recovery.
5. Added evidence extraction and cost forecast artifacts for sponsor review.

## Current canary-green arms

| Arm | Provider | Backend model | Canary cost | Runtime | Evidence |
|---|---|---:|---:|---:|---|
| `router-anthropic-haiku-sanitized` | `anthropic` | `claude-haiku-4-5-20251001` | $0.314650 | 486.133s | [result](../../../results/phase3/canary/arm-router-anthropic-haiku-sanitized/2026-06-01__13-17-13) |
| `router-anthropic-opus` | `anthropic` | `claude-opus-4-7` | $0.315033 | 289.333s | [result](../../../results/phase3/canary/arm-router-anthropic-opus/2026-06-01__09-36-08) |
| `router-anthropic-sonnet` | `anthropic` | `claude-sonnet-4-6` | $0.292982 | 82.333s | [result](../../../results/phase3/canary/arm-router-anthropic-sonnet/2026-05-30__18-57-05) |
| `router-deepseek-flash` | `deepseek` | `deepseek-v4-flash` | $0.114800 | 252.194s | [result](../../../results/phase3/canary/arm-router-deepseek-flash/2026-05-31__18-23-35) |
| `router-deepseek-pro` | `deepseek` | `deepseek-v4-pro` | $0.092179 | 425.081s | [result](../../../results/phase3/canary/arm-router-deepseek-pro/2026-05-31__21-44-33) |
| `router-gemini-3.1-pro` | `google-gemini` | `gemini-3.1-pro-preview` | $0.291061 | 129.269s | [result](../../../results/phase3/canary/arm-router-gemini-3.1-pro/2026-06-02__22-17-25) |
| `router-gemini-flash` | `google-gemini` | `gemini-3.5-flash` | $2.451235 | 150.889s | [result](../../../results/phase3/canary/arm-router-gemini-flash/2026-06-02__20-59-54) |
| `router-glm-5.1` | `zai-glm` | `glm-5.1` | $0.107285 | 135.771s | [result](../../../results/phase3/canary/arm-router-glm-5.1/2026-06-04__12-40-42) |
| `router-gpt-5.4` | `openai` | `gpt-5.4` | $0.799355 | 115.222s | [result](../../../results/phase3/canary/arm-router-gpt-5.4/2026-06-03__00-58-05) |
| `router-gpt-5.5` | `openai` | `gpt-5.5` | $2.546790 | 165.067s | [result](../../../results/phase3/canary/arm-router-gpt-5.5/2026-06-03__00-46-21) |
| `router-grok-build-0.1` | `xai` | `grok-build-0.1` | $0.710016 | 102.956s | [result](../../../results/phase3/canary/arm-router-grok-build-0.1/2026-06-04__03-06-37) |
| `router-kimi-k2.6` | `moonshot-kimi` | `kimi-k2.6` | $0.465169 | 197.975s | [result](../../../results/phase3/canary/arm-router-kimi-k2.6/2026-06-04__03-08-21) |
| `router-qwen-3.7-plus` | `dashscope-qwen` | `qwen3.7-plus` | $0.443505 | 149.79s | [result](../../../results/phase3/canary/arm-router-qwen-3.7-plus/2026-06-04__02-32-42) |


## Historical failed/superseded canaries

These are useful engineering evidence, but they should not be presented as current blockers.

| Arm | Classification | Superseded by |
|---|---|---|
| `router-glm-5` | `FAIL-AUTH/QUOTA` | superseded by router-glm-5.1 after Z.AI funding/model route normalization |
| `router-grok-3` | `FAIL-AUTH/QUOTA` | superseded by router-grok-build-0.1 after xAI funding/model route normalization |
| `router-kimi-k2.5` | `FAIL-AUTH/QUOTA` | superseded by router-kimi-k2.6 after Moonshot funding/model route normalization |
| `router-qwen-3.5` | `FAIL-AUTH/QUOTA` | superseded by router-qwen-3.7-plus after DashScope Singapore endpoint and model-access fixes |


## Funding recommendation

The canary results are strong enough to justify smoke testing, but not strong enough to skip directly to the full sweep.

Recommended staged funding:

1. **Fund 5-task smoke first:** estimated **$44.72**, reserve **$89.44**.
2. Use smoke results to replace canary-scaled cost estimates with real multi-task, provider-specific costs.
3. Approve the 20-task × 3-attempt sweep only after smoke confirms cost behavior.
4. Consider a 25-task expanded sweep after the 20-task sweep if the sponsor wants added coverage or contamination-risk mitigation.

## Cost caveats

The current estimate is intentionally preliminary:

- It scales from one canary task, not from a representative multi-task smoke set.
- Canary cost behavior varies heavily by provider.
- Some providers show large token/cache differences.
- Gemini Flash and GPT-5.5 were high-cost outliers in canary.
- Smoke results should become the new source of truth before full-sweep approval.

## Slide deck outline, not yet created

1. Executive summary / so what?
2. Phase 3 architecture and control flow.
3. Model-arm matrix and provider coverage.
4. Canary classification ledger.
5. Contamination mitigation.
6. Provider-specific lessons learned.
7. Cost forecast and funding gates.
8. Recommended next actions.
9. Appendix: evidence links, configs, result paths, and task references.

## Open items before slide creation

- Confirm exact smoke task list.
- Confirm whether historical failed/superseded canaries belong in the main deck or appendix only.
- Decide whether expanded sweep should use 25 Terminal-Bench 2.0 tasks or add newer/different tasks for contamination-risk mitigation.
- Replace canary-scaled estimates with smoke-scaled estimates once smoke runs are funded and complete.
