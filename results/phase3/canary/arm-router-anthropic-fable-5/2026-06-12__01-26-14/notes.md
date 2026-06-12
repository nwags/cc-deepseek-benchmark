# router-anthropic-fable-5 canary

- Date/run: 2026-06-12__01-26-14
- Mode: canary
- Task: modernize-scientific-stack
- Result: FAIL
- Reward: 0.0
- Exception: AgentTimeoutError
- Runtime: 11m 5s
- Workflow: GitHub Actions Phase 3 Arm Dispatch on VPS runner
- Artifact: phase3-router-anthropic-fable-5-canary-27388393464
- Interpretation: infrastructure path executed, but Claude Code never received a successful first model response. Evidence: trajectory contains only the initial user instruction, final_metrics.total_steps=1, agent token counts are zero, and claude-code.txt shows repeated api_retry events with error="unknown".
- Follow-up probe: a local Pop!_OS non-streaming LiteLLM /v1/messages probe to router-anthropic-fable-5 succeeded with response "ok"; this does not yet prove the GitHub Actions/VPS Claude Code streaming path is healthy.

## Follow-up local Claude Code route probe

A local Pop!_OS Claude Code route probe using router-anthropic-fable-5 succeeded:

- Claude Code version: 2.1.140
- LiteLLM proxy version observed in response headers: 1.86.1
- Result: success
- Response: ok
- Actual assistant model in stream-json: claude-fable-5
- Duration: ~3.7s
- Usage: input_tokens=2, cache_creation_input_tokens=30921, output_tokens=4
- Cost: $0.19336625

Interpretation: the basic local Claude Code → LiteLLM → Fable route works. The failed canary is more likely specific to the VPS/GitHub Actions/Harbor/Docker path, or to version differences between local and runner environments.

## Follow-up VPS Claude Code route probe

A direct VPS host Claude Code route probe using router-anthropic-fable-5 succeeded:

- Host: vps-c691f5f6
- User: bench
- Claude Code version: 2.1.169
- LiteLLM version: 1.88.1
- Result: success
- Response: ok
- Actual assistant model in stream-json: claude-fable-5
- Duration: ~4.5s
- Usage: input_tokens=1601, cache_creation_input_tokens=24456, output_tokens=4
- Cost: $0.160955

Interpretation: the Fable route works from the VPS host. The failed canary is therefore more likely specific to the Harbor/Docker benchmark execution path, the benchmark container environment, or the Claude Code version/path used inside Harbor.

## Follow-up firewall diagnosis

Container reachability testing isolated the canary failure to Docker bridge traffic being blocked by UFW on the VPS runner:

- Host-network container to 127.0.0.1:4000 succeeded.
- Before firewall fix, Docker bridge containers timed out when reaching host LiteLLM on port 4000.
- Adding temporary INPUT rules for docker0/br+ to port 4000 made default bridge, host.docker.internal, and user-defined bridge probes succeed.
- Interpretation: the original canary's zero-token AgentTimeoutError was caused by container-to-host LiteLLM reachability, not Fable model quality.

