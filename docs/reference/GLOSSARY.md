# Glossary

| Term | Definition |
|---|---|
| Agent | A system that uses an LLM inside a loop that can inspect state, use tools, run commands, edit files, and re-plan. |
| Agent harness | The scaffolding around the model: prompt format, tools, shell/file access, retry logic, and planning loop. Claude Code is the harness here. |
| AgentTimeoutError | Harbor exception when the agent exceeds the task or agent timeout. It is counted as a failed trial unless there is evidence of infrastructure failure. |
| Agent turn | One model/harness step in the trajectory. This report counts `source == agent` steps in `agent/trajectory.json`. |
| Anthropic-compatible API | An API that accepts the Anthropic Messages API format. DeepSeek exposes one at `https://api.deepseek.com/anthropic`. |
| Arm | An **arm** is one controlled experimental condition in the benchmark matrix. In this project, an arm usually corresponds to a specific combination of agent harness, router configuration, provider backend, model version, environment variables, tool policy, and run mode. For example, `router-qwen-3.7-plus`, `router-deepseek-pro`, and `router-gpt-5.5` are separate benchmark arms because each represents a distinct model/provider/configuration path being evaluated under the same benchmark harness. |
| Cache-hit input token | Input token billed at a lower cached-prefix rate. |
| Claude Code | Anthropic terminal coding agent used as the fixed harness in this experiment. |
| Cost per resolved task | Total arm spend divided by unique tasks solved at least once. |
| DeepSeek V4-Pro | DeepSeek quality-oriented backend tested through Claude Code's Anthropic-compatible configuration. |
| DeepSeek V4-Flash | DeepSeek lower-cost/faster backend tested through Claude Code's Anthropic-compatible configuration. |
| Failure mode | Assignment-requested category for failed trials: refused-to-try, looped, ran-out-of-budget, produced-wrong-output, or timed-out. |
| Harbor | Framework used to run Terminal-Bench tasks and agents reproducibly. |
| MCP server | Model Context Protocol server exposing tools/data/workflows to MCP clients. MCP was not central to this benchmark but is relevant background for agent tooling. |
| Oracle agent | Harbor reference-solution agent used as a sanity ceiling before paid model runs. |
| SWE-bench | Benchmark of real GitHub issues where systems must generate patches that resolve repository issues and pass tests. |
| SWE-bench Verified | Human-filtered SWE-bench subset of 500 instances. Useful context but not the main benchmark here because this project isolates Claude Code backend substitution. |
| Terminal-Bench 2.0 | Benchmark of realistic command-line tasks in containerized environments. |
| Tool call | A structured action requested by the agent, such as Bash, Read, Write, Edit, Grep, or Glob. |
| Wilson interval | Binomial confidence interval used for success rates with modest sample sizes. |