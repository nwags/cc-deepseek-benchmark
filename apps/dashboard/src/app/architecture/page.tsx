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
    title: "Claude Code agent harness",
    detail: "Claude Code remains the fixed agent harness that receives the task and performs observable work in the task environment."
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
    detail: "After agent execution, task-specific held-out verifier tests inspect the resulting workspace and determine correctness."
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
    detail: "Final Harbor output supplies the run result and complete trial evidence considered for canonical publication."
  },
  {
    title: "Publication discovery, eligibility, and path-safety checks",
    detail: "The publisher requires one unambiguous current-job run directory, workspace-bounded paths, structural completeness, and internally consistent final counters."
  },
  {
    title: "scripts/publish_phase3_run.py",
    detail: "This is the workflow final publisher that coordinates the current canonical publication path after benchmark execution."
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
      description="Benchmark execution and scoring, optional live observation, final canonical publication, and dashboard read paths are separate but related flows."
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
        and Harbor records the raw reward and result evidence.
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

      <FlowPanel
        title="3. Final canonical publication after execution"
        description="A distinct after-execution path validates complete Harbor output before any canonical mutation."
        items={canonicalPublicationFlow}
        variant="artifact"
      />

      <section className="quality-context-panel">
        <p>
          <strong>Publication eligibility:</strong> Complete error-bearing runs may be publishable when structurally complete;
          interrupted, partial, ambiguous, or inconsistent runs remain live-only.
        </p>
        <p>
          R2 upload and remote object verification occur before canonical database commit. Canonical database publication
          and transaction/rollback verification use one transaction and roll back on failed verification.
        </p>
        <p>
          Supabase stores canonical run, trial, and artifact metadata and relationships. Cloudflare R2 stores immutable,
          content-addressed evidence bytes. Publication failures do not rewrite the Harbor benchmark result or benchmark exit code.
        </p>
        <p>
          Final publication without live supervision is supported; the live path is not mandatory.{" "}<Link href="/runs">Open canonical Runs →</Link>
        </p>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>4. Dashboard storage and read paths</h2>
            <p>Dashboard pages declare their evidence source; not every page reads from one common store.</p>
          </div>
          <Link href="/glossary">Glossary →</Link>
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
        <div className="concept-grid">
          <article>
            <h3><span className="term-label">Benchmark run class <TermInfo term="Benchmark run class" /></span></h3>
            <p>User-facing interpretation of an execution, such as canary, smoke, full, ad-hoc, diagnostic, or dry-run where applicable.</p>
          </article>
          <article>
            <h3><span className="term-label">Result source/storage location <TermInfo term="Result source/storage location" /></span></h3>
            <p>Where result evidence originated or is retained across Harbor/local directories, Supabase, R2, or historical snapshots.</p>
          </article>
          <article>
            <h3><span className="term-label">R2 artifact <TermInfo term="R2 artifact" /></span></h3>
            <p>Evidence bytes stored in Cloudflare R2 rather than directly in Supabase.</p>
          </article>
          <article>
            <h3><span className="term-label">Recorded cost <TermInfo term="Recorded cost" /></span></h3>
            <p>Known captured cost. If rows are missing, treat it as a lower bound.</p>
          </article>
        </div>
      </section>
    </AppShell>
  );
}
