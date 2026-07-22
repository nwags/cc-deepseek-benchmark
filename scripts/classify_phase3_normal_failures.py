#!/usr/bin/env python3
"""Classify Phase 3 normal failed trials with deterministic first-pass rules."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.classify_phase3_exception_artifacts import (
    CONFIDENCE_BY_RANK,
    CONFIDENCE_RANK,
    EvidenceSource,
    R2Client,
    Rule,
    RuleMatch,
    adjusted_confidence,
    bool_from_text,
    dashboard_url,
    excerpt_contains_signal,
    markdown_table,
    normalize_evidence_sources,
    redact_secrets,
    safe_excerpt,
    signal,
)
from scripts.generate_phase3_qualitative_audit import utc_datestamp, write_tsv


DEFAULT_TRIAL_EVIDENCE = Path("results/phase3/reporting/phase3_trial_evidence_audit_20260709.tsv")
DEFAULT_OUTPUT_DIR = Path("results/phase3/reporting")
DEFAULT_BASE_URL = "http://127.0.0.1:3000"
NORMAL_FAILURE_FLAG = "normal_failed_trial"
MAX_NORMAL_ARTIFACT_BYTES = 96 * 1024

RELATED_ARTIFACT_TYPES = (
    "verifier_stdout",
    "verifier_ctrf",
    "verifier_reward",
    "result",
    "log",
    "agent_transcript",
    "trajectory",
)
PRIMARY_ARTIFACT_TYPES = ("verifier_stdout", "verifier_ctrf", "verifier_reward", "result")
FALLBACK_ARTIFACT_TYPES = ("log", "agent_transcript", "trajectory")
ARTIFACT_TYPE_RANK = {artifact_type: index for index, artifact_type in enumerate(RELATED_ARTIFACT_TYPES)}

CLASSIFICATION_HEADERS = [
    "suite_id",
    "arm_id",
    "run_label",
    "task_id",
    "attempt_index",
    "trial_id",
    "reward",
    "runtime_seconds",
    "primary_category",
    "secondary_category",
    "confidence",
    "needs_manual_review",
    "matched_signal",
    "matched_pattern",
    "evidence_artifact_type",
    "evidence_artifact_id",
    "evidence_excerpt",
    "classification_reason",
    "trial_dashboard_path",
    "recommended_next_step",
    "notes",
]

SUMMARY_HEADERS = [
    "arm_id",
    "primary_category",
    "count",
    "representative_tasks",
    "representative_matched_signals",
    "needs_manual_review_count",
    "confidence_floor",
]

CATEGORY_PRIORITY = {
    "verifier_environment_issue": 0,
    "syntax_or_compile_error": 1,
    "dependency_or_import_error": 2,
    "wrong_file_or_path": 3,
    "timeout_inside_verifier": 4,
    "runtime_exception_in_solution": 5,
    "test_assertion_failure": 6,
    "missing_or_wrong_output": 7,
    "no_meaningful_code_change": 8,
    "partial_solution": 9,
}

ASSERTION_SECONDARY_PRIORITY = {
    "performance_threshold_failure": 0,
    "numerical_or_data_mismatch": 1,
    "missing_expected_file_or_content": 2,
    "behavior_mismatch": 3,
    "output_mismatch": 4,
}


@dataclass(frozen=True)
class NormalFailureClassification:
    primary_category: str
    secondary_category: str
    confidence: str
    needs_manual_review: bool
    matched_signal: str
    matched_pattern: str
    evidence_artifact_type: str
    evidence_artifact_id: str
    evidence_excerpt: str
    classification_reason: str
    recommended_next_step: str
    notes: str


RULES = (
    Rule(
        category="verifier_environment_issue",
        confidence="high",
        patterns=(
            signal(
                "pytest setup/fixture failure",
                r"(?:ERROR at setup of|fixture ['\"]?\w+['\"]? not found|"
                r"(?:fixture|pytest|verifier) setup (?:failed|failure|error))",
            ),
            signal(
                "pytest collection error",
                r"(?:ERROR collecting|error(?:s)? during collection|collection error(?:s)?|"
                r"collected 0 items / \d+ errors?)",
            ),
            signal(
                "verifier/test import error",
                r"(?:ImportError while importing test module|"
                r"(?:verifier|test harness|conftest|pytest setup)[\s\S]{0,160}"
                r"\b(?:ImportError|ModuleNotFoundError)\b|"
                r"\b(?:ImportError|ModuleNotFoundError)\b[\s\S]{0,160}"
                r"(?:verifier setup|test harness|conftest))",
            ),
            signal(
                "missing verifier/test dependency",
                r"(?:verifier|pytest|test harness|conftest)[^\n]{0,120}"
                r"(?:dependency|package)[^\n]{0,80}(?:missing|not installed|not found)",
            ),
            signal(
                "permission denied in verifier setup",
                r"(?:(?:verifier|pytest|test|setup)[^\n]{0,120}permission denied|"
                r"permission denied[^\n]{0,120}(?:verifier|pytest|/tests|conftest|setup))",
            ),
            signal(
                "missing verifier environment variable",
                r"(?:(?:verifier|pytest|test|setup)[^\n]{0,120}"
                r"(?:environment variable|env var)[^\n]{0,80}(?:missing|not set|required)|"
                r"(?:environment variable|env var)[^\n]{0,80}(?:missing|not set|required)"
                r"[^\n]{0,120}(?:verifier|pytest|test|setup))",
            ),
            signal("no tests collected", r"(?:no tests (?:ran|collected)|collected 0 items\b)"),
            signal(
                "pytest infrastructure exception",
                r"(?:pytest internal error|INTERNALERROR>|PluggyTeardownRaisedWarning|"
                r"_pytest\.[A-Za-z_.]+Error)",
            ),
        ),
        recommended_next_step="Inspect verifier setup, collection, and test infrastructure independently of the candidate solution.",
    ),
    Rule(
        category="syntax_or_compile_error",
        confidence="high",
        patterns=(
            signal("SyntaxError", r"\bSyntaxError\b"),
            signal("IndentationError", r"\bIndentationError\b"),
            signal("compile error", r"\bcompile error\b"),
            signal("compilation failed", r"compilation failed"),
            signal("failed to compile", r"failed to compile"),
        ),
        recommended_next_step="Inspect verifier stdout and changed files for syntax or compilation failures.",
    ),
    Rule(
        category="dependency_or_import_error",
        confidence="high",
        patterns=(
            signal("ModuleNotFoundError", r"\bModuleNotFoundError\b"),
            signal("ImportError", r"\bImportError\b"),
            signal("No module named", r"No module named"),
            signal("cannot import name", r"cannot import name"),
            signal("package not found", r"package .*not found"),
        ),
        recommended_next_step="Check whether the solution introduced an unavailable dependency or wrong import path.",
    ),
    Rule(
        category="wrong_file_or_path",
        confidence="high",
        patterns=(
            signal("No such file or directory", r"No such file or directory"),
            signal("FileNotFoundError", r"\bFileNotFoundError\b"),
            signal("path does not exist", r"path .*does not exist"),
            signal("expected file not found", r"expected file .*not found"),
            signal("wrong file", r"wrong file"),
        ),
        recommended_next_step="Verify that the model edited the expected file path and produced required files.",
    ),
    Rule(
        category="timeout_inside_verifier",
        confidence="high",
        patterns=(
            signal("verifier timed out", r"verifier .*timed out"),
            signal("timeout in verifier", r"timeout in verifier"),
            signal("pytest timeout", r"pytest .*timeout"),
            signal("command timed out", r"command timed out"),
            signal("timeout expired", r"timeout expired"),
            signal("deadline exceeded", r"deadline exceeded"),
        ),
        recommended_next_step="Inspect verifier stdout/logs to determine whether tests or the submitted solution hung.",
    ),
    Rule(
        category="runtime_exception_in_solution",
        confidence="high",
        patterns=(
            signal("Traceback", r"Traceback \(most recent call last\)"),
            signal("RuntimeError", r"\bRuntimeError\b"),
            signal("ValueError", r"\bValueError\b"),
            signal("TypeError", r"\bTypeError\b"),
            signal("KeyError", r"\bKeyError\b"),
            signal("IndexError", r"\bIndexError\b"),
            signal("AttributeError", r"\bAttributeError\b"),
            signal("NameError", r"\bNameError\b"),
            signal("ZeroDivisionError", r"\bZeroDivisionError\b"),
        ),
        recommended_next_step="Review the runtime traceback and changed code to identify the failing execution path.",
    ),
    Rule(
        category="test_assertion_failure",
        confidence="high",
        patterns=(
            signal("AssertionError", r"\bAssertionError\b"),
            signal("pytest failure marker", r"[.F]*F[.F]* \[100%\]"),
            signal("assert comparison", r"\bassert\b.{0,120}(?:==|!=|<=|>=| is )"),
            signal("FAILURES", r"=+ FAILURES =+"),
            signal("failed pytest test case", r"\bFAILED\s+\S+::test_[A-Za-z0-9_]+"),
        ),
        recommended_next_step="Inspect verifier stdout/CTRF to identify the expected behavior that still failed.",
    ),
    Rule(
        category="missing_or_wrong_output",
        confidence="medium",
        patterns=(
            signal("expected actual mismatch", r"expected.{0,120}actual"),
            signal("actual expected mismatch", r"actual.{0,120}expected"),
            signal("output mismatch", r"output (?:mismatch|differs|did not match)"),
            signal("wrong answer", r"wrong answer"),
            signal("incorrect output", r"incorrect output"),
            signal("missing output", r"missing output"),
            signal("expected output", r"expected output"),
        ),
        recommended_next_step="Compare expected and actual outputs in verifier artifacts and inspect solution behavior.",
    ),
    Rule(
        category="no_meaningful_code_change",
        confidence="medium",
        patterns=(
            signal("no code changes", r"no (?:meaningful )?(?:code )?changes?"),
            signal("did not modify", r"did not modify"),
            signal("no files modified", r"no files? (?:were )?modified"),
            signal("unchanged solution", r"solution .*unchanged"),
            signal("unchanged from starting", r"unchanged from starting"),
        ),
        recommended_next_step="Inspect transcript and trajectory to confirm whether the model left the task effectively untouched.",
    ),
    Rule(
        category="partial_solution",
        confidence="medium",
        patterns=(
            signal("partial solution", r"partial solution"),
            signal("incomplete", r"\bincomplete\b"),
            signal("not implemented", r"not implemented"),
            signal("NotImplementedError", r"\bNotImplementedError\b"),
            signal("TODO", r"\bTODO\b"),
            signal("placeholder", r"\bplaceholder\b"),
        ),
        recommended_next_step="Inspect the diff/transcript to determine which requirements were attempted and which remain missing.",
    ),
)

ASSERTION_SECONDARY_RULES = (
    Rule(
        category="performance_threshold_failure",
        confidence="high",
        patterns=(
            signal(
                "test_compare_golden_vs_solution_runtime",
                r"\btest_compare_golden_vs_solution_runtime\b",
            ),
            signal("performance threshold", r"\b(?:runtime|latency|elapsed)[^\n]{0,100}\bthreshold\b"),
        ),
        recommended_next_step="Compare candidate runtime against the verifier threshold and golden implementation.",
    ),
    Rule(
        category="numerical_or_data_mismatch",
        confidence="high",
        patterns=(
            signal("test_data_matches", r"\btest_data_matches\b"),
            signal("numerical comparison", r"\b(?:allclose|array_equal|assert_array|assert_frame_equal)\b"),
        ),
        recommended_next_step="Compare the candidate data or numerical values with the expected result.",
    ),
    Rule(
        category="missing_expected_file_or_content",
        confidence="high",
        patterns=(
            signal("test_hello_html_exists", r"\btest_hello_html_exists\b"),
            signal(
                "missing expected file/content",
                r"(?:expected|required)[^\n]{0,100}(?:file|path|content)[^\n]{0,80}"
                r"(?:missing|not found|does not exist|absent)",
            ),
        ),
        recommended_next_step="Verify the required file path and expected file content.",
    ),
    Rule(
        category="behavior_mismatch",
        confidence="high",
        patterns=(
            signal("test_fibonacci_polyglot", r"\btest_fibonacci_polyglot\b"),
            signal(
                "test_tasks_cancel_above_max_concurrent",
                r"\btest_tasks_cancel_above_max_concurrent\b",
            ),
            signal("behavior mismatch", r"\bbehavior (?:mismatch|differs|incorrect)\b"),
        ),
        recommended_next_step="Inspect the candidate behavior exercised by the failed test case.",
    ),
    Rule(
        category="output_mismatch",
        confidence="high",
        patterns=(
            signal("test_password_match", r"\btest_password_match\b"),
            signal("asserted value mismatch", r"\bassert\b[^\n]{0,160}(?:==|!=| is )"),
            signal("expected/actual mismatch", r"\bexpected\b[^\n]{0,160}\bactual\b"),
        ),
        recommended_next_step="Compare the asserted output with the expected value.",
    ),
)


def read_trial_evidence(
    path: Path,
    *,
    focus_arms: Sequence[str],
    focus_tasks: Sequence[str],
    limit: int | None,
) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"Trial evidence file not found: {path}")
    arm_filter = set(focus_arms)
    task_filter = set(focus_tasks)
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("quality_flag") != NORMAL_FAILURE_FLAG:
                continue
            if arm_filter and row.get("arm_id") not in arm_filter:
                continue
            if task_filter and row.get("task_id") not in task_filter:
                continue
            rows.append(dict(row))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def matches_for_rules(
    evidence_sources: Sequence[EvidenceSource],
    *,
    rules: Sequence[Rule],
    category_priority: dict[str, int],
) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    for source in evidence_sources:
        for rule in rules:
            earliest = None
            earliest_signal = None
            for pattern in rule.patterns:
                match = pattern.pattern.search(source.text)
                if match and (
                    earliest is None
                    or (pattern.direct and earliest_signal is not None and not earliest_signal.direct)
                    or (
                        earliest_signal is not None
                        and pattern.direct == earliest_signal.direct
                        and match.start() < earliest.start()
                    )
                ):
                    earliest = match
                    earliest_signal = pattern
            if earliest and earliest_signal:
                matches.append(
                    RuleMatch(
                        category=rule.category,
                        confidence=adjusted_confidence(rule.confidence, direct=earliest_signal.direct),
                        recommended_next_step=rule.recommended_next_step,
                        start=earliest.start(),
                        end=earliest.end(),
                        matched_signal=redact_secrets(" ".join(earliest.group(0).replace("\x00", " ").split()))[:120],
                        matched_pattern=earliest_signal.pattern.pattern,
                        direct=earliest_signal.direct,
                        evidence_artifact_type=source.artifact_type,
                        evidence_artifact_id=source.artifact_id,
                        evidence_source_rank=source.source_rank,
                        source_text=source.text,
                    )
                )
    return sorted(
        matches,
        key=lambda match: (
            not match.direct,
            category_priority.get(match.category, 99),
            -CONFIDENCE_RANK[match.confidence],
            match.evidence_source_rank,
            match.start,
            match.category,
        ),
    )


def rule_matches(evidence_sources: Sequence[EvidenceSource]) -> list[RuleMatch]:
    return matches_for_rules(
        evidence_sources,
        rules=RULES,
        category_priority=CATEGORY_PRIORITY,
    )


def assertion_secondary_matches(evidence_sources: Sequence[EvidenceSource]) -> list[RuleMatch]:
    return matches_for_rules(
        evidence_sources,
        rules=ASSERTION_SECONDARY_RULES,
        category_priority=ASSERTION_SECONDARY_PRIORITY,
    )


def classify_normal_failure(
    *,
    target_row: dict[str, Any],
    evidence_by_type: dict[str, str] | Sequence[EvidenceSource],
    fetch_notes: Sequence[str] = (),
) -> NormalFailureClassification:
    evidence_sources = normalize_evidence_sources(evidence_by_type)
    evidence_text = "\n".join(source.text for source in evidence_sources if source.text)
    matches = rule_matches(evidence_sources)
    notes = list(fetch_notes)

    if not matches:
        notes.append("no deterministic rule matched")
        return NormalFailureClassification(
            primary_category="unknown_normal_failure",
            secondary_category="",
            confidence="low",
            needs_manual_review=True,
            matched_signal="",
            matched_pattern="",
            evidence_artifact_type="",
            evidence_artifact_id="",
            evidence_excerpt=safe_excerpt(evidence_text),
            classification_reason="No deterministic failure signal matched; manual review required.",
            recommended_next_step="Manually inspect verifier stdout, CTRF, result, log, and transcript artifacts.",
            notes="; ".join(note for note in notes if note),
        )

    primary = matches[0]
    secondary = None
    secondary_category = ""
    ambiguous_secondary = False
    if primary.category == "test_assertion_failure":
        assertion_matches = assertion_secondary_matches(evidence_sources)
        if assertion_matches:
            secondary = assertion_matches[0]
            secondary_category = secondary.category
            ambiguous_secondary = not secondary.direct
        else:
            secondary_category = "unknown_assertion_failure"
            ambiguous_secondary = True
    else:
        secondary = next((match for match in matches[1:] if match.category != primary.category), None)
        secondary_category = secondary.category if secondary else ""

    excerpt = safe_excerpt(primary.source_text, start=primary.start, end=primary.end)
    direct_signal_visible = primary.direct and excerpt_contains_signal(excerpt, primary.matched_signal)
    confidence = primary.confidence
    if confidence == "high" and not direct_signal_visible:
        confidence = "medium"
    if primary.category == "test_assertion_failure" and ambiguous_secondary and confidence == "high":
        confidence = "medium"
    needs_manual_review = confidence == "low" or not direct_signal_visible or ambiguous_secondary
    notes.append(f"matched_rule={primary.matched_pattern}")
    notes.append(f"direct_signal_visible={str(direct_signal_visible).lower()}")
    if secondary:
        notes.append(f"secondary_rule={secondary.matched_pattern}")
        notes.append(f"secondary_signal={secondary.matched_signal}")
    elif primary.category == "test_assertion_failure":
        notes.append("secondary_rule=no assertion subtype signal matched")

    classification_reason = (
        f"{confidence} confidence from "
        f"{'direct visible' if direct_signal_visible else 'indirect or non-visible'} "
        f"primary signal `{primary.matched_signal}` in "
        f"{primary.evidence_artifact_type or 'unknown'} artifact"
    )
    if secondary:
        classification_reason += (
            f"; secondary `{secondary.category}` from "
            f"{'direct' if secondary.direct else 'indirect'} signal `{secondary.matched_signal}`"
        )
    elif secondary_category:
        classification_reason += f"; secondary `{secondary_category}` requires manual review"

    return NormalFailureClassification(
        primary_category=primary.category,
        secondary_category=secondary_category,
        confidence=confidence,
        needs_manual_review=needs_manual_review,
        matched_signal=primary.matched_signal,
        matched_pattern=primary.matched_pattern,
        evidence_artifact_type=primary.evidence_artifact_type,
        evidence_artifact_id=primary.evidence_artifact_id,
        evidence_excerpt=excerpt,
        classification_reason=classification_reason,
        recommended_next_step=primary.recommended_next_step,
        notes="; ".join(note for note in notes if note),
    )


def fetch_related_artifacts(trial_ids: Sequence[str]) -> tuple[dict[str, list[dict[str, Any]]], str | None]:
    if not trial_ids:
        return {}, None
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        return {}, "SUPABASE_DB_URL unavailable; related artifacts were skipped"
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        return {}, "psycopg unavailable; related artifacts were skipped"

    sql = """
        select
          trial_id::text,
          id::text as artifact_id,
          artifact_type,
          r2_uri,
          size_bytes::int,
          created_at
        from benchmark.benchmark_artifacts
        where trial_id::text = any(%s)
          and artifact_type = any(%s)
          and r2_uri is not null
        order by trial_id::text, created_at nulls last, id
    """
    try:
        with psycopg.connect(db_url, row_factory=dict_row, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (list(trial_ids), list(RELATED_ARTIFACT_TYPES)))
                rows = list(cur.fetchall())
    except Exception as exc:  # pragma: no cover - live database availability only
        return {}, f"related artifact lookup failed: {type(exc).__name__}"

    grouped_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped_rows[row["trial_id"]].append(dict(row))

    grouped: dict[str, list[dict[str, Any]]] = {}
    for trial_id, trial_rows in grouped_rows.items():
        seen_types: set[str] = set()
        ordered_rows = sorted(
            trial_rows,
            key=lambda row: (
                ARTIFACT_TYPE_RANK.get(str(row.get("artifact_type") or ""), 99),
                str(row.get("created_at") or ""),
                str(row.get("artifact_id") or ""),
            ),
        )
        grouped[trial_id] = []
        for row in ordered_rows:
            artifact_type = str(row.get("artifact_type") or "")
            if artifact_type in seen_types:
                continue
            seen_types.add(artifact_type)
            grouped[trial_id].append(row)
    return grouped, None


def evidence_for_trial(
    *,
    r2: R2Client,
    related_artifacts: Sequence[dict[str, Any]],
    artifact_types: Sequence[str],
    start_rank: int = 0,
) -> tuple[list[EvidenceSource], list[str]]:
    evidence: list[EvidenceSource] = []
    notes: list[str] = []
    artifact_type_filter = set(artifact_types)
    for rank, artifact in enumerate(related_artifacts, start=start_rank):
        artifact_type = str(artifact.get("artifact_type") or "")
        if not artifact_type or artifact_type not in artifact_type_filter:
            continue
        text, error = r2.fetch_text(str(artifact.get("r2_uri") or ""), max_bytes=MAX_NORMAL_ARTIFACT_BYTES)
        if text is not None:
            evidence.append(
                EvidenceSource(
                    artifact_type=artifact_type,
                    artifact_id=str(artifact.get("artifact_id") or ""),
                    source_rank=rank,
                    text=text,
                )
            )
        elif error:
            notes.append(f"{artifact_type}_fetch={error}")
    return evidence, notes


def classification_row(
    *,
    target: dict[str, str],
    classification: NormalFailureClassification,
    evidence_types: Sequence[str],
    base_url: str,
) -> dict[str, Any]:
    trial_path = target.get("trial_dashboard_path") or f"/trials/{target.get('trial_id', '')}"
    notes = [classification.notes]
    if evidence_types:
        notes.append(f"evidence_sources={','.join(evidence_types)}")
    return {
        "suite_id": target.get("suite_id", ""),
        "arm_id": target.get("arm_id", ""),
        "run_label": target.get("run_label", ""),
        "task_id": target.get("task_id", ""),
        "attempt_index": target.get("attempt_index", ""),
        "trial_id": target.get("trial_id", ""),
        "reward": target.get("reward", ""),
        "runtime_seconds": target.get("runtime_seconds", ""),
        "primary_category": classification.primary_category,
        "secondary_category": classification.secondary_category,
        "confidence": classification.confidence,
        "needs_manual_review": classification.needs_manual_review,
        "matched_signal": classification.matched_signal,
        "matched_pattern": classification.matched_pattern,
        "evidence_artifact_type": classification.evidence_artifact_type,
        "evidence_artifact_id": classification.evidence_artifact_id,
        "evidence_excerpt": classification.evidence_excerpt,
        "classification_reason": classification.classification_reason,
        "trial_dashboard_path": dashboard_url(base_url, trial_path),
        "recommended_next_step": classification.recommended_next_step,
        "notes": "; ".join(note for note in notes if note),
    }


def build_summary_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("arm_id") or ""), str(row.get("primary_category") or ""))].append(row)

    summary: list[dict[str, Any]] = []
    for (arm_id, category), group in sorted(grouped.items()):
        confidence_floor_rank = min(CONFIDENCE_RANK[str(row.get("confidence") or "low")] for row in group)
        representative_tasks = sorted({str(row.get("task_id") or "") for row in group if row.get("task_id")})[:5]
        representative_signals: list[str] = []
        for row in group:
            signal_text = compact_signal(row.get("matched_signal"))
            if signal_text and signal_text not in representative_signals:
                representative_signals.append(signal_text)
            if len(representative_signals) >= 5:
                break
        summary.append(
            {
                "arm_id": arm_id,
                "primary_category": category,
                "count": len(group),
                "representative_tasks": ",".join(representative_tasks),
                "representative_matched_signals": ",".join(representative_signals),
                "needs_manual_review_count": sum(
                    1 for row in group if bool_from_text(row.get("needs_manual_review"))
                ),
                "confidence_floor": CONFIDENCE_BY_RANK[confidence_floor_rank],
            }
        )
    return summary


def generated_paths(output_dir: Path, datestamp: str) -> tuple[Path, Path]:
    return (
        output_dir / f"phase3_normal_failure_classification_{datestamp}.tsv",
        output_dir / f"phase3_normal_failure_classification_summary_{datestamp}.tsv",
    )


def compact_signal(value: Any, *, limit: int = 72) -> str:
    cleaned = " ".join(str(value or "").replace("\\n", " ").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(limit - 3, 0)] + "..."


def category_counts(rows: Sequence[dict[str, Any]]) -> list[tuple[str, int, int, str, str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("primary_category") or "")].append(row)
    result: list[tuple[str, int, int, str, str]] = []
    for category, group in grouped.items():
        confidence_floor_rank = min(CONFIDENCE_RANK[str(row.get("confidence") or "low")] for row in group)
        signals: list[str] = []
        for row in group:
            signal_text = compact_signal(row.get("matched_signal"))
            if signal_text and signal_text not in signals:
                signals.append(signal_text)
            if len(signals) >= 3:
                break
        result.append(
            (
                category,
                len(group),
                sum(1 for row in group if bool_from_text(row.get("needs_manual_review"))),
                CONFIDENCE_BY_RANK[confidence_floor_rank],
                ", ".join(signals),
            )
        )
    return sorted(result, key=lambda item: (-item[1], item[0]))


def exception_comparison(output_dir: Path, datestamp: str) -> str:
    path = output_dir / f"phase3_exception_classification_summary_{datestamp}.tsv"
    if not path.exists():
        return f"Exception classification summary was not found at `{path.as_posix()}`."
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    total = sum(int(row.get("count") or 0) for row in rows)
    categories = sorted({row.get("primary_category", "") for row in rows if row.get("primary_category")})
    category_text = ", ".join(f"`{category}`" for category in categories) or "none"
    return (
        f"Exception classifications for the same date cover {total} exception rows across "
        f"{category_text}. Normal-failure classification covers verifier failures that did not raise "
        "a harness exception and should be reviewed as solution/verifier evidence, not scoring changes."
    )


def classification_section(
    *,
    classification_path: Path,
    summary_path: Path,
    output_dir: Path,
    datestamp: str,
    rows: Sequence[dict[str, Any]],
    summary_rows: Sequence[dict[str, Any]],
) -> str:
    category_table = markdown_table(
        ["Primary category", "Count", "Manual-review flagged", "Confidence floor", "Matched signals"],
        category_counts(rows),
    )
    arm_table = markdown_table(
        ["Arm", "Category", "Count", "Manual review", "Confidence floor", "Matched signals"],
        [
            (
                row["arm_id"],
                row["primary_category"],
                row["count"],
                row["needs_manual_review_count"],
                row["confidence_floor"],
                row["representative_matched_signals"],
            )
            for row in summary_rows
        ],
    )
    sonnet_rows = [row for row in rows if row.get("arm_id") == "router-anthropic-sonnet"]
    gemini_flash_rows = [row for row in rows if row.get("arm_id") == "router-gemini-flash"]
    sonnet_table = markdown_table(
        ["Primary category", "Count", "Manual-review flagged", "Confidence floor", "Matched signals"],
        category_counts(sonnet_rows),
    )
    gemini_table = markdown_table(
        ["Primary category", "Count", "Manual-review flagged", "Confidence floor", "Matched signals"],
        category_counts(gemini_flash_rows),
    )
    manual_count = sum(1 for row in rows if bool_from_text(row.get("needs_manual_review")))
    classification_rel = classification_path.as_posix()
    summary_rel = summary_path.as_posix()

    return f"""## Automated First-Pass Normal Failure Classification

Source files:

- `{classification_rel}`
- `{summary_rel}`

This is deterministic, rule-based, evidence-assisted first-pass classification from verifier stdout, CTRF, reward, result, log, transcript, and trajectory artifacts when available. It is not final human judgment and does not change scoring semantics.

Summary by category:

{category_table}

Summary by arm and category:

{arm_table}

Rows marked `needs_manual_review`: {manual_count} of {len(rows)}.

Comparison against exception classifications:

{exception_comparison(output_dir, datestamp)}

Sonnet normal failures:

{sonnet_table}

Gemini Flash normal failures:

{gemini_table}
"""


def upsert_markdown_section(report_path: Path, section: str) -> None:
    header = "## Automated First-Pass Normal Failure Classification"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists():
        text = report_path.read_text(encoding="utf-8")
    else:
        text = f"# Phase 3 Artifact Qualitative Review {utc_datestamp()}\n"

    if header in text:
        start = text.index(header)
        next_header = text.find("\n## ", start + len(header))
        if next_header == -1:
            updated = text[:start].rstrip() + "\n\n" + section.rstrip() + "\n"
        else:
            updated = text[:start].rstrip() + "\n\n" + section.rstrip() + "\n\n" + text[next_header + 1 :].lstrip()
    else:
        marker = "\n## Open Questions and Recommended Actions"
        if marker in text:
            index = text.index(marker)
            updated = text[:index].rstrip() + "\n\n" + section.rstrip() + "\n" + text[index:]
        else:
            updated = text.rstrip() + "\n\n" + section.rstrip() + "\n"
    report_path.write_text(updated, encoding="utf-8")


def classify_targets(
    *,
    targets: Sequence[dict[str, str]],
    r2: R2Client,
    related_lookup: dict[str, list[dict[str, Any]]],
    related_lookup_note: str | None,
    base_url: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, target in enumerate(targets, start=1):
        if index == 1 or index % 25 == 0 or index == len(targets):
            print(f"classifying normal failure {index}/{len(targets)}", file=sys.stderr)
        notes = [related_lookup_note] if related_lookup_note else []
        related_artifacts = related_lookup.get(target.get("trial_id", ""), [])
        evidence, fetch_notes = evidence_for_trial(
            r2=r2,
            related_artifacts=related_artifacts,
            artifact_types=PRIMARY_ARTIFACT_TYPES,
        )
        notes.extend(fetch_notes)
        classification = classify_normal_failure(
            target_row=target,
            evidence_by_type=evidence,
            fetch_notes=notes,
        )
        if classification.needs_manual_review:
            fallback_evidence, fallback_notes = evidence_for_trial(
                r2=r2,
                related_artifacts=related_artifacts,
                artifact_types=FALLBACK_ARTIFACT_TYPES,
                start_rank=len(evidence),
            )
            evidence.extend(fallback_evidence)
            notes.extend(fallback_notes)
            classification = classify_normal_failure(
                target_row=target,
                evidence_by_type=evidence,
                fetch_notes=notes,
            )
        else:
            skipped = [
                str(artifact.get("artifact_type") or "")
                for artifact in related_artifacts
                if str(artifact.get("artifact_type") or "") in FALLBACK_ARTIFACT_TYPES
            ]
            if skipped:
                classification = NormalFailureClassification(
                    primary_category=classification.primary_category,
                    secondary_category=classification.secondary_category,
                    confidence=classification.confidence,
                    needs_manual_review=classification.needs_manual_review,
                    matched_signal=classification.matched_signal,
                    matched_pattern=classification.matched_pattern,
                    evidence_artifact_type=classification.evidence_artifact_type,
                    evidence_artifact_id=classification.evidence_artifact_id,
                    evidence_excerpt=classification.evidence_excerpt,
                    classification_reason=classification.classification_reason,
                    recommended_next_step=classification.recommended_next_step,
                    notes=(
                        f"{classification.notes}; "
                        f"deferred_low_priority_artifacts_after_confident_match={','.join(skipped)}"
                    ),
                )
        rows.append(
            classification_row(
                target=target,
                classification=classification,
                evidence_types=sorted({source.artifact_type for source in evidence}),
                base_url=base_url,
            )
        )
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial-evidence", type=Path, default=DEFAULT_TRIAL_EVIDENCE)
    parser.add_argument("--date", default=utc_datestamp(), help="UTC datestamp in YYYYMMDD format.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--docs-report", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--focus-arm", action="append", default=[])
    parser.add_argument("--focus-task", action="append", default=[])
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--include-related-artifacts", action=argparse.BooleanOptionalAction, default=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    docs_report = args.docs_report or Path(f"docs/reports/phase3/PHASE3_ARTIFACT_QUALITATIVE_REVIEW_{args.date}.md")
    targets = read_trial_evidence(
        args.trial_evidence,
        focus_arms=args.focus_arm,
        focus_tasks=args.focus_task,
        limit=args.limit,
    )
    related_lookup: dict[str, list[dict[str, Any]]] = {}
    related_note = None
    r2 = R2Client.from_env()
    if args.include_related_artifacts:
        related_lookup, related_note = fetch_related_artifacts([row.get("trial_id", "") for row in targets])

    rows = classify_targets(
        targets=targets,
        r2=r2,
        related_lookup=related_lookup,
        related_lookup_note=related_note,
        base_url=args.base_url,
    )
    summary_rows = build_summary_rows(rows)
    classification_path, summary_path = generated_paths(args.output_dir, args.date)
    write_tsv(classification_path, rows, CLASSIFICATION_HEADERS)
    write_tsv(summary_path, summary_rows, SUMMARY_HEADERS)
    upsert_markdown_section(
        docs_report,
        classification_section(
            classification_path=classification_path,
            summary_path=summary_path,
            output_dir=args.output_dir,
            datestamp=args.date,
            rows=rows,
            summary_rows=summary_rows,
        ),
    )
    print(classification_path)
    print(summary_path)
    print(docs_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
