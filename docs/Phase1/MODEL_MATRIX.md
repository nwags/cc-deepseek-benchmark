# Model Matrix

| Arm | Backend | Claude Code model setting | Purpose |
|---|---|---|---|
| anthropic-default | Anthropic | no explicit `--model` flag; observed smoke resolved to `claude-opus-4-7[1m]` | Test Claude Code’s actual default model-selection behavior in Harbor |
| anthropic-sonnet | Anthropic | `anthropic/claude-sonnet-4-6` or `sonnet` | Phase 1 comparable control |
| anthropic-haiku | Anthropic | pinned `anthropic/claude-haiku-4-5-20251001` | Fast/cheap Haiku arm |
| anthropic-opus | Anthropic | `opus` or pinned Opus | High-reasoning arm, budget permitting |
| anthropic-opusplan | Anthropic | `opusplan`; canary observed `claude-sonnet-4-6` only and no visible Plan Mode | Experimental canary only unless plan mode can be activated |
| deepseek-pro | DeepSeek | `deepseek-v4-pro[1m]` via Anthropic-compatible env override | Phase 1 DeepSeek quality/cost arm |
| deepseek-flash | DeepSeek | `deepseek-v4-flash` via Anthropic-compatible env override | Phase 1 DeepSeek cheap/fast arm |
