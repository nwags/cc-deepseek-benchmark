# Phase 3 Router Findings

This document records provider/model routing settings, observed backend model versions,
Claude Code/LiteLLM compatibility issues, and run-level findings for Phase 3 router arms.

## Methodology Notes

- Phase 3 outputs remain under `results/phase3/...`.
- Phase 1 and Phase 2 results remain intact.
- WebSearch/WebFetch are disallowed for contamination mitigation.
- For non-interactive Terminal-Bench runs, interactive planning/question tools may need to be disallowed:
  `EnterPlanMode,ExitPlanMode,AskUserQuestion`.
- Provider model slugs, observed backend model names, and router behavior must be verified before smoke/scored runs.

## router-gemini-flash

### Intended route

- Arm: `router-gemini-flash`
- LiteLLM model name: `router-gemini-flash`
- Backend model configured: `gemini/gemini-3.5-flash`
- Claude Code env model: `router-gemini-flash`
- Provider key env var: `GEMINI_API_KEY`

### Probe result

- `/v1/chat/completions` probe succeeded.
- Response text: `gemini flash route ok`
- Observed route: `router-gemini-flash`
- Observed backend in trajectories: `gemini-3.5-flash`

### Canary 1

- Result path: `results/phase3/canary/arm-router-gemini-flash/2026-06-02__17-59-33`
- Result: completed, no Harbor exception, reward 0.0
- Contamination audit: clean
- Cost reported: `$0.9195835`
- Failure mode: behavioral/tool-loop failure.
- Finding: model entered `EnterPlanMode`, then attempted `ExitPlanMode`; run ended before implementing files.
- Action: disallow `EnterPlanMode,ExitPlanMode,AskUserQuestion` for non-interactive Terminal-Bench runs.

### Canary 2, no-plan tools

- Result path: `results/phase3/canary/arm-router-gemini-flash/2026-06-02__20-30-15`
- Result: `NonZeroAgentExitCodeError`, reward 0.0
- Contamination audit: clean
- Cost reported: `$0.3962`
- Failure mode: Gemini free-tier quota/rate-limit.
- Error: `429 RESOURCE_EXHAUSTED`
- Quota metric: `generativelanguage.googleapis.com/generate_content_free_tier_requests`
- Quota: `20` requests/day/project/model for `gemini-3.5-flash` as reported by API error.
- Action: do not run smoke until billing/quota is upgraded or reset and a fresh no-plan canary is run.

### Current recommendation

Do not run smoke yet. After enabling billing or waiting for quota reset, rerun only the no-plan canary first.
If that canary reaches task completion without quota/setup failure, then run the 5-task smoke.

### Canary 3, no-plan tools, paid/quota resolved

- Result path: `results/phase3/canary/arm-router-gemini-flash/2026-06-02__20-59-54`
- Result: pass
- Reward: `1.0`
- Harbor exceptions: `0`
- Runtime: `2m 30s`
- Contamination audit: clean
- Input tokens: `433132`
- Output tokens: `11423`
- Cost reported: `$2.451235`
- Observed route/model names:
  - Router model: `router-gemini-flash`
  - Backend model observed in trajectory: `gemini-3.5-flash`
- Effective configuration:
  - `disallowed_tools=WebSearch,WebFetch,EnterPlanMode,ExitPlanMode,AskUserQuestion`
- Finding:
  - Disallowing `EnterPlanMode`, `ExitPlanMode`, and `AskUserQuestion` resolved the earlier behavioral failure.
  - Gemini Flash can complete the canary successfully through LiteLLM/Claude Code.
  - Successful run was substantially more expensive than the failed canaries because the model used many task-tracking/tool-loop turns and produced a long final summary.
- Current recommendation:
  - Mark `router-gemini-flash` canary as passed.
  - Do not run smoke until sponsor/funding update.
  - Consider reducing unnecessary task-tracking tools in future router arms if canary costs remain high.

## router-gemini-3.1-pro

### Canary 1, invalid backend slug

- Result path: `results/phase3/canary/arm-router-gemini-3.1-pro/2026-06-02__21-10-28`
- Result: `NonZeroAgentExitCodeError`
- Reward: `0.0`
- Cost: `$0`
- Tokens: `0 input / 0 output`
- Contamination audit: clean
- Failure mode: setup/model-route failure, not model-quality failure.
- Root cause: LiteLLM route used `gemini/gemini-3.1-pro`, but Google API returned 404: `models/gemini-3.1-pro is not found for API version v1alpha, or is not supported for generateContent`.
- Action: changed backend route to `gemini/gemini-3.1-pro-preview`, restarted LiteLLM, and reran canary.

### Canary 2, corrected preview backend

- Result path: `results/phase3/canary/arm-router-gemini-3.1-pro/2026-06-02__22-17-25`
- Result: pass
- Reward: `1.0`
- Harbor exceptions: `0`
- Runtime: `2m 9s`
- Contamination audit: clean
- Input tokens: `130505`
- Cache tokens: `89103`
- Output tokens: `1580`
- Cost reported: `$0.2910615`
- Effective configuration:
  - Claude Code model: `router-gemini-3.1-pro`
  - Backend route: `gemini/gemini-3.1-pro-preview`
  - Observed backend in trajectory: `gemini-3.1-pro-preview`
  - `disallowed_tools=WebSearch,WebFetch,EnterPlanMode,ExitPlanMode,AskUserQuestion`
- Finding:
  - The standard `gemini-3.1-pro-preview` endpoint works through LiteLLM/Claude Code for the Phase 3 canary.
  - Disallowing planning/question tools remains appropriate for non-interactive Terminal-Bench runs.
  - Canary cost was much lower than `router-gemini-flash` canary 3 because this run used fewer tool-loop/task-tracking turns and produced a shorter final response.
- Current recommendation:
  - Mark `router-gemini-3.1-pro` canary as passed.
  - Do not run smoke until sponsor/funding update.

## OpenAI GPT-5.5 canary

Run:
- Date: 2026-06-03
- Arm: `router-gpt-5.5`
- Mode: canary
- Task: `modernize-scientific-stack`
- Result path: `results/phase3/canary/arm-router-gpt-5.5/2026-06-03__00-46-21/result.json`

Outcome:
- Trials: 1
- Exceptions: 0
- Mean: 1.000
- Reward: 1.0
- Runtime: 2m45s
- Input tokens: 493,763
- Output tokens: 3,119
- Cost: $2.54679

Validation:
- Direct OpenAI API access to `gpt-5.5` was previously verified.
- Earlier failed canary was due to LiteLLM seeing `OPENAI_API_KEY=None`, not model access.
- After persisting `.secrets/litellm.env` and restarting the LiteLLM proxy, the Harbor canary succeeded.
- `audit_tool_usage.py --strict --fail-on-available` passed:
  - Actual WebSearch/WebFetch tool-use events: 0
  - Init records with WebSearch/WebFetch available: 0

Trajectory observations:
- The run succeeded and created `/app/analyze_climate_modern.py` plus `/app/requirements.txt`.
- The agent verified the script output:
  - `Station 101 mean temperature: -15.5°C`
  - `Station 102 mean temperature: 30.3°C`
- The trajectory showed repeated `Read` calls with `pages: ""`, causing invalid-pages tool errors before recovery. This did not prevent success, but it is worth tracking as a possible Claude Code/router compatibility artifact and token-cost contributor.


## OpenAI GPT-5.4 canary

Run:
- Date: 2026-06-03
- Arm: `router-gpt-5.4`
- Mode: canary
- Task: `modernize-scientific-stack`
- Result path: `results/phase3/canary/arm-router-gpt-5.4/2026-06-03__00-58-05/result.json`

Outcome:
- Status: pass
- Trials: 1
- Exceptions: 0
- Mean: 1.000
- Reward stats: `{"1.0": ["modernize-scientific-stack__WACxyXT"]}`
- Exception stats: `{}`
- Input tokens: 146861
- Output tokens: 2602
- Cost: $0.799355

Validation:
- `audit_tool_usage.py --strict --fail-on-available` was run after the canary.
- Effective disallowed tools include `WebSearch,WebFetch,EnterPlanMode,ExitPlanMode,AskUserQuestion`.

Observed model names:
- `gpt-5.4`

Trajectory observations:
- Repeated empty `pages` parameter errors observed: `True`
- `NonZeroAgentExitCodeError` observed in scanned files: `False`


## Canary Classification Ledger

Classification labels:

- `PASS`: routing/config good enough for smoke
- `FAIL-BENCH`: model ran but failed task
- `FAIL-CONFIG`: proxy/model/schema/tool issue
- `FAIL-AUTH/QUOTA`: provider access, credits, quota, or key issue
- `FAIL-CONTAMINATION`: forbidden web/tool exposure

## Remaining-provider canaries, 2026-06-03

### router-grok-3

- Result path: `results/phase3/canary/arm-router-grok-3/2026-06-03__02-28-35`
- Classification: `FAIL-AUTH/QUOTA`
- Harbor result: `NonZeroAgentExitCodeError`, reward `0.0`
- Cost reported: `$0`
- Contamination audit: clean
- Effective disallowed tools: `WebSearch,WebFetch,EnterPlanMode,ExitPlanMode,AskUserQuestion`
- Evidence:
  - Provider/LiteLLM returned `403`.
  - Error text indicated the xAI team/account lacked credits or license access.
- Interpretation:
  - The router reached the xAI/Grok backend, but the provider account/team is not funded or licensed for the requested model.
  - Do not rerun until xAI billing/credits/license are resolved.

### router-kimi-k2.5

- Result path: `results/phase3/canary/arm-router-kimi-k2.5/2026-06-03__02-29-50`
- Classification: `FAIL-AUTH/QUOTA`
- Harbor result: `NonZeroAgentExitCodeError`, reward `0.0`
- Cost reported: `$0`
- Contamination audit: clean
- Effective disallowed tools: `WebSearch,WebFetch,EnterPlanMode,ExitPlanMode,AskUserQuestion`
- Direct provider probe:
  - `.secrets/moonshot.env` exists and exports `MOONSHOT_API_KEY`.
  - `https://api.moonshot.ai/v1/chat/completions` returned `exceeded_current_quota_error`.
  - Error text indicated the Moonshot account is suspended due to insufficient balance.
  - `https://api.moonshot.cn/v1/chat/completions` returned invalid authentication, consistent with endpoint/account-region mismatch.
- Interpretation:
  - This is not a missing local secret file issue.
  - The Moonshot/Kimi key reaches the `.ai` endpoint, but the account lacks balance.
  - Do not rerun until Moonshot billing is restored and a direct cheap probe succeeds.

### router-qwen-3.5

- Result path: `results/phase3/canary/arm-router-qwen-3.5/2026-06-03__02-34-10`
- Classification: `FAIL-CONFIG`
- Secondary blocker: `FAIL-AUTH/QUOTA` until DashScope token plan/model entitlement is active
- Harbor result: `NonZeroAgentExitCodeError`, reward `0.0`
- Cost reported: `$0`
- Contamination audit: clean
- Effective disallowed tools: `WebSearch,WebFetch,EnterPlanMode,ExitPlanMode,AskUserQuestion`
- Evidence:
  - `.secrets/dashscope.env` exists and exports `DASHSCOPE_API_KEY`.
  - The account is configured for the Singapore DashScope/Model Studio endpoint.
  - Direct China endpoint probe returned `invalid_api_key`, which is expected when using a Singapore-region key against the China/Beijing endpoint.
  - Direct Singapore endpoint probe with `qwen-3.5` returned `model_not_found`, suggesting the configured backend model identifier is not valid/available as written.
  - Direct Singapore endpoint probe with `qwen-plus` reached the service but returned `Model.AccessDenied`, consistent with missing token plan or missing model entitlement.
  - Router probe with the real LiteLLM token still returned the China-style DashScope `Incorrect API key` message, suggesting the LiteLLM Qwen route may still be pointed at the wrong regional endpoint or using the wrong provider/model string.
- Interpretation:
  - Do not treat the DashScope key itself as proven bad.
  - Fix Qwen routing to the Singapore endpoint: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`.
  - Replace `qwen-3.5` with an actually available DashScope model name such as `qwen-plus`, `qwen-flash`, `qwen3.5-plus`, or `qwen3.5-flash`, depending on subscribed access.
  - After subscribing/enabling a token plan, run a cheap direct Singapore provider probe first, then rerun the LiteLLM router probe, then rerun Harbor canary.

### router-glm-5

- Result path: `results/phase3/canary/arm-router-glm-5/2026-06-03__02-38-35`
- Classification: `FAIL-AUTH/QUOTA`
- Harbor result: `NonZeroAgentExitCodeError`, reward `0.0`
- Cost reported: `$0`
- Contamination audit: clean
- Effective disallowed tools: `WebSearch,WebFetch,EnterPlanMode,ExitPlanMode,AskUserQuestion`
- Evidence:
  - Provider/LiteLLM returned repeated `429 rate_limit` retries.
  - Final error text indicated `ZaiException - Insufficient balance or no resource package. Please recharge.`
- Interpretation:
  - The router reached the Z.ai/GLM backend, but the account lacks balance or an enabled resource package.
  - Do not rerun until Z.ai billing/resource package access is resolved.

## Follow-up rule

Before rerunning Harbor canaries for any failed provider, first run a cheap direct provider probe. Only rerun Harbor after the direct provider probe succeeds.


## Qwen3.7-Plus canary, 2026-06-04

Run:
- Arm: `router-qwen-3.7-plus`
- Backend route: `dashscope/qwen3.7-plus`
- Provider endpoint: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
- Mode: `canary`
- Task: `modernize-scientific-stack`
- Result path: `results/phase3/canary/arm-router-qwen-3.7-plus/2026-06-04__02-32-42/result.json`

Outcome:
- Classification: `PASS`
- Trials: `1`
- Exceptions: `0`
- Mean: `1.000`
- Reward: `1.0`
- Runtime: `2m29s`
- Input tokens: `72,731`
- Cache tokens: `0`
- Output tokens: `3,194`
- Cost reported: `$0.443505`

Validation:
- Direct DashScope Singapore endpoint probes succeeded for `qwen3.7-plus`, `qwen3.6-plus`, and `qwen3.5-plus`; `qwen-plus` remained access-denied.
- LiteLLM router probe succeeded after changing the Qwen route to `router-qwen-3.7-plus` with backend `dashscope/qwen3.7-plus` and Singapore `api_base`.
- Harbor canary succeeded through Claude Code + LiteLLM.
- Contamination audit passed:
  - Actual WebSearch/WebFetch tool-use events: `0`
  - Init records with WebSearch/WebFetch available: `0`

Finding:
- Qwen is now routed/configured correctly for Phase 3 using the Singapore DashScope endpoint and `qwen3.7-plus`.
- The prior `router-qwen-3.5` failures should remain classified as `FAIL-AUTH/QUOTA` or `FAIL-CONFIG` depending on the specific run, because the selected model slug/access did not work.
- The active Qwen candidate for future smoke/full sweep should be `router-qwen-3.7-plus`, not `router-qwen-3.5`.

Recommendation:
- Mark `router-qwen-3.7-plus` as canary-passed.
- Do not rerun the older `router-qwen-3.5` arm unless there is a specific reason to compare older Qwen variants.

## Direct provider probes after funding/model-access fixes, 2026-06-04

After adding provider funding and/or model access, direct provider probes were rerun for Kimi and GLM with a larger output budget.

### Moonshot / Kimi

- Tested model: `kimi-k2.6`
- Endpoint: `https://api.moonshot.ai/v1/chat/completions`
- Probe setting: `temperature=1`, `max_tokens=512`
- Result: direct provider probe passed
- Evidence:
  - Returned model: `kimi-k2.6`
  - Finish reason: `stop`
  - Visible text: `kimi k2.6 direct ok`
  - Reasoning content was present, confirming the earlier empty visible output was caused by too-small `max_tokens`, not auth failure.
- Current classification for direct provider access: `PASS`

### Z.AI / GLM

- Tested model: `glm-5.1`
- Endpoint: `https://api.z.ai/api/paas/v4/chat/completions`
- Probe setting: `temperature=0`, `max_tokens=512`
- Result: direct provider probe passed
- Evidence:
  - Returned model: `glm-5.1`
  - Finish reason: `stop`
  - Visible text: `glm 5.1 direct ok`
  - Reasoning content was present; earlier `finish_reason=length` under `max_tokens=20` was a probe-budget artifact.
- Current classification for direct provider access: `PASS`

Interpretation:
- Kimi and GLM are no longer blocked on authentication or quota at the direct-provider layer.
- Next step is to patch LiteLLM routes and arm files to use versioned active arms:
  - `router-kimi-k2.6`
  - `router-glm-5.1`
  - `router-grok-build-0.1`
- Run cheap LiteLLM router probes before Harbor canaries.

## Remaining-provider canary recovery, 2026-06-04

After funding/model-access fixes and route normalization, all remaining provider canaries reached the backend, completed the `modernize-scientific-stack` canary task, and passed with clean contamination audits.

### router-grok-build-0.1

- Backend model: `grok-build-0.1`
- Result path: `results/phase3/canary/arm-router-grok-build-0.1/2026-06-04__03-06-37`
- Classification: `PASS`
- Harbor result: 1/1 completed, 0 exceptions, mean `1.000`, reward `1.0`
- Cost reported: `$0.710016`
- Contamination audit: clean

### router-kimi-k2.6

- Backend model: `kimi-k2.6`
- Classification: `PASS`
- Harbor result: 1/1 completed, 0 exceptions, mean `1.000`, reward `1.0`
- Cost reported: `$0.465169`
- Contamination audit: clean
- Note: direct provider probes showed `kimi-k2.6` requires either `temperature=1` or no temperature override; too-small `max_tokens` may return reasoning-only output before final answer.

### router-qwen-3.7-plus

- Backend model: `qwen3.7-plus`
- Classification: `PASS`
- Harbor result: 1/1 completed, 0 exceptions, mean `1.000`, reward `1.0`
- Cost reported: `$0.443505`
- Contamination audit: clean
- Route note: uses DashScope Singapore-compatible endpoint: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`.

### router-glm-5.1

- Backend model: `glm-5.1`
- Result path: `results/phase3/canary/arm-router-glm-5.1/2026-06-04__12-40-42`
- Classification: `PASS`
- Harbor result: 1/1 completed, 0 exceptions, mean `1.000`, reward `1.0`
- Cost reported: `$0.107285`
- Tokens: 40,707 input, 28,800 cache, 1,334 output
- Contamination audit: clean
- Note: grep hits for `AgentTimeoutError` came from Harbor config/lock metadata, not an observed exception.

<!-- phase3-2026-06-12-alignment:start -->
## 2026-06-12 alignment: current route findings

Current Phase 3 route findings to preserve:

- `router-anthropic-fable-5`: first canary attempt was an infrastructure timeout caused by Docker-to-host LiteLLM reachability. After persistent UFW rules were added and the runner doctor was updated, the rerun canary passed.
- `claude-mythos-5`: direct Anthropic probe returned HTTP 404 / `not_found_error`; treat as gated/unavailable for this account.
- `opusplan`: already covered in Phase 2 as canary/discovery evidence. It accepted the alias but did not show a visible true plan/execute cycle. Do not add it as a normal Phase 3 model arm.
- Hosted NVIDIA NIM: candidate hosted provider layer through LiteLLM. Add a benchmark arm only after direct API, LiteLLM route, Claude Code route, and Harbor canary probes pass.
- Locally hosted open-weight models and self-hosted NIM: tabled.
<!-- phase3-2026-06-12-alignment:end -->
