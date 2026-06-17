# Phase 3 Three-Slot Smoke Wave — 2026-06-16

## Summary

This wave tested three simultaneous Phase 3 smoke runs while also exercising the current runner-slot concurrency model.

Arms:

- `router-gpt-5.5`
- `router-gemini-3.1-pro`
- `router-gemini-flash`

Result: local runner concurrency worked, but Gemini-family provider concurrency showed rate-limit / quota-pressure symptoms. Future dashboard dispatch should model provider-family concurrency separately from runner capacity.

## Runs

| Arm | Run ID | Runner | LiteLLM port | Mean | Errors | Cost |
|---|---:|---|---:|---:|---:|---:|
| `router-gpt-5.5` | `27641152143` | `vps-c691f5f6` | `4000` | `0.200` | `0` | `$9.50053` |
| `router-gemini-3.1-pro` | `27641156327` | `vps-c691f5f6-slot3` | `4002` | `0.200` | `3` | `$8.01802` |
| `router-gemini-flash` | `27641161172` | `vps-c691f5f6-slot2` | `4001` | `0.400` | `4` | `$16.79284` |

## Artifacts

| Arm | Artifact ID |
|---|---:|
| `router-gpt-5.5` | `7678260061` |
| `router-gemini-3.1-pro` | `7678586897` |
| `router-gemini-flash` | `7679167668` |

## Task results

### `router-gpt-5.5`

- Completed trials: 5
- Errored trials: 0
- Input tokens: 1,580,546
- Cache tokens: 0
- Output tokens: 63,912
- Cost: $9.50053
- Passing task:
  - `modernize-scientific-stack`
- Failing tasks:
  - `schemelike-metacircular-eval`
  - `query-optimize`
  - `cancel-async-tasks`
  - `build-cython-ext`

### `router-gemini-3.1-pro`

- Completed trials: 5
- Errored trials: 3
- Input tokens: 2,255,522
- Cache tokens: 807,305
- Output tokens: 26,141
- Cost: $8.01802
- Passing task:
  - `modernize-scientific-stack`
- Failing tasks:
  - `schemelike-metacircular-eval`
  - `cancel-async-tasks`
  - `build-cython-ext`
- Exceptions:
  - `AgentTimeoutError`: `query-optimize`
  - `NonZeroAgentExitCodeError`: `cancel-async-tasks`, `build-cython-ext`
- Provider signal:
  - Gemini `429 Too Many Requests`

### `router-gemini-flash`

- Completed trials: 5
- Errored trials: 4
- Input tokens: 3,805,021
- Cache tokens: 268,335
- Output tokens: 67,627
- Cost: $16.79284
- Passing tasks:
  - `schemelike-metacircular-eval`
  - `cancel-async-tasks`
- Failing tasks:
  - `modernize-scientific-stack`
  - `query-optimize`
  - `build-cython-ext`
- Exceptions:
  - `AgentTimeoutError`: `modernize-scientific-stack`, `query-optimize`
  - `NonZeroAgentExitCodeError`: `cancel-async-tasks`, `build-cython-ext`
- Provider signal:
  - Gemini `429 Too Many Requests`

## Infrastructure finding

The 3-slot runner model worked:

- Three GitHub Actions jobs started concurrently.
- Each job landed on a separate runner slot.
- Each job used a distinct LiteLLM port.
- Artifacts uploaded successfully.
- Post-run VPS health check showed no active LiteLLM ports, no running benchmark containers, low load, and healthy memory/disk state.

## Provider-concurrency finding

The Gemini runs should not be interpreted as clean model-quality measurements without qualification. Both Gemini-family arms ran at the same time and encountered provider-side `429 Too Many Requests` errors.

Working interpretation:

- This was not a local runner-capacity failure.
- This was not a dashboard/planner failure.
- This was not necessarily a lack-of-funds problem.
- It is most likely a Gemini project/account/model rate-limit, quota, or throughput/capacity issue under parallel Gemini load.

## Dashboard implication

Dashboard dispatch should model two separate constraints:

1. Runner capacity
   - Current practical limit: 3 runner slots.
   - Current safe Harbor concurrency: `n_concurrent=1`.

2. Provider-family capacity
   - Gemini: default to max 1 concurrent Gemini-family arm until quota is verified or raised.
   - Qwen: block full-sweep use until Alibaba identity verification and official usage reporting are reconciled.
   - Fable: block until provider availability is restored.

## Planning note

A future dashboard run-plan validator should warn on a plan such as:

- `router-gemini-3.1-pro`
- `router-gemini-flash`

because that is two Gemini-family arms in the same wave.

A safer wave shape is:

- one Gemini-family arm
- one OpenAI arm
- one Anthropic, DeepSeek, Grok, Kimi, or GLM arm
