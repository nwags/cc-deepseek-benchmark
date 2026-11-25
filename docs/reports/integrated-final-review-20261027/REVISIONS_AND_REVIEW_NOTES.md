# Revision and review notes - October 27, 2026

This revision responds to the seven editorial/research issues raised against
the October 24 draft. It preserves that original package and the benchmark's
committed scientific record. The revised manuscript is authoritative for this
draft; its PDF is a generated reading copy. Human/controller approval remains
pending.

| Feedback | Concrete revision |
|---|---|
| Charts and graphs | Seven figures: architecture; raw/clean success and runtime; failure composition; quality/cost with evidence markers; task-family heatmap; source-scoped cached input; historical token-versus-spend shares. PNG and SVG assets and builders accompany the paper. |
| Costs rounded to cents | All human-facing manuscript USD amounts and ratios use decimal half-up rounding to two places. Totals are summed at source precision before rounding. Machine-readable evidence retains exact values for reproduction. |
| Test setup and architecture | Section 2 explains units, task selection, execution, scoring, containers/tools, gateway and sanitizer, observation/storage, reviewed evidence, controls, and gaps. Retained configuration audit identifies seven Claude Code versions and differing tool restrictions rather than assuming identical binaries/budgets. |
| Terminology introduced | Abstract/introduction and Methods define arms, runs, trials, selected runs, manifests, harness/backend/route, verifier, raw/clean/not-recorded outcomes, canonical versus live records, reconciliation, normalized absence, allocation, frontier, and token classes. Historical J2/DR/V3/V4 identifiers are introduced explicitly. |
| Research-paper organization | Abstract; Introduction with practical significance; Methods; Results; Discussion/recommendations; Challenges and mitigations; Conclusion. Detailed chronology, claim/test/access matrices, and review gate move to appendices. |
| Token-type findings | Section 3.5 separates input/cache-read/cache-write/output from reasoning-event metadata and unavailable reasoning/final-answer splits. It adds source-scoped usage, 868/960 thinking-event coverage, within-arm output/outcome medians with denominators, and historical token/cost contrasts. |
| Challenges and mitigations | Section 5 pairs nine concrete challenges with observed mitigations and residual limits, including task selection, dependence, software drift, public-task exposure, verifier/diagnostic limits, missing evidence, cost windows, token semantics, and retrospective selection. |

The token additions do not inspect or reproduce hidden reasoning. They use only
sanitized committed counters and classifications. Event counts are not token
counts. Zero event/counter observations are not proof of no internal reasoning
or no provider spend. No comparable 16-arm reasoning-versus-final token split
is claimed.

The prior focused Python and dashboard test counts remain attributed to the
October 24 review. This revision reruns the offline reproduction, adds metadata
and document/figure checks, and visually reviews the rendered PDF. Its validation
directory distinguishes those checks from retained prior logs.

## Website alignment after the report gate

The public website repository's main branch was rechecked at
`83fd7cbe047c06de3f1fd057d4f7a9627c712992`. No website file was changed.
The preceding audit found its V4 numeric export aligned with all 176 compared
fields in the accepted 16-arm comparison; the revised report does not alter
those scientific values. Alignment with the approved final manuscript will
require the following editorial work:

| Website surface | Alignment required |
|---|---|
| Benchmark report page | Replace the older emphasis on suspect no-op cases with the accepted failure taxonomy, including nine Fable refusals, 370 explicit failures, 28 not-recorded outcomes, and 19 successful timeout anomalies. |
| Methods and scope statements | Explain the same agent application, seven retained agent versions, workload selection, gateway/Haiku conditions, and limits of a controlled-comparison claim. Do not imply a single identical software/runtime environment. |
| Findings and charts | Reflect raw/clean success, runtime, family counterexamples, qualified cost frontier, token evidence, and challenge/mitigation limits. Keep historical plots and current V4 economics distinct. |
| Provider display | Map the existing Kimi K3 `moonshot` and Kimi K2.6 `moonshot-kimi` identifiers to a consistent human label/color without changing frozen canonical IDs. |
| Homepage and Documents links | Link the approved report and final PDF; label version/source dates consistently. |
| Resume/project summary | Check wording against the approved scope and attribution evidence; avoid universal quality claims, invented causal router claims, or unverified individual ownership. |

The revised PDF is a review draft. An approved final manuscript should generate
the final PDF before website changes are released. This package does not
authorize publication, merge, or push.
