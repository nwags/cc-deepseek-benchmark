-- Make imported benchmark runs idempotent.
-- A timestamped run directory should map to one logical run row.

create unique index if not exists idx_benchmark_runs_phase_mode_run_label_unique
    on benchmark.benchmark_runs(phase, mode, run_label);
