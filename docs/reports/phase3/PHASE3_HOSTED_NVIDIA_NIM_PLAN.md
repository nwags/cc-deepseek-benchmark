# Hosted NVIDIA NIM Route-Readiness Plan

Phase 3 treats NVIDIA NIM as a hosted provider/router layer, not as a local or self-hosted model-serving stack.

## Scope

In scope:

- Hosted NVIDIA NIM API access.
- LiteLLM route configuration for `nvidia_nim/...` models.
- Claude Code through Harbor using the same local LiteLLM proxy pattern as other router arms.
- Direct API, LiteLLM, Claude Code, and Harbor canary probes.

Out of scope for now:

- Self-hosted NVIDIA NIM.
- GPU runner provisioning.
- NVIDIA container runtime setup.
- Locally hosted open-weight model serving.

## Intended route

```text
Claude Code agent harness
  -> Anthropic-compatible Claude Code request
  -> local LiteLLM proxy
  -> LiteLLM NVIDIA NIM provider route
  -> NVIDIA hosted NIM OpenAI-compatible endpoint
  -> selected hosted NIM model
```

## Readiness sequence

1. Confirm `NVIDIA_API_KEY` exists locally and, later, as a GitHub Actions secret.
2. Run a direct hosted NVIDIA NIM `/v1/chat/completions` probe.
3. Add a temporary LiteLLM route in local config and run `/v1/models`.
4. Run a direct LiteLLM route probe.
5. Run a Claude Code route probe through the local LiteLLM proxy.
6. Add a reviewable `router-nvidia-nim-*` arm only after probes pass.
7. Run Harbor canary.
8. Add to smoke planning only after canary passes.

## Cost and quota note

Hosted NVIDIA NIM may not add a separate marketplace-router surcharge, but it can still have account quotas, rate limits, free-credit limits, or hosted endpoint constraints. Treat cost and quota behavior as a probe result, not an assumption.
