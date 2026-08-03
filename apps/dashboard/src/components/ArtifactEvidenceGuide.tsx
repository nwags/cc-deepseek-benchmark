import {
  artifactTypeDefinitions,
  canonicalRunArtifactTypes,
  canonicalTrialArtifactTypes
} from "../lib/artifact-types";

const lifecycle = [
  ["config", "The reproducibility snapshot"],
  ["trial.log", "Environment and agent setup"],
  ["claude-code.txt", "Visible Claude Code execution"],
  ["trajectory.json", "Structured behavior record"],
  ["exception.txt", "Optional exception branch"],
  ["test-stdout.txt", "Verifier explanation"],
  ["ctrf.json", "Structured test results"],
  ["reward.txt", "Raw score"],
  ["result.json", "Final Harbor record"]
] as const;

const readingOrder = [
  "result.json",
  "claude-code.txt",
  "verifier/test-stdout.txt",
  "trajectory.json",
  "config.json",
  "trial.log",
  "exception.txt when present",
  "ctrf.json and reward.txt for confirmation",
  "router evidence when retained"
];

const matrix = [
  ["Substantive success", "Reward passes; visible assistant or tool activity; verifier confirms the requested state."],
  ["Substantive failure", "Visible work occurred, but reward/verifier records failure."],
  ["Provider-policy refusal", "Explicit refusal marker or category. A refusal can occur before or after prior activity; policy disposition remains independent."],
  ["Empty completion", "Empty final result, no visible assistant content, and no tools."],
  ["Empty completion after long API-path wait", "Complete activity evidence is empty and retained end-to-end API-path timing is long; router/provider-only latency is not inferred."],
  ["Thinking-only empty completion", "Thinking-event metadata exists, but no visible content or tools. Thinking content is never read or shown."],
  ["Synthetic-retry empty completion", "Claude Code requests a visible response after an empty completion; the retry is also empty."],
  ["Timeout after meaningful activity", "A timeout follows visible messages or tool calls."],
  ["Unclassified exception", "An exception exists, but retained markers do not justify policy, timeout, setup, or transport attribution."],
  ["Telemetry mismatch", "Transcript usage exists but database/result telemetry is missing or zero."],
  ["Verifier/environment failure", "Verifier or setup evidence, rather than the model solution, explains failure."],
  ["Questionable success", "Reward passes despite no recorded visible activity; requires manual review."],
  ["Unknown", "Required evidence is unavailable, malformed, or too truncated for a supported conclusion."]
] as const;

export function ArtifactEvidenceGuide({ compact = false }: { compact?: boolean }) {
  return (
    <section className={`panel evidence-guide ${compact ? "evidence-guide-compact" : ""}`}>
      <div className="panel-heading">
        <div>
          <h2>{compact ? "How to investigate this trial" : "Artifact lifecycle and investigation guide"}</h2>
          <p>Read Harbor outcome, Claude Code activity, provider/router context, and verifier evidence as separate layers.</p>
        </div>
      </div>

      <details open={!compact}>
        <summary>Evidence levels and lifecycle</summary>
        <div className="evidence-guide-body">
          <div className="evidence-level-grid">
            <article>
              <h3>Run-root evidence</h3>
              <p>Shared job-level files live above individual task attempts. The common set is <span className="mono">{canonicalRunArtifactTypes.join(", ")}</span>.</p>
            </article>
            <article>
              <h3>Trial evidence</h3>
              <p>One task attempt normally has eight canonical artifacts: <span className="mono">{canonicalTrialArtifactTypes.join(", ")}</span>. An explicit exception artifact makes the expected set nine.</p>
            </article>
          </div>

          <div className="evidence-lifecycle-wrap">
            <ol className="evidence-lifecycle" aria-label="Trial artifact generation lifecycle">
              {lifecycle.map(([name, description], index) => (
                <li key={name} className={name === "exception.txt" ? "evidence-optional" : ""}>
                  <span className="mono">{name}</span>
                  <small>{description}</small>
                  {index < lifecycle.length - 1 ? <span className="evidence-arrow" aria-hidden="true">↓</span> : null}
                </li>
              ))}
            </ol>
            <aside className="router-lane">
              <strong>Separate observability lane</strong>
              <span>Claude Code ↔ router ↔ provider</span>
              <p>Router logs may be retained, unavailable/not retained, or unknown. They are not part of canonical 8/8 completeness.</p>
            </aside>
          </div>
        </div>
      </details>

      <details open={compact}>
        <summary>Recommended reading order</summary>
        <div className="evidence-guide-body">
          <ol className="reading-order">
            {readingOrder.map((item) => <li key={item}>{item}</li>)}
          </ol>
        </div>
      </details>

      {!compact ? (
        <>
          <details>
            <summary>Evidence triangles</summary>
            <div className="evidence-triangles">
              <article><h3>Outcome</h3><p>result → reward → verifier</p></article>
              <article><h3>Activity</h3><p>transcript → trajectory → verifier result</p></article>
              <article><h3>Infrastructure</h3><p>config → trial log → exception/router evidence</p></article>
            </div>
          </details>

          <details>
            <summary>Fast classification matrix</summary>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Derived classification</th><th>Conservative evidence signature</th></tr></thead>
                <tbody>{matrix.map(([name, signature]) => <tr key={name}><th>{name}</th><td>{signature}</td></tr>)}</tbody>
              </table>
            </div>
          </details>

          <details>
            <summary>Calibrated examples and telemetry semantics</summary>
            <div className="evidence-guide-body">
              <p><strong>Kimi near miss:</strong> visible assistant and tool activity produced the requested source, but verifier evidence found extra generated output files. That is a substantive raw failure with <span className="mono">extraneous_output_artifacts</span>, not an empty completion.</p>
              <p><strong>Missing, zero, and contradictory are different:</strong> a null database field means not recorded; explicit zero is recorded zero; nonzero transcript usage paired with database zero is contradictory telemetry. Cache-read and cache-creation input are included when reconciling total input.</p>
              <p><strong>Timing boundary:</strong> transcript duration supports an API-path duration only. Without retained router evidence, the dashboard does not assign that wait to the provider alone.</p>
              <p><strong>R2 boundary:</strong> an R2 URI proves indexing only. Read availability, stored-versus-remote size agreement, and verified SHA-256 integrity are separate states.</p>
              <p><strong>Result boundary:</strong> the stored database reward remains raw truth. Allow-listed Harbor result reward and exception fields are independent consistency evidence and never silently replace it.</p>
            </div>
          </details>

          <details>
            <summary>Artifact type reference</summary>
            <div className="concept-grid">
              {artifactTypeDefinitions.map((item) => (
                <article key={item.artifactType}>
                  <h3>{item.displayName} <span className="mono">{item.artifactType}</span></h3>
                  <p><strong>{item.shortDefinition}</strong> {item.definition}</p>
                  <p><strong>Best for:</strong> {item.bestFor.join(" ")}</p>
                  <p><strong>Caution:</strong> {item.cautions.join(" ")}</p>
                  <p className="muted">Common: {item.commonFilenames.join(", ")} · review priority: {item.reviewPriority}</p>
                </article>
              ))}
            </div>
          </details>
        </>
      ) : null}

      <div className="evidence-terminology">
        <strong>Important terminology:</strong> Claude Code transcript subtype <span className="mono">success</span> means the CLI terminated without a surfaced process/API exception. It does not mean the benchmark passed or that useful agent work occurred. Complete artifacts likewise do not imply substantive execution. Dashboard diagnoses are derived labels; raw rewards and stored quality flags are unchanged.
      </div>
    </section>
  );
}
