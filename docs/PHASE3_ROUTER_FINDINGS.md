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
