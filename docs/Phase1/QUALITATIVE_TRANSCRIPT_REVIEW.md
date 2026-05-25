# Qualitative Transcript Review

## 6. Targeted transcript review of divergent tasks

### 6.1 `schemelike-metacircular-eval`: DeepSeek Pro advantage on symbolic/interpreter work

Outcome: Anthropic 0/3, DeepSeek Pro 3/3, Flash 0/3.

This was the strongest DeepSeek Pro-positive divergence. The task required writing `eval.scm`, a metacircular evaluator for the Scheme-like language implemented by `interp.py`. The successful Pro transcripts show that Pro read the interpreter and test programs, wrote `/app/eval.scm`, repeatedly tested it using `interp.py`, and patched the evaluator until the self-interpretation behavior matched. One Pro run used 42 Bash calls and multiple edits to `eval.scm`; another used 49 Bash calls and iterative comparisons against test programs.

The Anthropic and Flash failures looked different. One Anthropic run read files but then hit an output-token failure before writing a solution. Two Anthropic runs timed out. Flash showed the same pattern: reading and planning without producing a working evaluator, followed by timeouts or output-limit failure. This looks less like an Anthropic API-format mismatch and more like a task/model dynamic: the task demands sustained symbolic implementation and repeated testing. Pro was willing and able to iterate through that loop; Anthropic and Flash did not complete it under the timeout.

Hedge-fund workflow alignment: low to medium. Most hedge-fund workflows do not require metacircular Scheme interpreters. However, the task is relevant by analogy to DSLs, strategy-expression evaluators, query planners, custom rule engines, and internal research languages.

### 6.2 `cancel-async-tasks`: Flash advantage on compact async control-flow debugging

Outcome: Anthropic 0/3, DeepSeek Pro 1/3, Flash 3/3.

This task asked for an async `run_tasks` implementation that limits concurrency and handles keyboard interrupts so cleanup code still runs. Anthropic wrote a conventional `asyncio.Semaphore` plus `gather` solution. The verifier failure showed the classic gotcha: queued tasks above `max_concurrent` were still created, and cancellation behavior did not prevent queued tasks from starting or did not drain cleanup correctly.

Flash's successful run wrote a more operationally correct signal-aware implementation: it tracked a `running` set, installed signal handlers, used a `stop_event`, cancelled running tasks, avoided launching additional queued work after interruption, and drained cancelled tasks to allow cleanup. It also ran local tests. This is a good example where the smaller/faster model was not merely cheaper; it found a simpler correct pattern.

Hedge-fund workflow alignment: high. Async cancellation and bounded concurrency map directly to market-data ingestion, websocket consumers, order-routing services, streaming analytics, and batch job orchestration.

### 6.3 `build-cython-ext`: Anthropic advantage on exhaustive scientific-stack compatibility

Outcome: Anthropic 3/3, DeepSeek Pro 2/3, Flash 1/3.

The task required cloning and building `pyknotid` with Cython extensions under Python 3.13 and NumPy 2.x. The failure mode is very informative. DeepSeek Pro and Flash both handled much of the obvious migration: `fractions.gcd` to `math.gcd`, deprecated `np.float`, `np.int`, and `np.bool` aliases, building extensions, and running visible tests. But the failing runs missed a remaining Cython path in `ccomplexity`: the verifier failed at `cc.cython_higher_order_writhe(points, contributions, order)`, indicating a remaining NumPy alias or compiled-extension compatibility problem.

Anthropic's successful run appears to have performed a broader compatibility sweep across more files and did not stop at the happy-path example. This suggests a pattern: Anthropic was more exhaustive on dependency-migration work, while DeepSeek sometimes declared success after visible tests or after fixing the most obvious migration paths.

Hedge-fund workflow alignment: high. Quant and data teams frequently rely on compiled scientific Python, Cython/Numba/C++ extensions, and fragile NumPy/SciPy compatibility surfaces.

### 6.4 `query-optimize`: DeepSeek advantage on SQL rewrite/search strategy

Outcome: Anthropic 1/3, DeepSeek Pro 2/3, Flash 2/3.

This task required writing an optimized SQL query. Anthropic produced a plausible CTE/window-function rewrite but failed the runtime comparison in two attempts. A successful Pro run explicitly inspected the schema, used query-plan analysis, materialized word-level stats and sense counts, and removed repeated correlated subqueries. The final explanation correctly identified correlated scalar subqueries as the core performance problem.

This looks like a domain-specific reasoning advantage for the DeepSeek arms on this task family: they were more likely to target the cost driver rather than only rewrite the query into a cleaner but still insufficient form.

Hedge-fund workflow alignment: high. Query optimization is directly relevant to research databases, backtest stores, feature stores, tick/quote archives, metadata catalogs, and reporting systems.

### 6.5 `openssl-selfsigned-cert`: Flash dependency-assumption failure

Outcome: Anthropic 3/3, DeepSeek Pro 3/3, Flash 1/3.

The Flash failure inspected here generated the certificate artifacts but wrote a Python verification script that imported `cryptography`, which was not installed in the container. The verifier failed with `ModuleNotFoundError: No module named 'cryptography'`. That is a concrete failure type: the model assumed a dependency rather than constraining itself to the available runtime or using the standard library/openssl CLI.

This does not look like a DeepSeek Anthropic-format issue. It is a model/tooling failure: insufficient environment awareness and insufficient local verification under the actual dependency set.

Hedge-fund workflow alignment: medium to high. Certificate and internal TLS work is DevOps/security infrastructure, relevant to internal APIs and data services, though not alpha research itself.

### 6.6 `password-recovery`: Anthropic advantage on forensic exactness

Outcome: Anthropic 3/3, DeepSeek Pro 2/3, Flash 1/3.

Flash's inspected failure found a partial password and wrote `PASSWORD=8XDP5Q2RT9ZW54` to `/app/recovered_passwords.txt`, but the verifier expected the raw password `8XDP5Q2RT9ZK7VB3BV4WW54`. The failure combined two issues: including the `PASSWORD=` prefix and failing to reconstruct the missing middle segment. One DeepSeek Pro attempt timed out without producing the file; two Pro attempts succeeded.

This task rewards forensic search persistence and exact output formatting. Anthropic was more reliable. Flash's failure is a good example of a model producing a plausible-looking recovered value and final explanation while missing a hidden exact-match requirement.

Hedge-fund workflow alignment: medium. It is relevant to incident response, credential recovery, disk forensics, and security operations, but less representative of day-to-day quant engineering.

### 6.7 Hard tasks where all arms struggled

`polyglot-rust-c` and `torch-pipeline-parallelism` were 0/3 across all arms. These are not good model-differentiation examples in this run. They indicate benchmark hardness or harness/task mismatch more than provider-specific weakness.

`torch-pipeline-parallelism` is still hedge-fund relevant for ML infrastructure, but the specific task is specialized. `polyglot-rust-c` is lower relevance: it is an interesting compiler/polyglot puzzle, but uncommon in production fund workflows.

## 7. Patterns that emerged

1. **DeepSeek Pro is best on sustained abstract implementation.** The clearest example is `schemelike-metacircular-eval`, where Pro solved all attempts and both other arms failed.
2. **Flash can be surprisingly strong on compact fixes.** `cancel-async-tasks` was the clearest example: Flash solved 3/3 with a clean signal/cancellation-aware design.
3. **Anthropic is stronger on exhaustive compatibility and exactness.** `build-cython-ext`, `password-recovery`, and `openssl-selfsigned-cert` show cases where Anthropic or Pro avoided narrow happy-path fixes better than Flash.
4. **Data engineering and security tasks were among the most hedge-fund-relevant.** The most representative tasks were `query-optimize`, `multi-source-data-merger`, `build-cython-ext`, `modernize-scientific-stack`, `portfolio-optimization`, `llm-inference-batching-scheduler`, `fix-code-vulnerability`, and `git-leak-recovery`.
5. **Cheap does not mean fast.** DeepSeek Pro was cheap and high quality, but slower in agent execution. Flash was cheap and near Anthropic speed.

