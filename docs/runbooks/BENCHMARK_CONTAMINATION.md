# Benchmark Contamination Controls

This document records benchmark-contamination risks and the current mitigation procedure for Phase 3 and later phases.

## Current status

Phase 1 and Phase 2 used public Terminal-Bench 2.0 tasks. Phase 3 also uses the same public task subset unless a later private holdout set is added.

The existing artifacts show that Claude Code may initialize with WebSearch and WebFetch available in its tool list. Tool availability is not the same as tool use, but it means reports should not claim the benchmark was web-isolated unless that is explicitly enforced and audited.

Phase 3 router work currently uses LiteLLM as a local gateway. Task containers need network access to the LiteLLM endpoint at the Docker host gateway, currently `http://172.17.0.1:4000`. Any future network restriction must preserve access to that endpoint.

## Main contamination risks

1. Training contamination

   Public benchmark tasks may have appeared in model training data.

2. Live web lookup

   The coding agent could use WebSearch, WebFetch, or direct network access if those capabilities are available.

3. Provider-side tools

   A backend provider may expose web search, retrieval, or agentic tool modes outside Claude Code if a web-enabled model or parameter set is selected.

4. Repo/log leakage

   Public raw results, reports, and transcripts may make task solutions easier for future systems to memorize.

## Current audit command

Run:

    make contamination-audit

Equivalent direct command:

    uv run python scripts/audit_tool_usage.py --strict results/phase1 results/phase2 results/phase3

The audit scans candidate Claude Code artifacts including `trajectory.json`, `claude-code.txt`, and session `.jsonl` files. It reports actual WebSearch/WebFetch tool-use events and separately reports init records where web tools were merely available.

Tool availability is not counted as usage.

## Interpretation

If the audit reports zero actual WebSearch/WebFetch usage, the repo may say:

- No actual WebSearch/WebFetch tool-use events were detected in scanned artifacts.

It should not say:

- Models were prevented from using the web.
- The benchmark is contamination-proof.
- The tasks are private holdouts.

If actual WebSearch/WebFetch usage is detected, the affected runs should be marked as contaminated or excluded from scored benchmark claims unless the run intentionally tested web-enabled agents.

## Recommended policy before scored Phase 3 runs

Before full scored Phase 3 sweeps:

1. Run `make contamination-audit`.
2. Avoid provider web-search-enabled model variants or API parameters.
3. Prefer explicit Claude Code permission rules that deny WebSearch and WebFetch if they can be passed reproducibly through Harbor.
4. Consider network egress restrictions that still allow the task container to reach LiteLLM.
5. Document whether the run is public-task benchmark evidence or private-holdout evidence.

## Stronger future mitigation

For stronger sponsor-grade claims, create private or newly authored tasks that are not published before evaluation. Public Terminal-Bench results remain useful for reproducibility and comparability, but they should be described as public-benchmark results rather than contamination-proof private evaluations.

## Initial historical audit finding

The first repository-wide audit found actual WebSearch/WebFetch tool-use events in historical Phase 1/2 artifacts.

Affected historical artifacts included:

- Phase 1: DeepSeek Pro on `polyglot-rust-c`
- Phase 2: DeepSeek Flash on `torch-pipeline-parallelism`
- Phase 2: DeepSeek Flash on `polyglot-rust-c`

The audit reported 26 raw WebSearch/WebFetch event records, but those records are repeated transcript/session representations of a smaller number of affected trials. These historical findings should be treated as a benchmark-validity caveat, not as a reason to delete or rewrite frozen Phase 1/2 results.

Going forward:

- do not claim Phase 1 or Phase 2 were web-isolated;
- disclose that actual web-tool use was later detected in a small number of historical trials;
- require strict contamination audit checks for new scored Phase 3+ runs;
- prefer explicit WebSearch/WebFetch denial or network controls before full scored sweeps.

For current and future work, use:

    make contamination-audit

to produce a non-failing full historical report, and use:

    make contamination-audit-strict

to fail if actual WebSearch/WebFetch usage is found under `AUDIT_ROOTS`, which defaults to `results/phase3`.

To audit a specific future result directory strictly:

    make contamination-audit-strict AUDIT_ROOTS=results/phase3/raw

## Patch B network-egress probe finding

A Phase 3 diagnostic probe tested Harbor's Docker `allow_internet=false` environment kwarg with router-mediated Claude Code and LiteLLM. Harbor recorded `allow_internet=false` in the run artifacts, but the retained Docker task container still used a normal compose network rather than `network_mode: none`.

A direct connectivity check from the retained task container showed:

- Public egress to `https://example.com` succeeded.
- The LiteLLM endpoint at `http://172.17.0.1:4000/v1/models` was reachable and returned `401 Unauthorized` without the required bearer token.
- Therefore the task container had both public internet egress and host-gateway LiteLLM reachability.

Conclusion: do not rely on Harbor `allow_internet=false` as the Phase 3 network-egress control until a stronger Docker/network rule is implemented and verified. For current Phase 3 runs, the verified contamination controls are:

1. Deny Claude Code WebSearch/WebFetch with `--agent-kwarg disallowed_tools=WebSearch,WebFetch`.
2. Audit artifacts with `scripts/audit_tool_usage.py --strict --fail-on-available`.
3. Treat public Terminal-Bench results as public-benchmark results, not contamination-proof private evaluations.

## Router Haiku compatibility finding

The Phase 3 router Haiku canary and smoke attempts failed before meaningful task execution. The failures were `NonZeroAgentExitCodeError` from Claude Code after the LiteLLM/Anthropic request returned HTTP 400.

Observed provider-side error:

- `adaptive thinking is not supported on this model`
- `This model does not support the effort parameter`

A follow-up manual canary with `--agent-kwarg max_thinking_tokens=0` still failed, which suggests the current Claude Code + LiteLLM Anthropic-router path is still sending an unsupported `effort`/adaptive-thinking parameter to the Haiku backend.

Conclusion: `router-anthropic-haiku` is currently incompatible with the Phase 3 Claude Code + LiteLLM router harness. Do not treat these Haiku router failures as model-quality benchmark failures. Keep direct Phase 2 Haiku results as the meaningful Haiku evidence unless/until the router can strip the unsupported parameter or Claude Code exposes a true no-effort/no-thinking mode for this path.
