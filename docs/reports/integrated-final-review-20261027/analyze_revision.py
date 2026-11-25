#!/usr/bin/env python3
"""Offline additions to the October 24 analysis. Never calls a provider or DB.

Run validate_report.py first. This script reads committed sanitized metadata,
extends the source inventory, and exports safe configuration/token summaries.
Thinking-event counts are metadata, never token counts or reasoning content.
"""
from __future__ import annotations

import csv
import hashlib
import json
import statistics
import subprocess
from collections import Counter
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "validation"
BASE = "79f790fdd9067e33a29e0409c15f8890068ff22d"
REVIEW = "results/manual_verification/comprehensive_review_20260731/"
CHECKS = []


def check(name, condition):
    CHECKS.append({"check": name, "passed": bool(condition)})
    if not condition:
        raise ValueError(name)


def read_csv(path, delimiter=","):
    with path.open(newline="") as f:
        return list(csv.DictReader(f, delimiter=delimiter))


def write_csv(name, rows):
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    check("HEAD remains pinned", subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == BASE)
    check("no tracked source modification", not subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=ROOT, text=True).strip())
    rows = read_csv(ROOT / REVIEW / "trial_review.csv")
    by_id = {r["trial_id"]: r for r in rows}
    evidence = [json.loads(line) for line in (ROOT / REVIEW / "trial_evidence.jsonl").read_text().splitlines()]
    check("960 exact evidence and review IDs", len(evidence) == len(by_id) == 960 and {e["trial_id"] for e in evidence} == by_id.keys())
    checks = {
        "task_commit": {"69671fbaac6d67a7ef0dfec016cc38a64ef7a77c": 960},
        "task_checksum": {None: 960},
        "timeout_multipliers": {"timeout_multiplier=1": 960},
        "verifier_configuration": {"enabled": 960},
        "resolved_model": {None: 960},
        "disallowed_tools": {"WebSearch,WebFetch,EnterPlanMode,ExitPlanMode,AskUserQuestion": 780, "WebSearch,WebFetch": 180},
        "claude_code_version": {"2.1.183": 180, "2.1.195": 480, "2.1.196": 13, "2.1.197": 99, "2.1.198": 8, "2.1.207": 120, "2.1.217": 60},
    }
    configuration = {}
    for key, expected in checks.items():
        counts = Counter((e.get("configuration") or {}).get(key) for e in evidence)
        check(f"retained configuration: {key}", counts == expected)
        configuration[key] = {"not_recorded" if k is None else k: v for k, v in counts.items()}
    check("no hidden reasoning retained", all(e.get("hidden_reasoning_retained") is False for e in evidence))
    check("thinking metadata integer for every trial", all(type(e.get("thinking_event_count")) is int and e["thinking_event_count"] >= 0 for e in evidence))
    check("868 trials with recorded thinking event metadata", sum(e["thinking_event_count"] > 0 for e in evidence) == 868)

    arm_rows, event_rows, config_rows = [], [], []
    for arm in sorted({r["arm_id"] for r in rows}):
        er = [e for e in evidence if by_id[e["trial_id"]]["arm_id"] == arm]
        arm_rows.append({
            "arm_id": arm, "trials": len(er),
            "trials_with_thinking_event_metadata": sum(e["thinking_event_count"] > 0 for e in er),
            "trials_without_recorded_thinking_event": sum(e["thinking_event_count"] == 0 for e in er),
            "median_thinking_event_count_NOT_tokens": statistics.median(e["thinking_event_count"] for e in er),
            "hidden_reasoning_content_retained": False,
            "cross_provider_reasoning_token_comparison_supported": False,
        })
        check(f"60 configuration rows: {arm}", len(er) == 60)
        for version, n in sorted(Counter(e["configuration"]["claude_code_version"] for e in er).items()):
            config_rows.append({"arm_id": arm, "claude_code_version": version, "trials": n})
        for e in er:
            r = by_id[e["trial_id"]]
            event_rows.append({"trial_id": e["trial_id"], "arm_id": arm, "raw_outcome": r["raw_outcome"],
                               "thinking_event_count_NOT_tokens": e["thinking_event_count"],
                               "evidence_complete": r["evidence_complete"], "hidden_reasoning_retained": False})
    write_csv("thinking_event_metadata_by_arm.csv", arm_rows)
    write_csv("thinking_event_metadata_by_trial.csv", event_rows)
    write_csv("retained_configuration_by_arm.csv", config_rows)

    op_path = "results/phase3/provider_usage/normalized/openai_provider_reconciliation_20260821.csv"
    usage_rows = []
    for r in read_csv(ROOT / op_path):
        if r["record_type"] != "full_sweep":
            continue
        total, cached, ordinary, output = [int(r[k]) for k in ["input_tokens", "cached_input_tokens", "uncached_input_tokens", "output_tokens"]]
        check(f"OpenAI input components: {r['arm_id']}", total == cached + ordinary)
        usage_rows.append({"arm_id": r["arm_id"], "scope": "selected_run", "authority": "provider_aggregate", "input_tokens": total,
                           "cache_read_tokens": cached, "other_input_tokens": ordinary, "output_tokens": output,
                           "cache_share_percent": str(Decimal(cached) / total * 100), "usage_bearing_trials": "aggregate_only",
                           "cache_creation_separate": "not_established", "source_path": op_path})

    # These totals are explicitly printed and semantically identified in the
    # committed provider ingestion reports. Their source is harness/session
    # usage, not provider billing. Do not silently upgrade their authority.
    selected = [
        ("router-deepseek-flash", 102663832, 100425344, 1733059, "60/60", "DEEPSEEK_PROVIDER_EVIDENCE_INGESTION_20260826.md"),
        ("router-deepseek-pro", 44293924, 42372608, 1046381, "60/60", "DEEPSEEK_PROVIDER_EVIDENCE_INGESTION_20260826.md"),
        ("router-gemini-3.1-pro", 25122141, 20368769, 509693, "60/60", "GEMINI_PROVIDER_EVIDENCE_INGESTION_20260827.md"),
        ("router-gemini-flash", 17250634, 10792465, 534977, "56/60", "GEMINI_PROVIDER_EVIDENCE_INGESTION_20260827.md"),
    ]
    for arm, total, cached, output, coverage, filename in selected:
        path = "docs/reports/phase3/" + filename
        source = (ROOT / path).read_text()
        for value in [total, cached, output]:
            check(f"retained published token total: {arm}/{value}", f"{value:,}" in source)
        check(f"cache subset geometry: {arm}", 0 <= cached <= total)
        usage_rows.append({"arm_id": arm, "scope": "selected_run", "authority": "qualified_harness_session", "input_tokens": total,
                           "cache_read_tokens": cached, "other_input_tokens": total - cached, "output_tokens": output,
                           "cache_share_percent": str(Decimal(cached) / total * 100), "usage_bearing_trials": coverage,
                           "cache_creation_separate": "not_established_in_collapsed_totals", "source_path": path})
    path = "docs/reports/phase3/KIMI_K3_PROVIDER_LOG_RECONCILIATION_20260805.md"
    text = (ROOT / path).read_text()
    for value in [39996874, 38341888, 1654986, 956453]:
        check(f"Kimi broader-log total: {value}", f"{value:,}" in text)
    usage_rows.append({"arm_id": "router-kimi-k3", "scope": "broader_provider_log_NOT_selected_run", "authority": "provider_log_low_run_allocation_confidence",
                       "input_tokens": 39996874, "cache_read_tokens": 38341888, "other_input_tokens": 1654986, "output_tokens": 956453,
                       "cache_share_percent": str(Decimal(38341888) / 39996874 * 100), "usage_bearing_trials": "unallocated",
                       "cache_creation_separate": "not_established", "source_path": path})
    write_csv("token_usage_scopes.csv", usage_rows)

    historical_path = "results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv"
    historical = read_csv(ROOT / historical_path, "\t")
    core_ids = {r["trial_id"] for r in rows if r["arm_id"] != "router-kimi-k3"}
    check("historical token table matches exact 900 core IDs", len(historical) == 900 and {r["trial_id"] for r in historical} == core_ids)
    output_rows = []
    for arm in sorted({r["arm_id"] for r in historical}):
        for outcome in ["success", "non_success"]:
            group = [r for r in historical if r["arm_id"] == arm and (by_id[r["trial_id"]]["raw_outcome"] == "success") == (outcome == "success")]
            # A zero or absent aggregate is not promoted to a zero provider bill.
            # The median is explicitly conditioned on positive retained usage.
            positive = [r for r in group if Decimal(r["input_tokens"] or 0) + Decimal(r["output_tokens"] or 0) > 0]
            med = statistics.median(Decimal(r["output_tokens"] or 0) for r in positive) if positive else None
            output_rows.append({"arm_id": arm, "raw_outcome_group": outcome, "selected_trials_in_group": len(group),
                                "positive_retained_usage_trials": len(positive), "no_positive_retained_usage_trials": len(group) - len(positive),
                                "median_output_tokens_given_positive_retained_usage": str(med) if med is not None else "",
                                "scope": "historical_900_core", "output_is_final_answer_only": False})
            check(f"output group coverage: {arm}/{outcome}", len(group) == len(positive) + int(output_rows[-1]["no_positive_retained_usage_trials"]))
    check("output groups retain all 900 core trials", sum(r["selected_trials_in_group"] for r in output_rows) == 900)
    for arm, outcome, expected in [("router-deepseek-flash", "success", "5442.5"), ("router-deepseek-flash", "non_success", "35036"),
                                    ("router-anthropic-haiku-sanitized", "success", "3260"), ("router-anthropic-haiku-sanitized", "non_success", "7991")]:
        value = next(r["median_output_tokens_given_positive_retained_usage"] for r in output_rows if r["arm_id"] == arm and r["raw_outcome_group"] == outcome)
        check(f"illustrative output median: {arm}/{outcome}", Decimal(value) == Decimal(expected))
    write_csv("output_tokens_by_outcome.csv", output_rows)
    for arm in ["router-gpt-5.4", "router-gpt-5.5"]:
        hr = [r for r in historical if r["arm_id"] == arm]
        check(f"historical OpenAI cache telemetry is zero: {arm}", len(hr) == 60 and all(Decimal(r["cache_tokens"] or 0) == 0 for r in hr))
    breakdown_path = "results/phase3/reporting/phase3_token_outcome_breakdown_20260713.tsv"
    breakdown = read_csv(ROOT / breakdown_path, "\t")
    totals = {k: str(sum(Decimal(r[k]) for r in breakdown)) for k in ["total_tokens", "failure_incomplete_tokens", "unclean_tokens"]}
    check("historical failure/incomplete token total", Decimal(totals["failure_incomplete_tokens"]) == 213482015)
    check("historical unclean token total", Decimal(totals["unclean_tokens"]) == 218979987)
    write_csv("historical_token_and_spend_shares.csv", breakdown)

    extra_refs = {
        "S28": "docs/reference/TASK_SELECTION.md",
        "S29": "docs/guides/CODEBASE_GUIDE.md",
        "S30": "scripts/lib/harbor.py",
        "S31": "configs/phases/phase3-router.yaml",
        "S32": REVIEW + "trial_evidence.jsonl",
        "S33": "docs/methodology/USAGE_AND_COST_EVIDENCE_MODEL.md",
        "S34": "apps/dashboard/src/lib/trial-analysis-core.ts",
        "S35": op_path,
        "S36": "docs/reports/phase3/OPENAI_PROVIDER_EVIDENCE_INGESTION_20260826.md",
        "S37": "docs/reports/phase3/DEEPSEEK_PROVIDER_EVIDENCE_INGESTION_20260826.md",
        "S38": "docs/reports/phase3/GEMINI_PROVIDER_EVIDENCE_INGESTION_20260827.md",
        "S39": breakdown_path,
        "S40": "scripts/lib/costs.py",
        "S41": "scripts/anthropic_sanitizer_proxy.py",
    }
    refs = json.loads((OUT / "source_reference_map.json").read_text()) | extra_refs
    (OUT / "source_reference_map.json").write_text(json.dumps(refs, indent=2) + "\n")
    inventory = {r["path"]: r for r in read_csv(OUT / "source_inventory.csv")}
    for path in extra_refs.values():
        p = ROOT / path
        inventory[path] = {"path": path, "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                           "last_change_commit": subprocess.check_output(["git", "log", "-1", "--format=%H", BASE, "--", path], cwd=ROOT, text=True).strip(),
                           "baseline_commit": BASE, "baseline_url": f"https://github.com/nwags/cc-deepseek-benchmark/blob/{BASE}/{path}"}
    write_csv("source_inventory.csv", [inventory[k] for k in sorted(inventory)])
    summary = {"review_date": "2026-10-27", "baseline": BASE, "checks_passed": len(CHECKS), "configuration_counts": configuration,
               "thinking_metadata": {"trials": 960, "positive_event_count_trials": 868, "zero_event_count_trials": 92,
                                     "hidden_reasoning_retained_trials": 0, "events_are_tokens": False,
                                     "reasoning_vs_final_token_split": "not_comparably_established"},
               "historical_core_token_totals": totals, "token_usage_scope_rows": len(usage_rows),
               "output_token_outcome_groups": len(output_rows),
               "source_of_configuration": REVIEW + "trial_evidence.jsonl", "fresh_raw_artifact_reads": False}
    (OUT / "revision_analysis_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (OUT / "revision_analysis_checks.json").write_text(json.dumps(CHECKS, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
