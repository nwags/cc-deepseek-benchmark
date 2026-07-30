# Live Run Supervision

## Scope

The live supervision path observes benchmark execution without exposing Harbor,
Docker, the Docker socket, SSH, or a new inbound service. Remote runners push
live metadata to Supabase and stable completed-trial artifacts to Cloudflare R2.
The local dashboard reads those shared services and never connects directly to
either VPS.

Observable process output is not hidden or private model reasoning. Live trial
rows are partial and may change until final canonical ingestion.

## Runner topology

All six slots have `self-hosted`, `Linux`, `X64`, and `cc-bench`.

| VPS | Runner display name | Routing labels |
|---|---|---|
| 1 | `vps-c691f5f6` | `cc-bench-vps1`, `cc-bench-slot-1` |
| 1 | `vps-c691f5f6-slot2` | `cc-bench-vps1`, `cc-bench-slot-2` |
| 1 | `vps-c691f5f6-slot3` | `cc-bench-vps1`, `cc-bench-slot-3` |
| 2 | `vps-phase3-vps2-slot4` | `cc-bench-vps2`, `cc-bench-slot-4` |
| 2 | `vps-phase3-vps2-slot5` | `cc-bench-vps2`, `cc-bench-slot-5` |
| 2 | `vps-phase3-vps2-slot6` | `cc-bench-vps2`, `cc-bench-slot-6` |

Display names are opaque. Do not parse them for routing. Use `runner_label` in
`phase3-arm-dispatch-v2.yml`; choose `cc-bench` for the broad pool or pin a host
or slot. The first later zero-cost deployment validation is intended for
`cc-bench-slot-4`.

Each runner registration owns an independent Actions workspace. Discovery is
restricted to `GITHUB_WORKSPACE`, the current arm/mode output roots, and a
pre-run snapshot. It never searches globally under `/home/bench`.
Discovered run and trial directories must be real directories, not symlinks.
Every result and allowlisted artifact is resolved beneath the workspace and its
run/trial parent again immediately before read, hash, or upload.

## Data flow

During execution:

1. `scripts/run_arm_live.py` writes redacted `.run/live/<live-run-id>.ndjson`.
2. A bounded queue batches live-run and event writes to
   `benchmark.live_runs` and `benchmark.live_run_events`.
3. A low-priority scanner identifies stable parseable completed trials and
   upserts `benchmark.live_trials`.
4. Stable allowlisted files are hashed and uploaded to execution-isolated,
   SHA-256-addressed R2 keys, then recorded in `benchmark.live_artifacts`.
5. Database or R2 failures emit a local warning and do not stop Harbor.

After execution, `scripts/publish_phase3_run.py` discovers exactly one
current-job run directory, builds the existing canonical ingestion manifest,
reconciles progressive uploads, uploads anything missing, and reuses
`scripts/ingest_phase3_run_metadata.py` to upsert:

- `benchmark.benchmark_arm_runs`
- `benchmark.benchmark_trials`
- `benchmark.benchmark_artifacts`

Before any canonical upload or insert, the publisher requires parseable root
final timestamps, zero pending/running/cancelled trials, internally consistent
root counters, complete trial results, and an exact expected-trial match when
live context provides one. Complete error-bearing runs remain eligible;
interrupted, partial, ambiguous, and inconsistent runs remain live-only.

The publisher verifies exact trial/artifact counts, SHA-256 and size metadata
through R2 `HEAD` calls, `benchmark.v_dashboard_arms`, and the
live-to-canonical arm-run link. Valid, explicitly invalid, and unclassified
suite states are reported as observed classifications; appearing as both valid
and invalid is rejected.

R2 upload and remote object verification complete before canonical database
publication begins. Canonical insertion, child-row replacement, live-run
linking, count/classification/dashboard verification, and the terminal live
publication state then use one PostgreSQL connection and transaction. The
transaction commits only after verification succeeds; any failed check rolls
back the complete canonical database attempt, including replacement deletes.

Every finalized manifest has a deterministic publication fingerprint over
stable run identity and final counters, trial identities/results, and
run-relative artifact paths, SHA-256 values, and sizes. Publisher timestamps,
absolute paths, R2 URIs, and JSON key order are excluded. The fingerprint is
stored in canonical and live metadata on first success. A completed supervised
publication, or an exact execution-scoped unsupervised publication, is a
verified immutable no-op: the publisher compares the fingerprint and canonical
children, verifies all referenced R2 metadata, and performs no upload, child
delete, or reinsertion. Conflicting replay evidence is a hard failure.

Final canonical R2 keys are execution-isolated and content-addressed by
SHA-256. An exact existing object is reused only after a matching `HEAD`;
different checksum, metadata size, or content length fails publication rather
than overwriting it.

The workflow publisher does not enable destructive replacement of trial rows.
If a pre-existing run has dependent `benchmark_trial_cost_coverage` or
`contamination_audits` rows, replacement is refused. The standalone maintenance
ingester retains `--allow-dependent-trial-replacement` for an explicitly
reviewed repair, and that operation can delete trial-linked derived rows through
foreign-key cascades. Metadata-only ingestion still preserves exact legacy R2
coverage by run-relative path, SHA-256, and size.

GitHub run ID, run attempt, opaque runner name, arm, and mode contribute to the
live-run ID and progressive R2 prefix. Workflow canonical labels and final R2
prefixes are execution-scoped; live-supervised publications use the
deterministic live ID. Workflow retries and concurrent slots therefore cannot
overwrite one another. The standalone historical ingester retains legacy
arm/timestamp labels, and metadata-only re-ingestion reconciles legacy absolute
and current relative artifact paths by run-relative path, SHA-256, and size.

## Database migration

`db/migrations/phase3/009_live_run_supervision.sql` adds:

- `benchmark.live_runs`
- `benchmark.live_run_events`
- `benchmark.live_trials`
- `benchmark.live_artifacts`

It includes uniqueness constraints and indexes for recent/active/stale runs,
GitHub execution identity, runner identity, ordered events, trial status, and
artifact lookup. Do not apply it as part of a benchmark job.

After the rollback-only integration has passed, first run the permanent
application utility in read-only preflight mode:

```bash
uv run --with 'psycopg[binary]' \
  python scripts/apply_live_supervision_migration.py \
  --check-only \
  --expected-sha256 df828690b8ee007c3a6a96966226bd47169b3c13fa5217f2ddcd349098cb8404
```

Review its database identity, migration hash, and preflight result. Only then
apply the reviewed migration:

```bash
uv run --with 'psycopg[binary]' \
  python scripts/apply_live_supervision_migration.py \
  --apply \
  --expected-sha256 df828690b8ee007c3a6a96966226bd47169b3c13fa5217f2ddcd349098cb8404 \
  --evidence-out .run/review/live-supervision-migration-009-application.json
```

`scripts/apply_live_supervision_migration.py` can apply only migration `009`;
it does not accept an arbitrary SQL path. It hashes the exact migration bytes
before connecting and requires both the operator-supplied hash and its internal
reviewed hash pin to match. It refuses an existing or partial live schema,
checks required canonical tables and views, and never reads or writes Supabase
subsystem migration registries. Application uses one transaction and a
migration-specific transaction advisory lock, repeats preflight after acquiring
the lock, verifies the schema before commit, and verifies it again from a second
connection after commit. The optional evidence JSON is written atomically to a
non-symlink path; the recommended `.run/review` location is local and ignored.
The evidence path is no-clobber and must not already exist. A retry must use a
new reviewed evidence filename rather than replacing the first attempt's
record. Every result reports whether the database commit was confirmed before
any later evidence or second-connection verification failure.

## Secrets

GitHub Actions uses these repository secrets:

- `SUPABASE_DB_URL`
- `R2_BUCKET`
- `R2_ENDPOINT_URL`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_REGION`

`R2_PREFIX` and `R2_ACCOUNT_ID` are optional. Provider and LiteLLM secrets
remain separate. The wrapper adds values from workspace-local `.secrets/*.env`
to its in-memory redactor without publishing secret names and values together.
Direct environment credentials remain supported. Validation prints missing
variable names only.

## Workflow controls

The primary dispatch defaults to:

- `supervise_live=true`
- `publish_results=false`
- `progressive_artifacts=false`
- `authorize_phase3_repair=false`
- `runner_label=cc-bench`

Phase 3 is closed. The completed `phase3-canary-1`, `phase3-smoke-5`, and
`phase3-full-20` suites reject new non-dry canonical publication by default.
An operator-approved repair must explicitly set both `publish_results=true`
and `authorize_phase3_repair=true`; progressive repair artifacts additionally
require `progressive_artifacts=true`. The publisher independently enforces the
closed-suite guard before final R2 or canonical database mutation. Ad-hoc
diagnostics with no completed suite identity remain separate.

For diagnostics, supervision, final publication, and progressive artifacts
remain independent inputs. Progressive artifacts require supervision and final
publication for a paid run.
Final publication remains independently usable when supervision is disabled:
the workflow omits the live-run ID, and canonical verification does not require
a live link. A separate workspace-relative publication discovery context keeps
the pre-run directory baseline and expected trial count available without
creating live staging state.

A dry run does not call a provider, upload benchmark results to R2, or insert
canonical benchmark rows. When supervision is enabled, it may publish a
non-scored `run_kind=dry-run` live row and events.

The benchmark exit code and canonical publication exit code are recorded and
enforced separately. Final publication runs under an `always()` condition so a
failed or exception-heavy Harbor run can still be represented if it produced a
valid final run directory.

Both the live wrapper and final publisher run through `uv` with explicit
runtime dependencies for `boto3` and `psycopg[binary]`; runner-global Python
packages are not assumed.

## Local inspection

Run a zero-cost local wrapper:

```bash
python scripts/run_arm_live.py \
  --arm-id router-anthropic-sonnet \
  --phase phase3 \
  --mode canary \
  --dry-run-metadata \
  --no-database-events \
  --no-progressive-artifacts \
  -- ./scripts/run_arm.sh phase3-router router-anthropic-sonnet --mode canary --dry-run
```

Inspect local evidence:

```bash
tail -n 30 .run/live/*.ndjson
cat .run/live/latest.json
```

Inspect final publication state:

```bash
cat .run/publish/*.json
```

Run the dashboard locally:

```bash
cd apps/dashboard
npm run dev
```

Open `/runs/live`. Shared Supabase state is the normal source. The page queries
at most 20 runs, 80 events, 200 trials, and 300 artifacts per selection. It
marks an active row stale after 90 seconds without a heartbeat. The optional
`DASHBOARD_LIVE_LOCAL_FALLBACK=true` path is labeled development-only.

## Performance and recovery

- Output, database, and scanner queues are bounded.
- Local NDJSON is written before shared publication.
- Database events are flushed in batches, not one transaction per output line.
- All output remains in local NDJSON. Shared process-output publication keeps
  the first 20 chunks and then samples every fifth chunk by default.
- Postgres retains only the newest 500 sampled process-output rows per live run;
  lifecycle, heartbeat, trial, artifact, and warning events are not sampled.
- Heartbeats default to 25 seconds and database flushes to 7.5 seconds.
- Artifact scanning defaults to 10 seconds with a 15-second stability window.
- Growing transcripts are not repeatedly uploaded.
- Progressive object keys include the artifact checksum, so changed files never
  overwrite objects referenced by an earlier checksum.
- Progressive reuse and final completion require matching remote checksum,
  metadata size, and content length; a database URI alone is not proof.
- Final canonical object keys include the artifact SHA-256; retries can reuse an
  exact object but cannot overwrite conflicting content.
- Retries use bounded exponential backoff.
- Failed database batches remain in a local spool for reconciliation.
- Final publication replays recoverable database spool batches before verification.
- Final canonical publication catches stable artifacts missed progressively.
- Publication failures do not rewrite the benchmark result or return code.
- Ordinary live upserts and event replay cannot reopen terminal publication
  state. An intentional publisher retry alone can transition
  `failed -> publishing -> verifying -> completed`; `completed` is immutable.
- `ineligible` is also terminal. Delayed live rows cannot replace its
  diagnostic message, canonical link, or publication fingerprint, and the
  ordinary failed-publication retry path cannot reopen it.
- Observed cost and token totals are monotonic. Stale rows cannot reduce them or
  replace terminal finish time, benchmark status, return code, failed
  publication message, or canonical link.
- Final live-trial evidence is ordered by `finished_at`: older or equal replay
  cannot replace terminal result fields, while a genuinely newer final result
  may do so. Trial timestamps, counters, cost, identity, and stability merge
  monotonically.
- Live artifact state advances from `observed` to `stable` to `uploaded`.
  Uploaded state and timestamps cannot regress, and conflicting non-null R2
  URIs for the same content identity fail the batch for local spool recovery.
- Duplicate live events do not update parent counters, heartbeats, elapsed
  time, or messages. Newly inserted event effects are monotonic.
- `.run`, live/publish directories, context, NDJSON, state, manifest, log, and
  spool paths are constrained to the supplied workspace and reject symlinked
  parents in workflow execution. The standalone
  `ingest_phase3_run_metadata.py` command remains a separate operator tool and
  may write an explicitly requested manifest outside the workspace.

GitHub artifacts retain redacted live NDJSON, `latest.json`, local database
spools, final manifests, and publication logs for diagnosis. Context and
manifest paths are workspace-relative; only a workspace fingerprint is shared.

## Rollback-only PostgreSQL integration

Before migration `009` is permanently applied, run the reviewed integration
harness only with its mandatory rollback acknowledgement:

```bash
uv run --with 'psycopg[binary]' \
  python scripts/verify_live_supervision_postgres.py --rollback-only
```

The command reads `SUPABASE_DB_URL` without printing it, refuses to run if any
live table already exists permanently, executes migration `009` and synthetic
application publication inside a transaction, suppresses the successful commit,
and rolls back. It separately forces the production verification-failure
rollback. A second connection must observe no live tables and zero synthetic
canonical or live rows after both paths. Output is limited to the migration
hash, pass/fail checks, and zero-persistence counts. It does not call R2 or a
provider. This real PostgreSQL test is still required because offline adapter
tests cannot prove PostgreSQL view visibility or transactional DDL semantics.
Failures report only a stable stage, exception type, SQLSTATE when available,
and any zero-persistence counts already observed; exception text, connection
details, SQL, and parameters are omitted.

## Deployment sequence

1. Review migration `009` and run the rollback-only PostgreSQL integration.
2. Run the permanent migration utility with `--check-only` and review its safe
   JSON result.
3. Apply migration `009` with the pinned hash and retain the ignored local
   application evidence.
4. Run the remote database doctor.
5. Confirm all six runners retain the phase-neutral labels.
6. Confirm workflow configs and required GitHub secret names.
7. Start the local dashboard and verify `/runs/live` can query the empty schema.
8. Dispatch one zero-cost dry run pinned to `cc-bench-slot-4`.
9. Verify the non-scored live row, event tail, heartbeat, and GitHub artifacts.
10. Verify no canonical benchmark row or benchmark-result R2 upload was created.
11. Keep completed Phase 3 suites closed except for an explicitly approved
   repair publication.
