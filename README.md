# Claude Code Backend Benchmark: Anthropic vs DeepSeek

This repo benchmarks Claude Code on Terminal-Bench 2.0 via Harbor using three model backend configurations:

- Arm A: Anthropic Claude
- Arm B: DeepSeek V4-Pro through DeepSeek's Anthropic-compatible endpoint
- Arm C: DeepSeek V4-Flash through DeepSeek's Anthropic-compatible endpoint

The goal is to test whether swapping Claude Code's model backend from Anthropic to DeepSeek preserves task quality while improving speed and cost per resolved task.

## Reproduction

See scripts/ for benchmark commands.

Raw Harbor outputs are committed under results/.

Final analysis is in analysis.ipynb or analysis.md.

Final conclusions are in FINDINGS.md.

## Harbor CLI version note

The assignment PDF references older Harbor commands such as:

```bash
harbor list-datasets
harbor run --dataset terminal-bench@2.0
```
