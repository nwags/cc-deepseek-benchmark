from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


def read_table(path: Path, delimiter: str):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_tsv(path: Path, rows: list[dict], cols: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in cols})


def phase_rows_from_combined(phase: str, path: Path) -> list[dict]:
    rows = read_table(path, ",")
    out = []
    for row in rows:
        out.append({
            "phase": phase,
            "arm_id": row["arm_dir"],
            "task_id": row.get("task_name") or row.get("task_path") or "",
            "trial_name": row.get("trial_name", ""),
            "success": row.get("success", ""),
            "source_file": str(path),
        })
    return out


def phase3_rows(path: Path) -> list[dict]:
    rows = read_table(path, "\t")
    out = []
    for row in rows:
        task = row.get("task_id") or row.get("task_name") or row.get("eval_id") or ""
        arm = row.get("arm_id") or row.get("arm") or ""
        trial = row.get("trial_id") or row.get("trial_name") or row.get("result_path") or ""
        out.append({
            "phase": "phase3",
            "arm_id": arm,
            "task_id": task,
            "trial_name": trial,
            "success": row.get("success") or row.get("reward") or "",
            "source_file": str(path),
        })
    return out


def summarize(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    by_phase_arm = defaultdict(list)
    by_phase = defaultdict(set)
    by_phase_arm_task = Counter()

    for row in rows:
        by_phase_arm[(row["phase"], row["arm_id"])].append(row)
        by_phase[row["phase"]].add(row["task_id"])
        by_phase_arm_task[(row["phase"], row["arm_id"], row["task_id"])] += 1

    arm_rows = []
    issue_rows = []

    for (phase, arm), arm_trials in sorted(by_phase_arm.items()):
        task_counts = Counter(row["task_id"] for row in arm_trials)
        unique_tasks = sorted(task_counts)
        count_values = sorted(set(task_counts.values()))
        expected_3_attempts = count_values == [3]
        expected_60_trials = len(arm_trials) == 60
        expected_20_tasks = len(unique_tasks) == 20

        status = "pass" if expected_3_attempts and expected_60_trials and expected_20_tasks else "review"
        arm_rows.append({
            "phase": phase,
            "arm_id": arm,
            "trial_count": len(arm_trials),
            "unique_task_count": len(unique_tasks),
            "attempt_counts_present": ",".join(str(x) for x in count_values),
            "status": status,
            "task_list": ",".join(unique_tasks),
        })

        if status != "pass":
            issue_rows.append({
                "phase": phase,
                "arm_id": arm,
                "issue": "unexpected trial/task/attempt shape",
                "detail": f"trials={len(arm_trials)} unique_tasks={len(unique_tasks)} attempt_counts={count_values}",
            })

        for task, count in sorted(task_counts.items()):
            if count != 3:
                issue_rows.append({
                    "phase": phase,
                    "arm_id": arm,
                    "issue": "task attempt count not 3",
                    "detail": f"{task} has {count} attempts",
                })

    phase_task_sets = {phase: tasks for phase, tasks in by_phase.items()}
    all_tasks = sorted(set().union(*phase_task_sets.values())) if phase_task_sets else []
    phase_rows = []

    for task in all_tasks:
        row = {"task_id": task}
        for phase in sorted(phase_task_sets):
            row[f"in_{phase}"] = "yes" if task in phase_task_sets[phase] else "no"
        phase_rows.append(row)

    phases = sorted(phase_task_sets)
    if phases:
        reference = phases[0]
        reference_tasks = phase_task_sets[reference]
        for phase in phases[1:]:
            missing = sorted(reference_tasks - phase_task_sets[phase])
            extra = sorted(phase_task_sets[phase] - reference_tasks)
            if missing:
                issue_rows.append({
                    "phase": phase,
                    "arm_id": "*",
                    "issue": f"tasks missing vs {reference}",
                    "detail": ",".join(missing),
                })
            if extra:
                issue_rows.append({
                    "phase": phase,
                    "arm_id": "*",
                    "issue": f"extra tasks vs {reference}",
                    "detail": ",".join(extra),
                })

    return arm_rows, phase_rows, issue_rows


def write_report(path: Path, arm_rows: list[dict], phase_rows: list[dict], issue_rows: list[dict]):
    phase_counts = defaultdict(set)
    for row in phase_rows:
        for key, value in row.items():
            if key.startswith("in_") and value == "yes":
                phase_counts[key.removeprefix("in_")].add(row["task_id"])

    lines = [
        "# Cross-phase task-set audit",
        "",
        "This report verifies whether Phase 1, Phase 2, and Phase 3 are comparable at the task-suite level.",
        "",
        "The expected scored-arm shape is 20 tasks × 3 attempts = 60 trials per arm.",
        "",
        "## Phase task counts",
        "",
        "| Phase | Unique tasks |",
        "|---|---:|",
    ]

    for phase in sorted(phase_counts):
        lines.append(f"| {phase} | {len(phase_counts[phase])} |")

    lines += [
        "",
        "## Arm shape audit",
        "",
        "| Phase | Arm | Trials | Unique tasks | Attempt counts present | Status |",
        "|---|---|---:|---:|---|---|",
    ]

    for row in arm_rows:
        lines.append(
            f"| {row['phase']} | `{row['arm_id']}` | {row['trial_count']} | "
            f"{row['unique_task_count']} | {row['attempt_counts_present']} | {row['status']} |"
        )

    lines += [
        "",
        "## Issues",
        "",
    ]

    if issue_rows:
        lines += [
            "| Phase | Arm | Issue | Detail |",
            "|---|---|---|---|",
        ]
        for row in issue_rows:
            detail = row["detail"].replace("|", "\\|")
            lines.append(f"| {row['phase']} | `{row['arm_id']}` | {row['issue']} | {detail} |")
    else:
        lines.append("No task-set or attempt-count issues found.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="20260714")
    parser.add_argument(
        "--phase3-trials",
        default="results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv",
    )
    args = parser.parse_args()

    rows = []
    rows += phase_rows_from_combined("phase1", Path("results/phase1/combined.csv"))
    rows += phase_rows_from_combined("phase2", Path("results/phase2/combined.csv"))
    rows += phase3_rows(Path(args.phase3_trials))

    arm_rows, phase_rows, issue_rows = summarize(rows)

    out_dir = Path("results/phase3/reporting")
    write_tsv(
        out_dir / f"cross_phase_task_arm_audit_{args.date}.tsv",
        arm_rows,
        ["phase", "arm_id", "trial_count", "unique_task_count", "attempt_counts_present", "status", "task_list"],
    )

    phase_cols = ["task_id"] + sorted([col for row in phase_rows for col in row if col.startswith("in_")])
    write_tsv(
        out_dir / f"cross_phase_task_membership_{args.date}.tsv",
        phase_rows,
        phase_cols,
    )

    write_tsv(
        out_dir / f"cross_phase_task_audit_issues_{args.date}.tsv",
        issue_rows,
        ["phase", "arm_id", "issue", "detail"],
    )

    write_report(
        Path(f"docs/reports/phase3/PHASE3_CROSS_PHASE_TASK_AUDIT_{args.date}.md"),
        arm_rows,
        phase_rows,
        issue_rows,
    )

    print("wrote cross-phase task audit artifacts")


if __name__ == "__main__":
    main()
