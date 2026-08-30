# Glossary

| Term | Definition |
|---|---|
| Agent | A system that uses an LLM inside a loop that can inspect state, use tools, run commands, edit files, and re-plan. |
| Agent harness | The scaffolding around the model: prompt format, tools, shell/file access, retry logic, and planning loop. Claude Code is the fixed principal harness for Phases 1–3; Phase 4 is planned to study this dimension. |
| AgentTimeoutError | Harbor exception when the agent exceeds the task or agent timeout. It is counted as a failed trial unless there is evidence of infrastructure failure. |
| Agent turn | One model/harness step in the trajectory. This report counts `source == agent` steps in `agent/trajectory.json`. |
| Anthropic-compatible API | An API that accepts the Anthropic Messages API format. DeepSeek exposes one at `https://api.deepseek.com/anthropic`. |
| Arm | An **arm** is one controlled experimental condition in the benchmark matrix. In this project, an arm usually corresponds to a specific combination of agent harness, router configuration, provider backend, model version, environment variables, tool policy, and run mode. For example, `router-qwen-3.7-plus`, `router-deepseek-pro`, and `router-gpt-5.5` are separate benchmark arms because each represents a distinct model/provider/configuration path being evaluated under the same benchmark harness. The term comes from experimental design, including clinical trials and A/B testing, where each arm is a treatment or variant being compared. |
| Cache-hit input token | Input token billed at a lower cached-prefix rate. |
| Canary | The cheapest practical paid qualification stage used to establish provider visibility, model identity, and a candidate usage/cost authority before Smoke. |
| Claude Code | Anthropic terminal coding agent used as the fixed principal harness for Phases 1–3. |
| Cost reconciliation | Reviewed arm-run record that evaluates cost evidence and selects the decision-facing cost, basis, relation, validation status, and limitations without overwriting raw harness cost. |
| Effective advancement | The derived state represented by `effective_can_advance`; true only when the current promotion gate has no fail-closed derived blockers. |
| Evidence promotion gate | Durable reviewed decision binding an arm, exact source arm run, transition, and exact current usage/cost reconciliations. Historical gates may remain stored without authorizing advancement. |
| Cost per resolved task | Total arm spend divided by unique tasks solved at least once. |
| DeepSeek V4-Pro | DeepSeek quality-oriented backend tested through Claude Code's Anthropic-compatible configuration. |
| DeepSeek V4-Flash | DeepSeek lower-cost/faster backend tested through Claude Code's Anthropic-compatible configuration. |
| Failure mode | Assignment-requested category for failed trials: refused-to-try, looped, ran-out-of-budget, produced-wrong-output, or timed-out. |
| Full sweep | The scored experimental stage that should begin only after Smoke has exact or qualified usage and cost authority. Full is not intended to discover basic telemetry semantics. |
| Harbor | Framework used to run Terminal-Bench tasks and agents reproducibly. |
| MCP server | Model Context Protocol server exposing tools/data/workflows to MCP clients. MCP was not central to this benchmark but is relevant background for agent tooling. |
| Model identity status | Reconciliation judgment recording whether the configured/harness/provider-observed model identities are matched, mismatched, or unknown. |
| Oracle agent | Harbor reference-solution agent used as a sanity ceiling before paid model runs. |
| Promotion review | Human review that records `pass`, `blocked`, or `waived` against one exact source arm run and evidence chain. The durable operator path is `scripts/review_evidence_promotion.py`. |
| Provider cost evidence | Independent first-party or provider-derived evidence used to validate economic cost, such as billed charges, invoices/dashboard totals, or provider usage combined with a pinned pricing snapshot. |
| Provider usage evidence | Independent provider evidence used to validate model identity and token/request usage. |
| Reconciliation | Reviewed layer that compares raw/harness evidence with provider evidence and selects a defensible authority while retaining both sources as provenance. |
| Selected cost basis | The reviewed basis explaining why a selected decision-facing cost is authoritative, such as provider billed, rate reconstructed, validated harness reported, or explicit lower bound. |
| Selected cost relation | Whether selected cost is exact, an estimate, a lower bound, or unresolved. |
| Selected usage authority | The reviewed source selected as authoritative for arm-run usage, such as provider request usage, provider aggregate usage, validated harness usage, or none. |
| Smoke | Repeatability and telemetry-qualification stage after Canary. Smoke must establish exact or qualified usage and cost authority before Full. |
| State fingerprint | SHA-256 emitted by promotion `--check-only` over the material reviewed source-run, reconciliation, limitation, and current-gate state. Mutation modes reject a changed fingerprint. |
| SWE-bench | Benchmark of real GitHub issues where systems must generate patches that resolve repository issues and pass tests. |
| SWE-bench Verified | Human-filtered SWE-bench subset of 500 instances. Useful context but not the main benchmark here because this project isolates Claude Code backend substitution. |
| Terminal-Bench 2.0 | Benchmark of realistic command-line tasks in containerized environments. |
| Tool call | A structured action requested by the agent, such as Bash, Read, Write, Edit, Grep, or Glob. |
| Usage reconciliation | Reviewed arm-run record that evaluates provider/harness usage and model identity and selects the current usage authority and validation status. |
| Waived promotion decision | Explicit attributable exception record with a waiver reason. It remains non-authorizing: `effective_can_advance` must be false until a later evidence-qualified pass supersedes it. |
| Wilson interval | Binomial confidence interval used for success rates with modest sample sizes. |