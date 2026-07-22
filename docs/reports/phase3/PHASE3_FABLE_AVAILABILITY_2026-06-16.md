# Phase 3 Fable 5 Availability Probe — 2026-06-16

## Summary

`router-anthropic-fable-5` should be treated as temporarily unavailable / provider-gated, not as a scored model-quality failure.

## Probe

- Workflow run: `27636587839`
- Arm: `router-anthropic-fable-5`
- Mode: `canary`
- Task: `modernize-scientific-stack`
- Label: `fable-availability-probe`
- Result path:
  `results/phase3/ad-hoc/fable-availability-probe/arm-router-anthropic-fable-5/2026-06-16__17-42-58/`

## Result

- Trials: 1
- Errors: 1
- Mean: 0.0
- Exception: `NonZeroAgentExitCodeError`
- Input tokens: 0
- Cache tokens: 0
- Output tokens: 0
- Cost: 0.0 USD

## Provider response

LiteLLM surfaced an Anthropic 404 / `not_found_error`:

> Claude Fable 5 is not available. Please use Opus 4.8.

## Interpretation

This is a provider availability / access-gating failure. It should not be counted as a scored Phase 3 smoke result for Fable quality. Do not rerun full Fable smoke until access is restored. If a replacement Anthropic high-end arm is needed, use the Opus route instead.
