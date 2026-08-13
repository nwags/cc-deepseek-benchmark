import Link from "next/link";

import type { ReviewedPhase3ScopeId } from "../lib/phase3-reviewed-comparison";

type CorpusScopeSelectorProps = {
  pathname: "/cross-phase" | "/cost-coverage";
  selectedScopeId: ReviewedPhase3ScopeId;
};

const OPTIONS: readonly Readonly<{
  id: ReviewedPhase3ScopeId;
  label: string;
}>[] = [
  {
    id: "phase3-extended",
    label: "Phase 3 extended",
  },
  {
    id: "phase3-core",
    label: "Phase 3 core",
  },
];

export function CorpusScopeSelector({ pathname, selectedScopeId }: CorpusScopeSelectorProps) {
  return (
    <nav className="quality-context-panel" aria-label="Select reviewed Phase 3 corpus">
      <p><strong>Reviewed comparison scope</strong></p>
      <div className="row-action-links">
        {OPTIONS.map((option) => {
          const selected = option.id === selectedScopeId;
          return (
            <Link
              key={option.id}
              href={`${pathname}?scope=${option.id}`}
              aria-current={selected ? "page" : undefined}
              className={selected ? "quality-badge" : undefined}
            >
              {option.label}{selected ? " — selected" : ""}
            </Link>
          );
        })}
      </div>
      <p className="muted">
        Phase 3 extended is the current reviewed comparison. Phase 3 core preserves the historical reviewed snapshot.
      </p>
    </nav>
  );
}
