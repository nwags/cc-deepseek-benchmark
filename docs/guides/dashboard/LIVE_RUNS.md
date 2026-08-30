# Live Runs page guide

## Executive summary

Live Runs is mutable execution observation, not canonical benchmark truth. It shows shared live
Supabase state, heartbeat liveness, observable output/tool events, stable completed partial trials,
and progressive R2 artifacts while a supervised execution is in progress. Final publication can
change or complete what is visible here.

## Route and implementation

- Dashboard route: `/runs/live`.
- Page source: `apps/dashboard/src/app/runs/live/page.tsx`.

## Data sources

- Shared live Supabase relations queried by `live-data.ts` for recent, active, stale, selected-run,
  event, trial, and artifact state.
- Progressive R2 artifact references for stable completed-trial files.
- An explicitly enabled local-development fallback (`DASHBOARD_LIVE_LOCAL_FALLBACK=true`) may be
  used only after cloud reads fail.
- Heartbeat and event timestamps feed the liveness notice; stale state uses
  `LIVE_STALE_AFTER_SECONDS`.

## Population and authority

- Recent live executions are mutable operational observations, including active, stale, completed,
  failed, or interrupted supervision state.
- Partial trial rows appear only when stable parseable completion evidence has been observed.
- Observed token/cost counters are partial and subject to later canonical/provider reconciliation.
- Live artifact metadata and bytes do not become canonical benchmark evidence merely because they
  are visible here.

## How to read the page

- Use heartbeat/liveness first to decide whether the displayed execution state is current enough to
  interpret.
- Use warnings, tool activity, observable output, partial trials, progressive artifacts, and event
  tail as separate observation channels.
- Tool activity exposes structured observable tool-use/result lifecycle records; thinking/private
  reasoning content is not parsed or displayed.
- Canonical publication status is distinct from benchmark status and live publication status.

## Controls and filters

- `live_run_id` selects a particular execution; absent input selects the most recent returned row.
- While a non-stale active run exists, the page auto-refreshes every eight seconds.
- Section navigation appears for selected-execution details.
- Local fallback is configuration-gated and is clearly labeled when used.

## Caveats and non-inferences

- Partial reward, cost, token, event, and artifact information may change before final canonical
  publication.
- This is not an independent runner-fleet availability/capacity monitor; runner names are execution
  metadata.
- A successful live observation is not proof that final R2 reconciliation or canonical Supabase
  publication succeeded.
- Database/migration failure does not cause live observations to be substituted into canonical Runs.

## Common workflows

- Use Live Runs during a supervised execution to detect stalls, warnings, provider/runtime errors,
  and completed stable trials.
- After execution, move to canonical Runs and Artifacts to verify what was finally published.
- Use Architecture and the live supervision runbook when diagnosing whether a problem is in Harbor
  execution, observation, progressive upload, or final publication.

## Evidence tracing

- Live execution → selected `live_run_id` → events/partial trials/progressive artifacts.
- Progressive artifact → `/live-artifacts/[artifactId]` → R2 object metadata/preview.
- After final publication → canonical arm-run link → Runs → canonical trial/artifact evidence.

## Related documentation

- [Codebase Guide](../CODEBASE_GUIDE.md) for implementation and provenance boundaries.
- [Runs page guide](RUNS.md).
- [Architecture page guide](ARCHITECTURE.md).
- [Live Run Supervision runbook](../../runbooks/LIVE_RUN_SUPERVISION.md).
