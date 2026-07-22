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

<!-- phase3-2026-06-12-alignment:start -->
## 2026-06-12 Phase 3 coverage status convention

Use these statuses for Phase 3 model/provider coverage:

| Status | Meaning |
|---|---|
| `active` | Current route/model slug intended for canary/smoke/full-sweep consideration. |
| `canary-passed` | Harbor canary passed and the arm is eligible for smoke planning. |
| `superseded` | Earlier slug/config kept for provenance but replaced by a newer working route. |
| `gated` | Provider/model exists but account access is unavailable or denied. |
| `infra-failed` | Failure traced to runner/router infrastructure, not model quality. |
| `planned-probe` | Candidate provider/model requires direct API and LiteLLM route probes before an arm is added. |
| `tabled` | Out of current Phase 3 scope. |

Current special cases:

- Anthropic Fable 5: canary-passed after Docker/UFW firewall fix.
- Anthropic Mythos 5: gated/unavailable after direct API 404.
- OpusPlan: Phase 2 discovery finding only; not a normal Phase 3 arm.
- Hosted NVIDIA NIM: retired from active Phase 3 plan; revisit only under official paid/quota-approved access.
- Self-hosted NIM and locally hosted open-weight models: tabled.
<!-- phase3-2026-06-12-alignment:end -->
