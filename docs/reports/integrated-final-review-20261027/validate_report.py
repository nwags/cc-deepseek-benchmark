#!/usr/bin/env python3
"""Offline arithmetic and provenance checks; writes only this review package.

No provider, database, R2, benchmark, or historical generator entry point is
called. Source snapshots are read without modification. Python standard library
only. Run from any directory with: python3 /path/to/validate_report.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import statistics
import subprocess
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "validation"
BASE = "79f790fdd9067e33a29e0409c15f8890068ff22d"
REPORTING = "results/phase3/reporting/"
REVIEW = "results/manual_verification/comprehensive_review_20260731/"
J2 = "results/manual_verification/failure_taxonomy_20260813/"
D = Decimal
CHECKS: list[dict] = []
SOURCES: set[str] = set()


def check(name, condition, detail=None):
    CHECKS.append({"check": name, "passed": bool(condition), "detail": detail})
    if not condition:
        raise ValueError(f"Validation failed: {name}: {detail}")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source(path):
    SOURCES.add(path)
    return ROOT / path


def read_json(path):
    return json.loads(source(path).read_text())


def rows(path):
    with source(path).open(newline="") as f:
        return list(csv.DictReader(f, delimiter="\t" if path.endswith(".tsv") else ","))


def jsonl(path):
    return [json.loads(line) for line in source(path).read_text().splitlines() if line]


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n")


def write_csv(name, data):
    with (OUT / name).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def verify_inputs(label, data):
    for item in data.get("inputs", []):
        if isinstance(item, dict) and "path" in item and "sha256" in item:
            check(f"{label}: input {item['role']}", sha(source(item["path"])) == item["sha256"])


def verify_manifest(directory, manifest):
    for name, item in manifest["outputs"].items():
        p = source(directory + name)
        check(f"manifest hash: {directory}{name}", sha(p) == item["sha256"])
        check(f"manifest bytes: {directory}{name}", p.stat().st_size == item["bytes"])
        if item.get("rows") is not None:
            count = len(jsonl(directory + name) if name.endswith(".jsonl") else rows(directory + name))
            check(f"manifest rows: {directory}{name}", count == item["rows"], count)


def composition(r, t):
    # Reproduce DR-302 presentation precedence, never changing raw outcomes.
    if r["raw_outcome"] != "failure":
        return None
    if r["policy_disposition"] == "provider_policy_refusal":
        return "provider_policy_refusal"
    if r["execution_validity"] == "invalid_response_path":
        return "invalid_response_path"
    if r["failure_subtype"] in {"missing_required_output", "extraneous_output_artifacts"}:
        return r["failure_subtype"]
    if r["activity_subtype"] == "timeout_after_meaningful_activity":
        return "timeout_after_meaningful_activity"
    if t["verifier_failure_category"]["value"] != "none":
        return "verifier_task_failure"
    return "unknown_or_incomplete_evidence"


def main():
    OUT.mkdir(exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    check("base commit pinned", head == BASE, head)
    check("tracked source tree unchanged before analysis", not subprocess.check_output(
        ["git", "diff", "HEAD", "--name-only"], cwd=ROOT, text=True).strip())

    review_manifest = read_json(REVIEW + "review_manifest.json")
    taxonomy_manifest = read_json(J2 + "failure_taxonomy_manifest.json")
    verify_manifest(REVIEW, review_manifest)
    verify_manifest(J2, taxonomy_manifest)
    check("review/J2 scope fingerprint agrees", review_manifest["scope_fingerprint"] == taxonomy_manifest["scope_fingerprint"])
    for item in taxonomy_manifest["inputs"].values():
        check(f"J2 input hash: {item['path']}", sha(source(item["path"])) == item["sha256"])
    for item in taxonomy_manifest["implementations"].values():
        check(f"J2 producer hash: {item['path']}", sha(source(item["path"])) == item["sha256"])
    for role, path in {"analyzer": "apps/dashboard/src/lib/trial-analysis-core.ts", "generator": "scripts/generate_comprehensive_evidence_review.py"}.items():
        check(f"comprehensive producer hash: {role}", sha(source(path)) == review_manifest["source_hashes"][role])

    snapshots = {}
    for label, name in {
        "historical": "phase3_extended_reviewed_comparison_20260805.json",
        "selection": "phase3_reviewed_run_selection_20260809.json",
        "aug21": "phase3_current_reviewed_comparison_20260821.json",
        "aug24": "phase3_current_reviewed_comparison_20260824.json",
        "current": "phase3_current_reviewed_comparison_20260825.json",
    }.items():
        snapshots[label] = read_json(REPORTING + name)
        verify_inputs(label, snapshots[label])

    trial_rows = rows(REVIEW + "trial_review.csv")
    trials = {r["trial_id"]: r for r in trial_rows}
    tax = {r["trial_id"]: r for r in jsonl(J2 + "trial_failure_taxonomy.jsonl")}
    evidence = {r["trial_id"]: r for r in jsonl(REVIEW + "trial_evidence.jsonl")}
    check("exact 960 unique review/J2/evidence trial IDs", len(trials) == len(trial_rows) == 960 and trials.keys() == tax.keys() == evidence.keys())
    trial_ids_hash = hashlib.sha256("\n".join(sorted(trials)).encode()).hexdigest()
    check("exact reviewed trial-ID manifest digest", trial_ids_hash == review_manifest["scope_fingerprint_inputs"]["trial_ids_sha256"], trial_ids_hash)
    for tid, r in trials.items():
        check(f"trial identity/outcome join: {tid}", all(r[k] == tax[tid][k] for k in ["arm_id", "task_id", "raw_outcome"]))

    scope_totals, scope_rows = {}, []
    all_task_ids = {r["task_id"] for r in trial_rows}
    for scope_id, expected_n, expected_s in [("phase3-core", 900, 515), ("phase3-extended", 960, 562)]:
        selection = snapshots["selection"]["scopes"][scope_id]["selections"]
        selected = {r["armId"]: r["selectedRunLabel"] for r in selection}
        selected_rows = [r for r in trial_rows if r["arm_id"] in selected]
        check(f"{scope_id}: exact run membership", all(r["run_label"] == selected[r["arm_id"]] for r in selected_rows))
        for arm_id in selected:
            ar = [r for r in selected_rows if r["arm_id"] == arm_id]
            check(f"{scope_id}: 20 x 3 shape {arm_id}", len(ar) == 60 and {r["task_id"] for r in ar} == all_task_ids and set(Counter(r["task_id"] for r in ar).values()) == {3})
            check(f"{scope_id}: attempts 1/2/3 {arm_id}", all({r["task_attempt"] for r in ar if r["task_id"] == t} == {"1", "2", "3"} for t in all_task_ids))
        outcomes = Counter(r["raw_outcome"] for r in selected_rows)
        check(f"{scope_id}: total/raw-success reproduction", len(selected_rows) == expected_n and outcomes["success"] == expected_s, dict(outcomes))
        current_scope = snapshots["current"]["scopes"][scope_id]
        current_sum = sum(D(a["selectedCostUsd"]) for a in current_scope["arms"])
        check(f"{scope_id}: selected cost decimal sum", current_sum == D(current_scope["selectedCostEvidence"]["selectedCostUsd"]), str(current_sum))
        clean = sum(r["raw_outcome"] == "success" and not r["exception_type"] for r in selected_rows)
        check(f"{scope_id}: clean-success reproduction", clean == sum(a["cleanSuccessCount"] for a in current_scope["arms"]), clean)
        ids = sorted(r["trial_id"] for r in selected_rows)
        scope_totals[scope_id] = {"arms": len(selected), "trials": len(selected_rows), "outcomes": dict(outcomes), "clean_successes": clean, "selected_cost_usd": str(current_sum), "trial_ids_sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest()}
        write_json(scope_id + "_derived_membership_manifest.json", {
            "schema": "integrated-report-derived-membership-v1",
            "authority": "Derived export only; original reviewed manifests and run selection remain authoritative.",
            "scope": scope_id,
            "baseline_commit": BASE,
            "review_manifest_sha256": sha(source(REVIEW + "review_manifest.json")),
            "run_selection_sha256": sha(source(REPORTING + "phase3_reviewed_run_selection_20260809.json")),
            "trial_count": len(ids),
            "trial_ids_sha256": scope_totals[scope_id]["trial_ids_sha256"],
            "selected_run_labels": selected,
            "trial_ids": ids,
        })
        for r in selected_rows:
            scope_rows.append({k: r[k] for k in ["trial_id", "run_label", "arm_id", "task_id", "task_attempt", "raw_outcome"]} | {"scope": scope_id})
    write_csv("exact_reviewed_trial_membership.csv", scope_rows)

    core_cost = rows(REPORTING + "phase3_trial_cost_coverage_20260712.tsv")
    core_ids = {r["trial_id"] for r in core_cost}
    check("900 core cost IDs equal selected core review IDs", core_ids == {r["trial_id"] for r in scope_rows if r["scope"] == "phase3-core"})
    core_recorded = sum(D(r["recorded_cost_usd"]) for r in core_cost if r["recorded_cost_usd"])
    core_adjusted_rows = sum(D(r["adjusted_cost_usd"]) for r in core_cost if r["adjusted_cost_usd"])
    core_arm_cost = rows(REPORTING + "phase3_arm_cost_coverage_20260712.tsv")
    core_adjusted_arms = sum(D(r["adjusted_cost_usd"]) for r in core_arm_cost)
    check("historical core recorded cost reproduced", core_recorded == D("820.77472875"))
    check("historical core adjusted arm sum reproduced", core_adjusted_arms == D("972.169845489198"))
    check("historical row/arm rounding residual bounded", abs(core_adjusted_arms - core_adjusted_rows) < D("0.000000001"))

    ledger = {r["arm_id"]: r for r in rows(REPORTING + "phase3_current_arm_cost_reconciliation_20260825.csv")}
    contract = {r["arm_id"]: r for r in rows(REPORTING + "phase3_cross_provider_consistency_20260828.csv")}
    current_arms = snapshots["current"]["scopes"]["phase3-extended"]["arms"]
    check("exact arm membership across ledger/contract/current layer", ledger.keys() == contract.keys() == {a["armId"] for a in current_arms})
    arm_rows, failure_rows, refusal_rows = [], [], []
    global_composition = Counter()
    for a in sorted(current_arms, key=lambda a: (-a["successCount"], a["armId"])):
        aid = a["armId"]
        ar = [r for r in trial_rows if r["arm_id"] == aid]
        l, c = ledger[aid], contract[aid]
        check(f"selected run/cost contract: {aid}", l["selected_run_label"] == c["selected_run_label"] == a["currentSelectedRunLabel"] and D(l["selected_cost_usd"]) == D(c["reporting_selected_cost_usd"]) == D(a["selectedCostUsd"]) and l["selected_cost_relation"] == c["reporting_selected_cost_relation"] == a["selectedCostRelation"])
        out = Counter(r["raw_outcome"] for r in ar)
        clean = sum(r["raw_outcome"] == "success" and not r["exception_type"] for r in ar)
        check(f"arm success/clean count: {aid}", out["success"] == a["successCount"] and clean == a["cleanSuccessCount"])
        arm_rows.append({"arm_id": aid, "run_label": a["currentSelectedRunLabel"], "raw_successes": out["success"], "clean_successes": clean, "raw_failures": out["failure"], "not_recorded": out["not_recorded"], "trials": len(ar), "median_retained_runtime_seconds": statistics.median(float(r["runtime_seconds"]) for r in ar if r["runtime_seconds"]), "selected_cost_usd": a["selectedCostUsd"], "selected_relation": a["selectedCostRelation"], "selected_basis": a["selectedCostBasis"], "confidence": a["selectedCostConfidence"], "provider_billed_cost_usd": a["providerBilledCostUsd"], "normalized_state": c["contract_state"], "cost_per_clean_success_ratio_usd": str(D(a["selectedCostUsd"]) / clean), "trial_allocation": a["selectedTrialCostAllocationStatus"], "outcome_allocation": a["selectedOutcomeCostAllocationStatus"]})
        comp = Counter(composition(r, tax[r["trial_id"]]) for r in ar if r["raw_outcome"] == "failure")
        global_composition.update(comp)
        for cat, n in comp.items():
            failure_rows.append({"arm_id": aid, "category": cat, "count": n})
        for r in ar:
            if r["policy_disposition"] == "provider_policy_refusal":
                refusal_rows.append({k: r[k] for k in ["trial_id", "run_label", "arm_id", "task_attempt", "raw_outcome", "canonical_completeness", "evidence_complete", "supporting_artifact_ids"]})
    expected_comp = {"verifier_task_failure": 167, "timeout_after_meaningful_activity": 127, "provider_policy_refusal": 9, "invalid_response_path": 4, "missing_required_output": 7, "extraneous_output_artifacts": 22, "unknown_or_incomplete_evidence": 34}
    check("DR-302 exact failure composition", dict(global_composition) == expected_comp, dict(global_composition))
    check("nine refusals in one selected arm", len(refusal_rows) == 9 and {r["arm_id"] for r in refusal_rows} == {"router-anthropic-fable-5"})
    successful_timeouts = sum(r["raw_outcome"] == "success" and r["activity_subtype"] == "timeout_after_meaningful_activity" for r in trial_rows)
    check("19 successful timeout anomalies excluded from raw-failure partition", successful_timeouts == 19)
    write_csv("arm_comparison.csv", arm_rows)
    write_csv("failure_composition_by_arm.csv", failure_rows)
    write_csv("refusal_trial_ids.csv", refusal_rows)
    trace_specs = [
        ("ordinary success / control", lambda r: r["arm_id"] == "router-deepseek-flash" and r["raw_outcome"] == "success" and r["termination_subtype"] == "none"),
        ("policy refusal", lambda r: r["policy_disposition"] == "provider_policy_refusal"),
        ("successful timeout / counterexample", lambda r: r["arm_id"] == "router-kimi-k3" and r["raw_outcome"] == "success" and r["activity_subtype"] == "timeout_after_meaningful_activity"),
        ("dominant Gemini Flash timeout pattern", lambda r: r["arm_id"] == "router-gemini-flash" and composition(r, tax[r["trial_id"]]) == "timeout_after_meaningful_activity"),
        ("Haiku verifier/task failure", lambda r: r["arm_id"] == "router-anthropic-haiku-sanitized" and composition(r, tax[r["trial_id"]]) == "verifier_task_failure"),
        ("incomplete residual / uncertainty", lambda r: composition(r, tax[r["trial_id"]]) == "unknown_or_incomplete_evidence" and r["evidence_complete"] == "False"),
    ]
    traces = []
    for purpose, predicate in trace_specs:
        r = next(r for r in sorted(trial_rows, key=lambda r: r["trial_id"]) if predicate(r))
        t = tax[r["trial_id"]]
        traces.append({"purpose": purpose, "selection": "Deterministic first sorted trial ID matching the declared pattern; representative illustration, not random prevalence sample.", "review_source": REVIEW + "trial_review.csv", "taxonomy_source": J2 + "trial_failure_taxonomy.jsonl", "trial": {k: r[k] for k in ["trial_id", "run_label", "arm_id", "raw_outcome", "execution_validity", "activity_subtype", "policy_disposition", "failure_subtype", "termination_subtype", "canonical_completeness", "evidence_complete", "classification_confidence"]}, "taxonomy": {k: {"value": t[k]["value"], "confidence": t[k]["confidence"]} for k in ["response_path_class", "verifier_failure_category", "assertion_failure_category", "trajectory_disposition"]}, "supporting_artifact_ids": json.loads(r["supporting_artifact_ids"]), "full_raw_artifact_read_this_review": False, "dashboard_path": "/trials/" + r["trial_id"]})
    write_json("evidence_traces.json", traces)
    frontiers = {}
    for metric in ["raw_successes", "clean_successes"]:
        frontiers[metric] = sorted(r["arm_id"] for r in arm_rows if not any(
            D(q["selected_cost_usd"]) <= D(r["selected_cost_usd"])
            and q[metric] >= r[metric]
            and (D(q["selected_cost_usd"]) < D(r["selected_cost_usd"]) or q[metric] > r[metric])
            for q in arm_rows))
        check(f"nominal current frontier: {metric}", frontiers[metric] == ["router-deepseek-flash", "router-kimi-k3"])

    families = {r["task_id"]: r["task_family"] for r in rows("configs/tasks/phase3_task_taxonomy.tsv")}
    family_rows, task_rows = [], []
    for scope in ["phase3-core", "phase3-extended"]:
        sr = [r for r in trial_rows if scope == "phase3-extended" or r["arm_id"] != "router-kimi-k3"]
        for family in sorted(set(families.values())):
            for aid in ["ALL"] + sorted({r["arm_id"] for r in sr}):
                fr = [r for r in sr if families[r["task_id"]] == family and (aid == "ALL" or r["arm_id"] == aid)]
                family_rows.append({"scope": scope, "arm_id": aid, "family": family, "task_count": len({r["task_id"] for r in fr}), "trials": len(fr), "raw_successes": sum(r["raw_outcome"] == "success" for r in fr), "clean_successes": sum(r["raw_outcome"] == "success" and not r["exception_type"] for r in fr), "raw_failures": sum(r["raw_outcome"] == "failure" for r in fr), "not_recorded": sum(r["raw_outcome"] == "not_recorded" for r in fr)})
        for task in sorted(all_task_ids):
            tr = [r for r in sr if r["task_id"] == task]
            task_rows.append({"scope": scope, "task_id": task, "trials": len(tr), "successes": sum(r["raw_outcome"] == "success" for r in tr)})
    old_families = rows(REPORTING + "phase3_task_family_arm_matrix_20260716.tsv")
    lookup = {(r["arm_id"], r["family"]): r for r in family_rows if r["scope"] == "phase3-core"}
    check("all 150 historical core arm/family counts reproduced", len(old_families) == 150 and all(int(r["success_count"]) == lookup[(r["arm_id"], r["task_family"])]["raw_successes"] and int(r["trial_count"]) == lookup[(r["arm_id"], r["task_family"])]["trials"] for r in old_families))
    write_csv("task_family_profiles.csv", family_rows)
    write_csv("task_profiles.csv", task_rows)

    phase_rows = []
    for phase in ["phase1", "phase2"]:
        pr = rows(f"results/{phase}/combined.csv")
        check(f"{phase}: same 20-task subset", {"terminal-bench-2.0:" + r["task_name"] for r in pr} == all_task_ids)
        for aid in sorted({r["arm_dir"] for r in pr}):
            ar = [r for r in pr if r["arm_dir"] == aid]
            check(f"{phase}: 60 trials/20x3 {aid}", len(ar) == 60 and len(Counter(r["task_name"] for r in ar)) == 20 and set(Counter(r["task_name"] for r in ar).values()) == {3})
            phase_rows.append({"phase": phase, "arm_id": aid, "trials": len(ar), "successes": sum(r["success"] == "True" for r in ar), "recorded_cost_usd": str(sum(D(r["effective_cost_usd"]) for r in ar if r["effective_cost_usd"])), "missing_cost_rows": sum(not r["effective_cost_usd"] for r in ar), "median_wall_clock_seconds": statistics.median(float(r["wall_clock_seconds"]) for r in ar)})
    check("Phase 1 headline successes", sum(r["successes"] for r in phase_rows if r["phase"] == "phase1") == 118)
    check("Phase 2 headline successes", sum(r["successes"] for r in phase_rows if r["phase"] == "phase2") == 185)
    write_csv("phase1_phase2_reproduction.csv", phase_rows)

    # Exact retained canary fingerprint: no task instructions/transcript excerpts copied.
    canary_path = "results/phase3/canary/arm-router-gpt-5.4/2026-06-03__00-58-05/modernize-scientific-stack__WACxyXT/result.json"
    canary = read_json(canary_path)["agent_result"]
    canary_formula = D(str(canary["n_input_tokens"])) * D(5) / 1000000 + D(str(canary["n_output_tokens"])) * D(25) / 1000000
    check("retained GPT canary incorrect client-price arithmetic", canary_formula == D(str(canary["cost_usd"])) == D("0.799355") and canary["n_cache_tokens"] == 0)
    openai = rows("results/phase3/provider_usage/normalized/openai_provider_reconciliation_20260821.csv")
    openai_current = sum(D(a["selectedCostUsd"]) for a in current_arms if a["provider"] == "openai")
    check("OpenAI exact selected-run cost total", openai_current == D("78.3968475"))
    check("OpenAI sanitized selected cost rows reproduce", sum(D(r["provider_billed_cost_usd"]) for r in openai if r["record_type"] == "full_sweep") == openai_current)
    check("OpenAI aggregate allocation firewall", all(a["selectedTrialCostAllocationStatus"] == a["selectedOutcomeCostAllocationStatus"] == "unavailable_provider_aggregate" for a in current_arms if a["provider"] == "openai"))
    kimi = next(a for a in current_arms if a["armId"] == "router-kimi-k3")
    check("Kimi estimate/no outcome join preserved", kimi["selectedCostRelation"] == "estimate" and kimi["selectedOutcomeCostAllocationStatus"] == "unavailable_no_reviewed_outcome_join")
    check("16 reporting cost relations differ from 10 normalized authority chains", Counter(a["selectedCostRelation"] for a in current_arms) == {"exact": 4, "estimate": 7, "lower_bound": 5} and Counter(r["contract_state"] for r in contract.values()) == {"accepted_absence_anthropic_not_normalized": 4, "accepted_absence_glm_deliberate_empty": 2, "normalized_exact_provider_billed": 2, "normalized_qualified_lower_bound": 3, "normalized_qualified_rate_estimate": 5})

    chronology = []
    for label in ["historical", "aug21", "aug24", "current"]:
        data = snapshots[label]
        for scope_id, scope in data["scopes"].items():
            arm_costs = []
            for a in scope["arms"]:
                value = a.get("selectedCostUsd") or a.get("adjustedKnownCostUsd") or a.get("qualifiedRetainedRateCostUsd")
                arm_costs.append(D(value))
                chronology.append({"layer": label, "reviewed_at": data["reviewedAt"], "scope": scope_id, "arm_id": a["armId"], "cost_usd": value})
            scope_totals[scope_id][label + "_arm_cost_sum_usd"] = str(sum(arm_costs))
    write_csv("cost_chronology.csv", chronology)

    navigation = source("apps/dashboard/src/components/AppShell.tsx").read_text()
    nav = re.findall(r'\{ href: "([^"]+)", label: "([^"]+)" \}', navigation)
    check("exact principal dashboard surface count", len(nav) == 16)
    dashboard_rows = []
    for route, label in nav:
        path = "apps/dashboard/src/app/" + (route.strip("/") + "/" if route != "/" else "") + "page.tsx"
        check(f"dashboard route source exists: {label}", source(path).is_file())
        dashboard_rows.append({"surface": label, "route": route, "page_source": path, "source_contract_review": "documentation reviewed; no rendered acceptance", "live_rendered_status": "unavailable", "access_limit": "no shared URL; SUPABASE_DB_URL absent; separate local HTTP requests refused"})
    write_csv("dashboard_surface_review.csv", dashboard_rows)

    # Exploratory paired task-cluster bootstrap, not a universal model-ranking test.
    task_deltas = []
    for task in sorted(all_task_ids):
        a = sum(r["raw_outcome"] == "success" for r in trial_rows if r["task_id"] == task and r["arm_id"] == "router-kimi-k3")
        b = sum(r["raw_outcome"] == "success" for r in trial_rows if r["task_id"] == task and r["arm_id"] == "router-gpt-5.5")
        task_deltas.append((a - b) / 3)
    rng = random.Random(20261024)
    boot = sorted(statistics.mean(rng.choices(task_deltas, k=20)) * 100 for _ in range(20000))

    # Hash public sources used by this report and each page manual; no private input.
    for glob in ["docs/guides/*.md", "docs/guides/dashboard/*.md", "docs/reports/phase3/*202607*.md", "docs/reports/phase3/*202608*.md"]:
        SOURCES.update(str(p.relative_to(ROOT)) for p in ROOT.glob(glob))
    SOURCES.update(["AGENTS.md", "README.md", "apps/dashboard/README.md", "apps/dashboard/src/lib/failure-composition.ts", "docs/methodology/USAGE_AND_COST_EVIDENCE_MODEL.md", "docs/runbooks/ARTIFACT_POLICY.md", "docs/runbooks/BENCHMARK_CONTAMINATION.md", "docs/runbooks/COLLABORATION.md", "docs/plans/TEAM_PROVIDER_EVIDENCE_RELAY_API_PLAN_20260831.md", "docs/plans/PROVIDER_EVIDENCE_IMPORT_AND_STAGE_CAPTURE_PLAN_20260831.md"])
    inventory = []
    for path in sorted(SOURCES):
        p = ROOT / path
        commit = subprocess.check_output(["git", "log", "-1", "--format=%H", BASE, "--", path], cwd=ROOT, text=True).strip()
        inventory.append({"path": path, "bytes": p.stat().st_size, "sha256": sha(p), "last_change_commit": commit, "baseline_commit": BASE, "baseline_url": f"https://github.com/nwags/cc-deepseek-benchmark/blob/{BASE}/{path}"})
    write_csv("source_inventory.csv", inventory)

    check("tracked source tree unchanged after analysis", not subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=ROOT, text=True).strip())
    summary = {"base_commit": BASE, "checks_passed": len(CHECKS), "scopes": scope_totals, "nominal_frontiers": frontiers, "raw_failure_composition": dict(global_composition), "successful_timeout_anomalies": successful_timeouts, "historical_core_recorded_usd": str(core_recorded), "historical_core_adjusted_arm_usd": str(core_adjusted_arms), "historical_core_adjusted_trial_usd": str(core_adjusted_rows), "historical_core_row_minus_arm_residual_usd": str(core_adjusted_rows - core_adjusted_arms), "raw_outcomes": dict(Counter(r["raw_outcome"] for r in trial_rows)), "review_evidence_complete": dict(Counter(r["evidence_complete"] for r in trial_rows)), "review_confidence": dict(Counter(r["classification_confidence"] for r in trial_rows)), "router_observability": dict(Counter(r["router_observability"] for r in trial_rows)), "normalized_states": dict(Counter(r["contract_state"] for r in contract.values())), "reporting_cost_relations": dict(Counter(a["selectedCostRelation"] for a in current_arms)), "exploratory_k3_minus_gpt55_task_bootstrap": {"seed": 20261024, "resamples": 20000, "unit": "20 tasks, paired 3-attempt raw-success averages", "delta_percentage_points": statistics.mean(task_deltas) * 100, "percentile_95_interval_percentage_points": [boot[499], boot[19499]], "qualification": "Exploratory sensitivity to resampling this selected public task subset; not a representative-workload confidence guarantee."}, "dashboard_live_review": "unavailable_no_shared_url_or_SUPABASE_DB_URL", "phase3_full_raw_files": "not present in committed checkout; read committed manifest-bound derived review and historical cost rows", "fresh_provider_DB_R2_validation": "not performed"}
    write_json("validation_summary.json", summary)
    write_json("validation_checks.json", CHECKS)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
