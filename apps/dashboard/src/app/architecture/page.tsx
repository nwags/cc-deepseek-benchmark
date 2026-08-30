import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { TermInfo } from "../../components/TermInfo";

export const dynamic = "force-dynamic";

type FlowItem = {
  title: string;
  detail: string;
};

const executionAndScoringFlow: FlowItem[] = [
  {
    title: "Benchmark questions and comparison design",
    detail: "Benchmark questions define the models, routes, task population, and comparisons that the study is intended to evaluate."
  },
  {
    title: "Benchmark design and arm selection",
    detail: "Checked-in arm configuration and suite/task configuration select the model route and benchmark workload without exposing secret values."
  },
  {
    title: "Local or GitHub Actions dispatch",
    detail: "The same config-driven benchmark can be dispatched locally or through the reviewed GitHub Actions workflow."
  },
  {
    title: "Selected execution host / self-hosted runner",
    detail: "Local dispatch executes in the selected local workspace. GitHub Actions uses a selected self-hosted runner workspace on an OVH VPS, where the dispatched benchmark executes. This describes execution topology, not fleet status, and makes no runner count, availability, capacity, or queue-depth claim."
  },
  {
    title: "Harbor task container",
    detail: "Harbor orchestrates the isolated Terminal-Bench task environment and its result directory."
  },
  {
    title: "Configured agent harness",
    detail: "For Phases 1–3, the Claude Code agent harness is the fixed principal harness. Harness identity is already canonical arm metadata; a future Phase 4 may vary this dimension only after a compatibility and methodology review."
  },
  {
    title: "LiteLLM route when applicable",
    detail: "Only routed arms pass model API traffic through LiteLLM; direct arms do not acquire this stage implicitly."
  },
  {
    title: "Provider/model backend",
    detail: "The selected backend returns model responses to the harness path so agent execution can continue."
  },
  {
    title: "Held-out verifier/test execution",
    detail: "The task-specific verifier and tests are not the task instructions the agent is solving from. After the agent finishes, they inspect the resulting workspace and determine benchmark correctness and reward. This keeps dashboard diagnosis as interpretation rather than scoring authority without claiming more secrecy or isolation than the retained benchmark contract supports."
  },
  {
    title: "Raw reward and result creation",
    detail: "Harbor records the raw verifier reward and structured result evidence without replacing that evidence with a derived dashboard interpretation."
  }
];

const liveObservationFlow: FlowItem[] = [
  {
    title: "Harbor result directories and observable process activity",
    detail: "The optional observer watches lifecycle state, process output, heartbeats, completed-trial evidence, and stable artifacts while Harbor continues running."
  },
  {
    title: "scripts/run_arm_live.py",
    detail: "The live wrapper supervises the benchmark command without becoming the benchmark scorer or changing Harbor results."
  },
  {
    title: "Local redacted NDJSON and heartbeats",
    detail: "Observable events are redacted and retained locally before optional shared publication."
  },
  {
    title: "Supabase live metadata/state",
    detail: "When shared database publication is enabled, partial rows may be written to benchmark.live_runs, benchmark.live_run_events, benchmark.live_trials, and benchmark.live_artifacts; local redacted NDJSON remains available independently."
  },
  {
    title: "Cloudflare R2 artifact bytes",
    detail: "Stable allowlisted artifact bytes may be uploaded progressively under execution-isolated, content-addressed object keys."
  },
  {
    title: "Live Runs dashboard read path",
    detail: "Server-side dashboard code reads shared live metadata from Supabase and stable evidence bytes from R2."
  }
];

const canonicalPublicationFlow: FlowItem[] = [
  {
    title: "Harbor final result directory and canonical trial artifacts",
    detail: "The final Harbor result directory supplies structured result/reward/status evidence plus the available trial artifacts considered for canonical publication; optional artifacts are not assumed to exist for every trial."
  },
  {
    title: "Publication discovery, eligibility, and path-safety checks",
    detail: "The publisher requires one unambiguous current-job run directory, workspace-bounded paths, structural completeness, and internally consistent final counters."
  },
  {
    title: "scripts/publish_phase3_run.py",
    detail: "This is the workflow's final canonical publisher. It runs after benchmark execution and coordinates eligible-result discovery, manifest-backed verification, R2 reconciliation, transactional canonical metadata publication, final relationship checks, and the applicable live-to-canonical arm-run link."
  },
  {
    title: "scripts/ingest_phase3_run_metadata.py functionality",
    detail: "The publisher reuses its manifest construction and ingestion helpers; the script also remains a separate historical/operator ingestion tool, not the sole current workflow publication path."
  },
  {
    title: "Progressive-artifact reconciliation and missing uploads",
    detail: "Progressive artifacts are reconciled when present. Whether or not live supervision ran, the final publisher uploads any missing canonical artifacts before R2 verification and canonical database publication."
  },
  {
    title: "R2 checksum/size/object verification",
    detail: "Local hashes and sizes are checked, then uploaded or reused R2 objects are verified before canonical database publication begins."
  },
  {
    title: "Transactional canonical Supabase publication",
    detail: "Canonical metadata and relationships are inserted and verified in one database transaction; failed verification rolls back the canonical attempt."
  },
  {
    title: "Dashboard verification and live-to-canonical linking",
    detail: "Final counts, classifications, artifact relationships, and any applicable live-to-canonical link are verified before completion."
  }
];


const evidenceQualificationFlow: FlowItem[] = [
  {
    title: "Canonical arm run",
    detail: "A completed canonical arm run is the execution identity that reconciliations and promotion review bind to. Normalized provider evidence may also attach to that arm run or an exact trial when allocation supports that precision; broader provider evidence can remain unallocated until reconciliation."
  },
  {
    title: "Provider evidence collection and ingestion",
    detail: "Provider usage, billing/cost, pricing, and model-identity evidence are retained as independent provenance rather than overwriting Harbor or harness telemetry."
  },
  {
    title: "Normalized provider usage and cost evidence",
    detail: "Provider-specific observations are normalized while preserving allocation scope, completeness, source identity, and limitations."
  },
  {
    title: "Usage and cost reconciliations",
    detail: "Independent reconciliation records select the current usage/model-identity authority and economic authority for the exact arm run."
  },
  {
    title: "Guarded promotion review",
    detail: "scripts/review_evidence_promotion.py records a reviewed Canary→Smoke or Smoke→Full decision using exact reconciliation UUIDs and a reviewed-state fingerprint."
  },
  {
    title: "Fail-closed promotion view",
    detail: "benchmark.v_evidence_promotion_gate derives whether the stored review and its exact current evidence chain effectively authorize advancement."
  },
  {
    title: "Read-only Planner",
    detail: "The Planner reads current promotion evidence, displays the evidence chain, and withholds Smoke/Full commands when effective advancement is absent. It does not itself write gates or dispatch work."
  }
];

function FlowPanel({
  title,
  description,
  items,
  variant
}: {
  title: string;
  description: string;
  items: FlowItem[];
  variant: "request" | "artifact";
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <Link href="/glossary">Glossary →</Link>
      </div>

      <div className={`architecture-flow architecture-flow-${variant}`}>
        {items.map((node, index) => (
          <div className="architecture-step" key={node.title}>
            <div className="architecture-node">
              <span className="architecture-index">{index + 1}</span>
              <div>
                <h3>{node.title}</h3>
                <p>{node.detail}</p>
              </div>
            </div>
            {index < items.length - 1 ? (
              <div className="architecture-arrow" aria-hidden="true">
                {variant === "request" ? "→" : "↓"}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

export default function ArchitecturePage() {
  return (
    <AppShell
      title="Architecture"
      description="Benchmark execution and scoring, optional live observation, canonical publication, provider-evidence qualification, promotion review, and dashboard read paths are separate but related flows."
    >
      <section className="quality-context-panel">
        <strong>Separate paths, separate responsibilities.</strong> Execution and verifier scoring create the benchmark result.
        Live supervision is optional and observes an in-progress execution. Final canonical publication runs after execution and does not depend on live supervision.
      </section>

      <FlowPanel
        title="1. Benchmark execution and scoring"
        description="Forward execution/scoring progression from benchmark design to Harbor's retained verifier result."
        items={executionAndScoringFlow}
        variant="request"
      />

      <section className="quality-context-panel">
        <strong>No LLM judge determines the benchmark reward.</strong> The held-out verifier/tests determine correctness,
        and Harbor records the raw reward and result evidence. The dashboard can explain execution evidence, but it does not rescore the trial.
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Concrete retained Harbor evidence</h2>
            <p>Representative artifacts explain what was scored and what the agent did; availability varies by trial.</p>
          </div>
          <div className="panel-heading-actions">
            <Link href="/artifacts">Open Artifacts →</Link>
            <Link href="/trial-quality">Open Trial Quality →</Link>
          </div>
        </div>
        <dl className="architecture-evidence-list">
          <div><dt><code>result</code></dt><dd>Harbor&apos;s structured result, reward, and status evidence.</dd></div>
          <div><dt><code>agent_transcript</code></dt><dd>The observable agent interaction and task-execution record; private model reasoning is not exposed.</dd></div>
          <div><dt><code>verifier_stdout</code></dt><dd>Human-readable output from the task-specific verifier or tests.</dd></div>
          <div><dt><code>trajectory</code></dt><dd>Structured evidence of observable agent and tool behavior when retained.</dd></div>
          <div><dt><code>verifier_ctrf</code></dt><dd>Structured test and assertion confirmation when produced.</dd></div>
          <div><dt><code>verifier_reward</code></dt><dd>Raw confirmation of the verifier reward.</dd></div>
        </dl>
        <p className="architecture-evidence-note">
          Additional <code>config</code>, <code>log</code>, or <code>exception</code> evidence may be retained when present.
          No trial is represented as having every optional artifact.
        </p>
      </section>

      <FlowPanel
        title="2. Optional live observation during execution"
        description="An optional, failure-isolated observation path alongside Harbor—not a prerequisite for benchmark execution or final publication."
        items={liveObservationFlow}
        variant="artifact"
      />

      <section className="quality-context-panel">
        <p>
          <strong>Live supervision is optional.</strong> It observes process output, lifecycle state, heartbeats,
          completed-trial evidence, and stable artifacts. Observable process output is not private model reasoning.
        </p>
        <p>
          Database or R2 publication failure does not stop Harbor. Live rows are partial and can change before canonical publication.
          This is execution observation, not an independent fleet-capacity monitor.
        </p>
        <p>
          The dashboard reads shared Supabase/R2 services and does not connect directly to the VPS, Harbor, Docker,
          the Docker socket, or SSH. Supabase stores live metadata and row state; R2 stores artifact bytes.{" "}<Link href="/runs/live">Open Live Runs →</Link>
        </p>
      </section>

      <section className="panel architecture-switch-panel">
        <div className="panel-heading">
          <div>
            <h2>Live and publication controls</h2>
            <p>Current workflow defaults are safety settings; they are separate from architectural capability.</p>
          </div>
        </div>
        <div className="architecture-switch-layout">
          <dl className="architecture-switch-behavior">
            <div>
              <dt><code>supervise_live=true</code></dt>
              <dd>
                Wraps the benchmark command with <code>scripts/run_arm_live.py</code> so observable execution metadata,
                events, heartbeats, completed-trial evidence, and stable artifacts can be captured. Shared live database
                publication still depends on configured credentials. The wrapper neither scores nor changes Harbor&apos;s result.
              </dd>
            </div>
            <div>
              <dt><code>supervise_live=false</code></dt>
              <dd>
                Runs the benchmark without <code>scripts/run_arm_live.py</code> supervision. A separately requested final
                canonical publication may still run after execution.
              </dd>
            </div>
            <div>
              <dt><code>progressive_artifacts=true</code></dt>
              <dd>
                For a paid run, requires both <code>supervise_live=true</code> and <code>publish_results=true</code>.
                Stable completed-trial artifacts may then be uploaded while the benchmark runs.
              </dd>
            </div>
            <div>
              <dt><code>publish_results=true</code></dt>
              <dd>
                Runs the workflow&apos;s after-execution final publication step with <code>scripts/publish_phase3_run.py</code>.
                This can run whether or not live supervision was enabled.
              </dd>
            </div>
          </dl>
          <aside className="architecture-config-defaults" aria-label="Current workflow dispatch defaults">
            <h3>Current workflow_dispatch defaults</h3>
            <dl>
              <div><dt><code>supervise_live</code></dt><dd><strong>true</strong></dd></div>
              <div><dt><code>publish_results</code></dt><dd><strong>false</strong> · Phase 3 closeout safety default</dd></div>
              <div><dt><code>progressive_artifacts</code></dt><dd><strong>false</strong></dd></div>
            </dl>
            <p>The <code>publish_results=false</code> default does not mean canonical publication is globally disabled.</p>
          </aside>
        </div>
      </section>

      <FlowPanel
        title="3. Final canonical publication after execution"
        description="A distinct after-execution path validates the complete Harbor result directory and retained trial evidence before any canonical mutation."
        items={canonicalPublicationFlow}
        variant="artifact"
      />

      <section className="quality-context-panel">
        <p className="architecture-publisher-lead">
          <strong><code>scripts/publish_phase3_run.py</code> is the workflow final canonical publisher.</strong>
        </p>
        <p>
          <strong>Publication eligibility:</strong> Complete error-bearing runs may be publishable when structurally complete;
          interrupted, partial, ambiguous, or inconsistent runs remain live-only.
        </p>
        <p>
          It discovers the eligible final Harbor result directory, applies eligibility and path-safety checks, builds or reuses
          ingestion-manifest functionality, and reconciles live database spool and progressive-artifact evidence when applicable.
          When object upload is requested, it uploads missing canonical R2 objects and verifies checksum, size, and object integrity
          before canonical database publication.
        </p>
        <p>
          R2 upload and remote object verification occur before canonical database commit. Canonical database publication
          and transaction/rollback verification use one transaction and roll back on failed verification. Final counts and
          relationships are verified, and the applicable live run is linked to its canonical arm run.
        </p>
        <p>
          Supabase stores canonical run, trial, and artifact metadata and relationships. Cloudflare R2 stores immutable,
          content-addressed evidence bytes. Publication failures do not rewrite the Harbor benchmark result or benchmark exit code.
        </p>
        <p>
          Final publication without live supervision is supported; the live path is not mandatory.{" "}<Link href="/runs">Open canonical Runs →</Link>
        </p>
      </section>

      <FlowPanel
        title="4. Provider evidence, reconciliation, and promotion review"
        description="A post-execution evidence-authority path keeps provider observations, reviewed reconciliation, and benchmark-advancement decisions distinct from raw scoring."
        items={evidenceQualificationFlow}
        variant="artifact"
      />

      <section className="quality-context-panel">
        <p>
          <strong>Future-phase boundary:</strong> Phase 4 may vary the configured agent harness, but it is not
          active. Before its first paid Canary, promotion authorization must be reviewed for experiment/suite scoping
          so an earlier gate cannot authorize a new experiment based only on arm and target mode.
        </p>
        <p>
          Phase 5 remains after Phase 4. Its planned procedure dimension introduces retained planning evidence
          and separable planning/execution usage, cost, latency, and failure attribution; those are extension
          requirements, not current canonical schema claims.
        </p>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>5. Dashboard storage and read paths</h2>
            <p>Dashboard pages declare their evidence source; not every page reads from one common store.</p>
          </div>
          <div className="panel-heading-actions">
            <Link href="/data-model">Data Model →</Link>
            <Link href="/glossary">Glossary →</Link>
          </div>
        </div>
        <div className="concept-grid">
          <article>
            <h3>Supabase metadata and state</h3>
            <p>
              Queryable live and canonical metadata, counters, relationships, validity, cost, and artifact records.{" "}<Link href="/runs/live">Live Runs</Link> · <Link href="/runs">Runs</Link>
            </p>
          </article>
          <article>
            <h3>Cloudflare R2 evidence bytes</h3>
            <p>
              Actual result JSON, logs, transcripts, trajectories, verifier outputs, and related artifact bytes.{" "}<Link href="/artifacts">Artifacts</Link>
            </p>
          </article>
          <article>
            <h3>Dashboard server-side read path</h3>
            <p>
              Server-side dashboard code reads Supabase metadata/state and fetches bounded artifact previews or immutable downloads from R2.
            </p>
          </article>
          <article>
            <h3>Historical file-backed review snapshots</h3>
            <p>
              Reviewed snapshots remain separate from current Supabase-backed views and retain their frozen corpus and provenance.{" "}<Link href="/cross-phase">Cross-phase</Link>
            </p>
          </article>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Public dashboard terminology</h2>
          <p>Public labels describe intent; internal compatibility fields remain documented in the glossary.</p>
        </div>
        <div className="concept-grid architecture-terminology-grid">
          <article>
            <h3>
              <span className="term-label architecture-terminology-label">
                <span className="architecture-terminology-text">Benchmark run class</span>
                <TermInfo term="Benchmark run class" />
              </span>
            </h3>
            <p>User-facing interpretation of an execution, such as canary, smoke, full, ad-hoc, diagnostic, or dry-run where applicable.</p>
          </article>
          <article>
            <h3>
              <span className="term-label architecture-terminology-label">
                <span className="architecture-terminology-text">Result source/storage location</span>
                <TermInfo term="Result source/storage location" />
              </span>
            </h3>
            <p>Where result evidence originated or is retained across Harbor/local directories, Supabase, R2, or historical snapshots.</p>
          </article>
          <article>
            <h3>
              <span className="term-label architecture-terminology-label">
                <span className="architecture-terminology-text">R2 artifact</span>
                <TermInfo term="R2 artifact" />
              </span>
            </h3>
            <p>Evidence bytes stored in Cloudflare R2 rather than directly in Supabase.</p>
          </article>
          <article>
            <h3>
              <span className="term-label architecture-terminology-label">
                <span className="architecture-terminology-text">Recorded cost</span>
                <TermInfo term="Recorded cost" />
              </span>
            </h3>
            <p>Known captured cost. If rows are missing, treat it as a lower bound.</p>
          </article>
        </div>
      </section>
    </AppShell>
  );
}
