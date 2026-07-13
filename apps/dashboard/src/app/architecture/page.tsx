import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { TermInfo } from "../../components/TermInfo";

export const dynamic = "force-dynamic";

const executionFlow = [
  {
    title: "Sponsor questions",
    detail: "Benchmark questions define which models, providers, and tasks need to be compared."
  },
  {
    title: "Model-arm plan",
    detail: "The arm plan turns sponsor questions into concrete model routes and benchmark suites."
  },
  {
    title: "Arm configs",
    detail: "configs/arms/*.yaml defines each Claude Code backend route, model name, and provider path."
  },
  {
    title: "Run scripts / dispatch",
    detail: "Local commands or GitHub Actions dispatch canary, smoke, or full benchmark jobs."
  },
  {
    title: "Containerized benchmark environment",
    detail: "Harbor runs Terminal-Bench tasks while Claude Code remains the fixed agent harness."
  },
  {
    title: "LiteLLM router service",
    detail: "Claude Code sends Anthropic-compatible requests to LiteLLM, which routes them to provider APIs."
  },
  {
    title: "Provider backends",
    detail: "Anthropic, DeepSeek, Gemini, OpenAI, xAI, Moonshot/Kimi, DashScope/Qwen, and Z.AI/GLM return model responses."
  }
];

const evidenceFlow = [
  {
    title: "Result directories",
    detail: "Harbor writes artifacts under results/phase3/{canary,smoke,raw}/..."
  },
  {
    title: "Ingestion script",
    detail: "ingest_phase3_run_metadata.py normalizes run metadata, trial rows, costs, and artifact records."
  },
  {
    title: "Supabase metadata",
    detail: "Queryable tables and views store suites, arm runs, evals, trials, cost coverage, and artifact metadata."
  },
  {
    title: "Cloudflare R2 artifacts",
    detail: "Evidence files such as result JSON, logs, and trajectories are stored outside the database."
  },
  {
    title: "Dashboard",
    detail: "Users compare full suites, arm runs, evals, diagnostics, cost coverage, and evidence coverage."
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
  items: { title: string; detail: string }[];
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
              <div className="architecture-arrow">
                {variant === "request" ? "↔" : "↓"}
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
      description="Two complementary views: benchmark execution/routing, and evidence flow into the dashboard."
    >
      <FlowPanel
        title="Execution and routing architecture"
        description="Bidirectional request/response flow from benchmark planning through Claude Code, LiteLLM, and provider backends."
        items={executionFlow}
        variant="request"
      />

      <FlowPanel
        title="Evidence and dashboard architecture"
        description="One-way artifact and metadata flow from benchmark outputs into Supabase, R2, and the dashboard."
        items={evidenceFlow}
        variant="artifact"
      />

      <section className="panel">
        <div className="panel-heading">
          <h2>Important dashboard concepts</h2>
          <p>This is not a second architecture diagram; it explains terms that commonly cause confusion.</p>
        </div>
        <div className="concept-grid">
          <article>
            <h3><span className="term-label">Logical mode <TermInfo term="Logical mode" /></span></h3>
            <p>Sponsor-facing run type, such as canary, smoke, or full.</p>
          </article>
          <article>
            <h3><span className="term-label">Storage mode <TermInfo term="Storage mode" /></span></h3>
            <p>Physical results directory or legacy ingestion key, such as raw, smoke, or canary.</p>
          </article>
          <article>
            <h3><span className="term-label">R2 artifact <TermInfo term="R2 artifact" /></span></h3>
            <p>Evidence file stored in Cloudflare R2 rather than directly in Supabase.</p>
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
