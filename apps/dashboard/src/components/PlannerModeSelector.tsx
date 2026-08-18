import Link from "next/link";

import { PLANNER_MODE_OPTIONS, type PlannerMode } from "../lib/planner-modes";

export function PlannerModeSelector({ selectedMode }: { selectedMode: PlannerMode }) {
  return (
    <nav className="quality-context-panel" aria-label="Select Planner mode">
      <p><strong>Planner mode</strong></p>
      <div className="row-action-links">
        {PLANNER_MODE_OPTIONS.map((option) => {
          const selected = option.id === selectedMode;
          return (
            <Link
              key={option.id}
              href={`/planner?mode=${option.id}`}
              aria-current={selected ? "page" : undefined}
              className={selected ? "quality-badge" : undefined}
            >
              {option.label}{selected ? " — selected" : ""}
            </Link>
          );
        })}
      </div>
      <p className="muted">Both modes are read-only planning aids. They do not mutate the repository or launch workflows.</p>
    </nav>
  );
}
