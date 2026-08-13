import Link from "next/link";

import { AppShell } from "../../components/AppShell";

const liveRelations = [
  "benchmark.live_runs",
  "benchmark.live_run_events",
  "benchmark.live_trials",
  "benchmark.live_artifacts",
] as const;

const canonicalRelations = [
  "benchmark.benchmark_runs",
  "benchmark.benchmark_arms",
  "benchmark.benchmark_tasks",
  "benchmark.benchmark_trials",
  "benchmark.benchmark_artifacts",
  "benchmark.benchmark_eval_suites",
  "benchmark.benchmark_eval_suite_items",
  "benchmark.benchmark_arm_runs",
] as const;

const derivedRelationGroups = [
  {
    label: "Validity",
    relations: [
      "benchmark.benchmark_invalid_arm_runs",
      "benchmark.v_valid_arm_run_summary",
      "benchmark.v_valid_suite_arm_comparison",
      "benchmark.v_valid_eval_arm_comparison",
      "benchmark.v_valid_suite_arm_quality_summary",
    ],
  },
  {
    label: "Quality",
    relations: [
      "benchmark.v_trial_quality_flags",
      "benchmark.v_arm_run_quality_summary",
      "benchmark.v_arm_run_summary",
      "benchmark.v_arm_run_trials",
    ],
  },
  {
    label: "General dashboard",
    relations: [
      "benchmark.v_dashboard_runs",
      "benchmark.v_dashboard_arms",
      "benchmark.v_dashboard_tasks",
    ],
  },
  {
    label: "Cost",
    relations: [
      "benchmark.benchmark_trial_cost_coverage",
      "benchmark.v_trial_adjusted_cost_coverage",
      "benchmark.v_arm_outcome_cost_breakdown",
      "benchmark.v_suite_adjusted_cost_frontier",
    ],
  },
] as const;

function RelationList({ relations }: { relations: readonly string[] }) {
  return (
    <ul className="data-model-relation-names">
      {relations.map((relation) => <li key={relation}><code>{relation}</code></li>)}
    </ul>
  );
}

export default function DataModelPage() {
  return (
    <AppShell
      title="Data Model"
      description="A checked-in reference for live observation, canonical benchmark metadata, derived views, artifact bytes, reviewed snapshots, and dashboard consumers."
    >
      <section className="quality-context-panel data-model-orientation">
        <p>
          <strong>This is a documentation route, not a live schema inspector.</strong> It describes the repository&apos;s
          checked-in schema and audited dashboard read relationships without querying Supabase or R2.
        </p>
        <div className="data-model-cross-links">
          <Link href="/architecture">Architecture →</Link>
          <Link href="/glossary">Glossary →</Link>
        </div>
      </section>

      <section className="panel" aria-labelledby="data-model-reading-order">
        <div className="panel-heading">
          <div>
            <h2 id="data-model-reading-order">Model reading order</h2>
            <p>Each layer has a distinct authority; line style or color is never the only relationship cue.</p>
          </div>
        </div>
        <ol className="data-model-layer-index">
          <li><strong>A</strong><span>Live, non-canonical execution observations</span></li>
          <li><strong>B</strong><span>Canonical benchmark metadata and relationships</span></li>
          <li><strong>C</strong><span>Derived validity, quality, dashboard, and cost query layers</span></li>
          <li><strong>D</strong><span>Cloudflare R2 evidence bytes outside Postgres</span></li>
          <li><strong>E</strong><span>Checked-in reviewed and historical snapshots</span></li>
          <li><strong>F</strong><span>Dashboard consumers with declared populations and sources</span></li>
        </ol>
        <p className="data-model-source-reference">
          Checked-in diagram source: <code>docs/diagrams/DASHBOARD_DATA_MODEL_20260812.mmd</code>. The semantic HTML below
          is the accessible text equivalent and remains complete without rendering Mermaid.
        </p>
      </section>

      <section className="panel data-model-layer data-model-layer-live" aria-labelledby="data-model-live">
        <div className="panel-heading">
          <div>
            <p className="data-model-layer-label">Layer A · non-canonical</p>
            <h2 id="data-model-live">Live execution state</h2>
            <p>Mutable observations while a benchmark is running; they do not become benchmark truth until final publication succeeds.</p>
          </div>
          <Link href="/runs/live">Open Live Runs →</Link>
        </div>
        <div className="data-model-layer-body">
          <RelationList relations={liveRelations} />
          <div className="data-model-relationship-block">
            <h3>Direct database relationships</h3>
            <dl className="data-model-edges">
              <div><dt><code>live_run_events.live_run_id</code></dt><dd>references <code>live_runs.live_run_id</code></dd></div>
              <div><dt><code>live_trials.live_run_id</code></dt><dd>references <code>live_runs.live_run_id</code></dd></div>
              <div><dt><code>live_artifacts.live_run_id</code></dt><dd>references <code>live_runs.live_run_id</code></dd></div>
              <div className="data-model-edge-canonical"><dt><code>live_runs.canonical_arm_run_id</code></dt><dd>references <code>benchmark_arm_runs.id</code> — the only direct live-to-canonical foreign key</dd></div>
            </dl>
          </div>
        </div>
        <aside className="data-model-caution">
          <strong>Reconciliation is not a per-row foreign key.</strong> Live trial and artifact observations are reconciled
          during final publication using run identity, retained evidence, manifests, hashes, and paths. There is no direct
          per-trial or per-artifact canonical foreign key in the audited live schema.
        </aside>
      </section>

      <section className="panel data-model-layer" aria-labelledby="data-model-canonical">
        <div className="panel-heading">
          <div>
            <p className="data-model-layer-label">Layer B · canonical</p>
            <h2 id="data-model-canonical">Canonical benchmark metadata</h2>
            <p>Published run, arm, task, trial, artifact, suite, and arm-run identities and their principal foreign-key relationships.</p>
          </div>
          <Link href="/runs">Open Runs →</Link>
        </div>
        <div className="data-model-layer-body">
          <RelationList relations={canonicalRelations} />
          <div className="data-model-relationship-block">
            <h3>Principal canonical relationships</h3>
            <dl className="data-model-edges">
              <div><dt><code>benchmark_arm_runs.run_id</code></dt><dd>references <code>benchmark_runs.id</code></dd></div>
              <div><dt><code>benchmark_arm_runs.arm_id</code></dt><dd>references <code>benchmark_arms.arm_id</code></dd></div>
              <div><dt><code>benchmark_arm_runs.suite_id</code></dt><dd>references <code>benchmark_eval_suites.suite_id</code></dd></div>
              <div><dt><code>benchmark_trials.run_id</code></dt><dd>references <code>benchmark_runs.id</code></dd></div>
              <div><dt><code>benchmark_trials.arm_id</code></dt><dd>references <code>benchmark_arms.arm_id</code></dd></div>
              <div><dt><code>benchmark_trials.task_id</code></dt><dd>references <code>benchmark_tasks.task_id</code></dd></div>
              <div><dt><code>benchmark_trials.arm_run_id</code></dt><dd>references <code>benchmark_arm_runs.id</code></dd></div>
              <div><dt><code>benchmark_artifacts.run_id</code></dt><dd>references <code>benchmark_runs.id</code></dd></div>
              <div><dt><code>benchmark_artifacts.trial_id</code></dt><dd>references <code>benchmark_trials.id</code></dd></div>
            </dl>
          </div>
        </div>
      </section>

      <section className="panel data-model-layer" aria-labelledby="data-model-derived">
        <div className="panel-heading">
          <div>
            <p className="data-model-layer-label">Layer C · query/derived</p>
            <h2 id="data-model-derived">Validity, quality, dashboard, and cost views</h2>
            <p>Representative query families over canonical metadata—not a second source of benchmark truth.</p>
          </div>
        </div>
        <div className="data-model-derived-grid">
          {derivedRelationGroups.map((group) => (
            <section key={group.label} aria-labelledby={`derived-${group.label.toLowerCase().replaceAll(" ", "-")}`}>
              <h3 id={`derived-${group.label.toLowerCase().replaceAll(" ", "-")}`}>{group.label}</h3>
              <RelationList relations={group.relations} />
            </section>
          ))}
        </div>
        <p className="data-model-layer-note">Individual dashboard pages consume only the relations appropriate to their declared population and evidence contract.</p>
      </section>

      <section className="panel data-model-layer data-model-layer-storage" aria-labelledby="data-model-r2">
        <div className="panel-heading">
          <div>
            <p className="data-model-layer-label">Layer D · external byte storage</p>
            <h2 id="data-model-r2">Cloudflare R2 evidence bytes</h2>
            <p>R2 sits outside the Supabase/Postgres entity boundary; its relationships are storage references, not database foreign keys.</p>
          </div>
          <Link href="/artifacts">Open Artifacts →</Link>
        </div>
        <div className="data-model-storage-layout">
          <div>
            <h3>Metadata references</h3>
            <dl className="data-model-edges">
              <div><dt><code>live_artifacts.r2_uri</code></dt><dd>references an external live artifact object location</dd></div>
              <div><dt><code>benchmark_artifacts.r2_uri</code></dt><dd>references an external canonical artifact object location</dd></div>
            </dl>
          </div>
          <aside className="data-model-caution">
            <strong>Reference is not retrieval proof.</strong> An indexed row or <code>r2_uri</code> alone does not prove
            that bytes were retrieved, complete, or verified against recorded hash and size. Supabase/Postgres stores
            metadata and relationships; R2 stores artifact bytes.
          </aside>
        </div>
      </section>

      <section className="panel data-model-layer" aria-labelledby="data-model-reviewed">
        <div className="panel-heading">
          <div>
            <p className="data-model-layer-label">Layer E · checked-in provenance</p>
            <h2 id="data-model-reviewed">Reviewed and historical file-backed snapshots</h2>
            <p>Frozen provenance layers remain separate from operational database rows and are not silently refreshed from newer stored evidence.</p>
          </div>
          <Link href="/cross-phase">Open Cross-phase →</Link>
        </div>
        <ul className="data-model-snapshot-list">
          <li><strong>F1 reviewed Phase 3 comparison snapshot</strong><span>Quantitative reviewed comparison facts and core/extended membership.</span></li>
          <li><strong>G1 reviewed run-selection snapshot</strong><span>Frozen selected-run identity and evidence links for the reviewed arms.</span></li>
          <li><strong>Historical Cross-phase/reporting inputs</strong><span>Retained Phase 1/2 and historical Phase 3 comparison provenance.</span></li>
          <li><strong>Comprehensive evidence-review snapshots</strong><span>Manifest-bound reviewed evidence used where that page declares the snapshot source.</span></li>
        </ul>
      </section>

      <section className="panel data-model-layer" aria-labelledby="data-model-consumers">
        <div className="panel-heading">
          <div>
            <p className="data-model-layer-label">Layer F · consumers</p>
            <h2 id="data-model-consumers">Representative dashboard consumers</h2>
            <p>Routes disclose their source and population; this list shows representative consumers rather than claiming every page reads every relation.</p>
          </div>
        </div>
        <div className="data-model-consumer-grid">
          <section>
            <h3>Live</h3>
            <p><Link href="/runs/live">/runs/live</Link></p>
            <p><code>/live-artifacts/[artifactId]</code></p>
          </section>
          <section>
            <h3>Canonical / operational</h3>
            <p><Link href="/runs">/runs</Link> · <Link href="/artifacts">/artifacts</Link> · <code>/trials/[trialId]</code></p>
            <p><Link href="/arms">/arms</Link> · <Link href="/eval-suites">/eval-suites</Link> · <Link href="/evals">/evals</Link> · <Link href="/trial-quality">/trial-quality</Link></p>
          </section>
          <section>
            <h3>Reviewed / file-backed</h3>
            <p><Link href="/">Overview reviewed comparison and chart</Link></p>
            <p><Link href="/cross-phase">/cross-phase</Link> · <Link href="/cost-coverage">/cost-coverage</Link> · <Link href="/comprehensive-review">/comprehensive-review</Link></p>
          </section>
        </div>
        <p className="data-model-layer-note">
          Some pages deliberately combine clearly separated sources. Overview, for example, presents reviewed snapshot facts and chart data alongside a distinctly labeled dynamic operational inventory.
        </p>
      </section>
    </AppShell>
  );
}
