# Task Selection

The benchmark uses a 20-task subset from the 89 tasks available in `terminal-bench@2.0`.

The assignment asks for a representative subset stratified by difficulty and category. Harbor 0.6.6 exposed task names locally but did not expose a clean difficulty/category table through the CLI, so this repo uses a manually stratified subset by visible task theme.

## Selected tasks

| Task | Theme |
|---|---|
| build-cython-ext | build/toolchain |
| cancel-async-tasks | Python/concurrency debugging |
| custom-memory-heap-crash | C++/memory debugging |
| fix-code-vulnerability | security/software engineering |
| git-leak-recovery | security/recovery |
| multi-source-data-merger | data engineering |
| modernize-scientific-stack | scientific Python modernization |
| query-optimize | database/query optimization |
| portfolio-optimization | numerical/performance |
| rstan-to-pystan | statistical modeling / migration |
| mteb-retrieve | retrieval / ML evaluation |
| llm-inference-batching-scheduler | LLM systems / scheduling |
| torch-pipeline-parallelism | distributed ML systems |
| configure-git-webserver | systems/admin |
| nginx-request-logging | webserver/admin |
| openssl-selfsigned-cert | security/admin |
| sqlite-db-truncate | database recovery |
| password-recovery | security/recovery |
| polyglot-rust-c | systems programming / interoperability |
| schemelike-metacircular-eval | programming languages / interpreter debugging |

## Notes

The same `tasks.txt` is used for all three benchmark arms:

- Arm A: Anthropic Claude backend
- Arm B: DeepSeek V4-Pro backend
- Arm C: DeepSeek V4-Flash backend

Each arm runs 3 attempts per task.
