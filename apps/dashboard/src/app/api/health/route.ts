import { queryRows } from "../../../lib/db";

export async function GET() {
  const rows = await queryRows<{ runs: number; trials: number }>(`
    select
      count(*)::int as runs,
      coalesce(sum(trial_count), 0)::int as trials
    from benchmark.v_dashboard_runs
    where phase = 'phase3'
  `);

  return Response.json({
    ok: true,
    phase: "phase3",
    ...rows[0]
  });
}
