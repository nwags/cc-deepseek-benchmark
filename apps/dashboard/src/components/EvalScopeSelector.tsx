import Link from "next/link";

import type { EvalInventoryScopeId } from "../lib/eval-scopes";

const OPTIONS: readonly Readonly<{
  id: EvalInventoryScopeId;
  label: string;
}>[] = [
  { id: "valid-imported", label: "Valid imported" },
  { id: "all-imported", label: "All imported" },
];

export function EvalScopeSelector({ selectedScopeId }: { selectedScopeId: EvalInventoryScopeId }) {
  return (
    <nav className="quality-context-panel" aria-label="Select eval inventory scope">
      <p><strong>Eval inventory scope</strong></p>
      <div className="row-action-links">
        {OPTIONS.map((option) => {
          const selected = option.id === selectedScopeId;
          return (
            <Link
              key={option.id}
              href={`/evals?scope=${option.id}`}
              aria-current={selected ? "page" : undefined}
              className={selected ? "quality-badge" : undefined}
            >
              {option.label}{selected ? " — selected" : ""}
            </Link>
          );
        })}
      </div>
      <p className="muted">
        Valid imported excludes invalid or quarantined arm runs. All imported retains the broader task evidence formerly shown on Tasks.
        Neither scope is a fixed full-suite leaderboard denominator.
      </p>
    </nav>
  );
}
