import Link from "next/link";
import { SuiteHeatmapCellRow } from "../lib/dashboard-data";
import { formatPercent } from "../lib/format";
import { TermInfo } from "./TermInfo";

function bucketClass(row: SuiteHeatmapCellRow | undefined) {
  if (!row || row.trial_count === 0 || row.pass_rate === null) return "heatmap-cell heatmap-cell-empty";
  if (row.pass_rate === 0) return "heatmap-cell heatmap-cell-0";
  if (row.pass_rate < 0.5) return "heatmap-cell heatmap-cell-1";
  if (row.pass_rate < 1) return "heatmap-cell heatmap-cell-2";
  return "heatmap-cell heatmap-cell-3";
}

export function SuiteHeatmap({
  rows,
  title = "Full-suite eval × arm heatmap",
  description = "Each cell shows successes / trials for one arm on one eval."
}: {
  rows: SuiteHeatmapCellRow[];
  title?: string;
  description?: string;
}) {
  const arms = Array.from(new Set(rows.map((row) => row.arm_id))).sort();

  const taskMap = new Map<string, {
    task_id: string;
    task_name: string | null;
    task_pass_rate: number | null;
    cells: Map<string, SuiteHeatmapCellRow>;
  }>();

  for (const row of rows) {
    if (!taskMap.has(row.task_id)) {
      taskMap.set(row.task_id, {
        task_id: row.task_id,
        task_name: row.task_name,
        task_pass_rate: row.task_pass_rate,
        cells: new Map()
      });
    }
    taskMap.get(row.task_id)?.cells.set(row.arm_id, row);
  }

  const tasks = Array.from(taskMap.values()).sort((a, b) => {
    const aRate = a.task_pass_rate ?? 999;
    const bRate = b.task_pass_rate ?? 999;
    if (aRate !== bRate) return aRate - bRate;
    return a.task_id.localeCompare(b.task_id);
  });

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          <p>
            {description} Darker cells indicate fewer successes. Use this as a pattern finder; tables remain the source of exact values.
          </p>
        </div>
        <div className="heatmap-legend" aria-label="Heatmap legend">
          <span><span className="heatmap-swatch heatmap-cell-0" />0%</span>
          <span><span className="heatmap-swatch heatmap-cell-1" />partial</span>
          <span><span className="heatmap-swatch heatmap-cell-2" />mostly</span>
          <span><span className="heatmap-swatch heatmap-cell-3" />100%</span>
        </div>
      </div>

      <div className="heatmap-scroll">
        <table className="heatmap-table">
          <thead>
            <tr>
              <th>Eval</th>
              <th><span className="term-label">Overall <TermInfo term="Pass rate" /></span></th>
              {arms.map((arm) => (
                <th key={arm} className="heatmap-arm-heading" title={arm} aria-label={arm}>{arm}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.task_id}>
                <th className="heatmap-task-heading">
                  <Link href={`/evals/${encodeURIComponent(task.task_id)}`}>
                    {task.task_name ?? task.task_id}
                  </Link>
                </th>
                <td className="heatmap-overall">{formatPercent(task.task_pass_rate)}</td>
                {arms.map((arm) => {
                  const cell = task.cells.get(arm);
                  return (
                    <td key={`${task.task_id}-${arm}`} className={bucketClass(cell)}>
                      {cell ? (
                        <span title={`${arm} on ${task.task_name ?? task.task_id}: ${cell.success_count}/${cell.trial_count}`}>
                          {cell.success_count}/{cell.trial_count}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
