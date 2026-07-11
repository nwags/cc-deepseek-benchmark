#!/usr/bin/env python3
"""Classify Phase 3 exception artifacts with deterministic first-pass rules."""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_phase3_qualitative_audit import utc_datestamp, write_tsv


DEFAULT_TARGETS = Path("results/phase3/reporting/phase3_exception_review_targets_20260706.tsv")
DEFAULT_OUTPUT_DIR = Path("results/phase3/reporting")
DEFAULT_BASE_URL = "http://127.0.0.1:3000"
MAX_ARTIFACT_BYTES = 256 * 1024
MAX_EXCERPT_CHARS = 300

RELATED_ARTIFACT_TYPES = (
    "result",
    "log",
    "agent_transcript",
    "trajectory",
    "verifier_stdout",
    "verifier_ctrf",
    "verifier_reward",
)

CLASSIFICATION_HEADERS = [
    "suite_id",
    "arm_id",
    "run_label",
    "task_id",
    "attempt_index",
    "trial_id",
    "exception_artifact_id",
    "exception_artifact_dashboard_path",
    "exception_type",
    "missing_cost",
    "reward",
    "runtime_seconds",
    "runtime_band",
    "primary_category",
    "secondary_category",
    "confidence",
    "needs_manual_review",
    "matched_signal",
    "matched_pattern",
    "evidence_artifact_type",
    "evidence_artifact_id",
    "evidence_source_rank",
    "classification_reason",
    "evidence_source_artifact_types",
    "evidence_excerpt",
    "recommended_next_step",
    "notes",
]

SUMMARY_HEADERS = [
    "arm_id",
    "primary_category",
    "runtime_band",
    "count",
    "missing_cost_count",
    "needs_manual_review_count",
    "representative_tasks",
    "representative_matched_signals",
    "confidence_floor",
]

CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
CONFIDENCE_BY_RANK = {0: "low", 1: "medium", 2: "high"}


@dataclass(frozen=True)
class SignalPattern:
    label: str
    pattern: re.Pattern[str]
    direct: bool = True


@dataclass(frozen=True)
class Rule:
    category: str
    confidence: str
    patterns: tuple[SignalPattern, ...]
    recommended_next_step: str


@dataclass(frozen=True)
class EvidenceSource:
    artifact_type: str
    artifact_id: str
    source_rank: int
    text: str


@dataclass(frozen=True)
class RuleMatch:
    category: str
    confidence: str
    recommended_next_step: str
    start: int
    end: int
    matched_signal: str
    matched_pattern: str
    direct: bool
    evidence_artifact_type: str
    evidence_artifact_id: str
    evidence_source_rank: int
    source_text: str


def regex(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE | re.MULTILINE)


def signal(label: str, pattern: str, *, direct: bool = True) -> SignalPattern:
    return SignalPattern(label=label, pattern=regex(pattern), direct=direct)


CATEGORY_PRIORITY = {
    "agent_timeout": 0,
    "nonzero_agent_exit": 1,
    "connection_refused_or_service_unavailable": 2,
    "context_length_or_payload_error": 3,
    "provider_rate_limit": 4,
    "auth_or_permission_error": 5,
    "provider_overloaded_or_unavailable": 6,
    "router_litellm_error": 7,
    "max_turns_or_budget_exhaustion": 8,
    "task_runtime_timeout": 9,
    "verifier_or_test_failure_exception": 10,
    "model_loop_or_stall": 11,
    "harness_infrastructure_error": 12,
}


@dataclass(frozen=True)
class Classification:
    primary_category: str
    secondary_category: str
    confidence: str
    needs_manual_review: bool
    matched_signal: str
    matched_pattern: str
    evidence_artifact_type: str
    evidence_artifact_id: str
    evidence_source_rank: int | str
    classification_reason: str
    evidence_excerpt: str
    recommended_next_step: str
    notes: str


RULES = (
    Rule(
        category="agent_timeout",
        confidence="high",
        patterns=(
            signal("AgentTimeoutError", r"\bAgentTimeoutError\b"),
            signal("agent timed out", r"\bagent timed out\b"),
            signal("agent timeout", r"\bagent timeout\b"),
            signal("timeout waiting for agent", r"timeout waiting for agent"),
        ),
        recommended_next_step="Inspect agent transcript and runtime logs for stalled command or provider wait.",
    ),
    Rule(
        category="nonzero_agent_exit",
        confidence="high",
        patterns=(
            signal("NonZeroAgentExitCodeError", r"\bNonZeroAgentExitCodeError\b"),
            signal("non-zero agent exit", r"non[- ]?zero agent exit"),
            signal("agent exited with code", r"agent exited with (?:exit )?code [1-9]"),
        ),
        recommended_next_step="Inspect trial log and result artifact for the failing command and exit code.",
    ),
    Rule(
        category="provider_rate_limit",
        confidence="high",
        patterns=(
            signal("HTTP 429", r"(?:http|status(?:_code)?|response(?: status)?|code)\D{0,20}\b429\b"),
            signal("429 rate/quota", r"\b429\b\D{0,80}(?:rate|quota|too many|resource_exhausted)"),
            signal("rate limit", r"rate[_ -]?limit(?:ed|ing)?"),
            signal("RESOURCE_EXHAUSTED", r"\bRESOURCE_EXHAUSTED\b"),
            signal("quota exceeded", r"quota exceeded"),
            signal("too many requests", r"too many requests"),
        ),
        recommended_next_step="Confirm provider quota/rate-limit event and separate provider capacity from model behavior.",
    ),
    Rule(
        category="connection_refused_or_service_unavailable",
        confidence="high",
        patterns=(
            signal("ConnectionRefusedError", r"\bConnectionRefused(?:Error)?\b"),
            signal("connection refused", r"connection refused"),
            signal("ECONNREFUSED", r"\bECONNREFUSED\b"),
            signal("failed to establish connection", r"failed to establish a new connection"),
        ),
        recommended_next_step="Check runner service health, proxy reachability, and local runtime logs.",
    ),
    Rule(
        category="auth_or_permission_error",
        confidence="high",
        patterns=(
            signal("HTTP 401", r"(?:http|status(?:_code)?|response(?: status)?|code)\D{0,20}\b401\b"),
            signal("HTTP 403", r"(?:http|status(?:_code)?|response(?: status)?|code)\D{0,20}\b403\b"),
            signal("401/403 auth context", r"\b(?:401|403)\b\D{0,80}(?:unauthori[sz]ed|forbidden|permission|auth)"),
            signal("unauthorized", r"unauthori[sz]ed"),
            signal("forbidden", r"forbidden"),
            signal("authentication failure", r"authentication (?:failed|required|error)"),
            signal("invalid api key", r"invalid api key"),
            signal("permission denied", r"permission denied"),
            signal("access denied", r"access denied"),
        ),
        recommended_next_step="Check credential scope, provider account access, and runner secret wiring.",
    ),
    Rule(
        category="context_length_or_payload_error",
        confidence="high",
        patterns=(
            signal("context length", r"context length"),
            signal("context window", r"context window"),
            signal("maximum context", r"maximum context"),
            signal("payload too large", r"payload too large"),
            signal("HTTP 413", r"(?:http|status(?:_code)?|response(?: status)?|code)\D{0,20}\b413\b"),
            signal("input too long", r"input too long"),
            signal("token limit", r"token limit"),
        ),
        recommended_next_step="Inspect prompt/artifact size and provider context-window handling.",
    ),
    Rule(
        category="provider_overloaded_or_unavailable",
        confidence="medium",
        patterns=(
            signal("HTTP 5xx", r"(?:http|status(?:_code)?|response(?: status)?|code)\D{0,20}\b50[0234]\b"),
            signal("overloaded", r"overload(?:ed)?"),
            signal("temporarily unavailable", r"temporarily unavailable"),
            signal("service unavailable", r"service unavailable"),
            signal("bad gateway", r"bad gateway"),
            signal("gateway timeout", r"gateway timeout"),
            signal("upstream error", r"upstream .*error", direct=False),
        ),
        recommended_next_step="Confirm provider or upstream outage signal against logs and retry behavior.",
    ),
    Rule(
        category="router_litellm_error",
        confidence="medium",
        patterns=(
            signal("LiteLLM", r"\bLiteLLM\b"),
            signal("LiteLLM exception", r"litellmexception"),
            signal("router error", r"router .*error", direct=False),
            signal("gateway router", r"gateway .*router", direct=False),
        ),
        recommended_next_step="Inspect router/LiteLLM logs and model routing metadata for the same time window.",
    ),
    Rule(
        category="max_turns_or_budget_exhaustion",
        confidence="medium",
        patterns=(
            signal("max turns", r"max(?:imum)? turns"),
            signal("max_turns", r"max_turns"),
            signal("turn budget", r"turn budget"),
            signal("budget exhausted", r"budget exhausted"),
            signal("max iterations", r"max(?:imum)? iterations"),
            signal("iteration limit", r"iteration limit"),
        ),
        recommended_next_step="Inspect transcript for progress, repeated actions, and run-plan exhaustion.",
    ),
    Rule(
        category="task_runtime_timeout",
        confidence="medium",
        patterns=(
            signal("task timed out", r"task timed out"),
            signal("runtime timeout", r"runtime timeout"),
            signal("deadline exceeded", r"deadline exceeded"),
            signal("command timed out", r"command timed out"),
            signal("timeout expired", r"timeout expired"),
            signal("pytest timeout", r"pytest .*timeout"),
        ),
        recommended_next_step="Check whether the task, verifier, or shell command exceeded its runtime limit.",
    ),
    Rule(
        category="verifier_or_test_failure_exception",
        confidence="medium",
        patterns=(
            signal("verifier", r"\bverifier\b", direct=False),
            signal("CTRF", r"\bctrf\b", direct=False),
            signal("test stdout", r"test-stdout", direct=False),
            signal("CalledProcessError", r"\bCalledProcessError\b"),
            signal("pytest", r"\bpytest\b", direct=False),
            signal("assertion error", r"assertion(?:error)?"),
        ),
        recommended_next_step="Inspect verifier stdout, CTRF, and result artifacts to separate test failure from harness exception.",
    ),
    Rule(
        category="model_loop_or_stall",
        confidence="medium",
        patterns=(
            signal("looping", r"\bloop(?:ing)?\b"),
            signal("stalled", r"\bstall(?:ed|ing)?\b"),
            signal("no progress", r"no progress"),
            signal("repeated command/action", r"repeat(?:ed|ing) (?:command|action|response)"),
        ),
        recommended_next_step="Inspect transcript for repeated actions or lack of task progress.",
    ),
    Rule(
        category="harness_infrastructure_error",
        confidence="medium",
        patterns=(
            signal("docker", r"\bdocker\b"),
            signal("container", r"\bcontainer\b", direct=False),
            signal("no space left", r"no space left"),
            signal("filesystem", r"filesystem", direct=False),
            signal("harbor", r"\bharbor\b", direct=False),
            signal("terminal-bench", r"terminal-bench", direct=False),
        ),
        recommended_next_step="Inspect runner host, container, and Terminal-Bench harness logs.",
    ),
)

SECRET_REDACTIONS = (
    (regex(r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}"), "Bearer [REDACTED]"),
    (regex(r"\b(?:sk|xai)-[A-Za-z0-9_-]{12,}\b"), "[REDACTED_API_KEY]"),
    (regex(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), "[REDACTED_ACCESS_KEY]"),
    (regex(r"\bAIza[A-Za-z0-9_-]{20,}\b"), "[REDACTED_API_KEY]"),
    (regex(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED_TOKEN]"),
    (
        regex(
            r"['\"]?(?:api[_-]?key|access[_-]?token|auth[_-]?token|token|secret|password)['\"]?"
            r"\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{12,}"
        ),
        "[REDACTED_SECRET]",
    ),
)


def parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def runtime_band(runtime_seconds: Any) -> str:
    runtime = parse_decimal(runtime_seconds)
    if runtime is None:
        return "unknown_runtime"
    if runtime < Decimal("90"):
        return "fast_exception_under_90s"
    if runtime <= Decimal("1200"):
        return "mid_exception_90_to_1200s"
    return "long_exception_over_1200s"


def normalize_whitespace(value: str) -> str:
    return " ".join(value.replace("\x00", " ").split())


def redact_secrets(value: str) -> str:
    redacted = value
    for pattern, replacement in SECRET_REDACTIONS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def safe_excerpt(text: str, *, start: int = 0, end: int = 0, limit: int = MAX_EXCERPT_CHARS) -> str:
    if not text:
        return ""
    radius = max(limit // 2, 1)
    if end > start:
        left = max(0, start - radius)
        right = min(len(text), end + radius)
        snippet = text[left:right]
    else:
        snippet = text[:limit]
    cleaned = redact_secrets(normalize_whitespace(snippet))
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(limit - 3, 0)] + "..."


def excerpt_contains_signal(excerpt: str, matched_signal: str) -> bool:
    if not excerpt or not matched_signal:
        return False
    visible_signal = redact_secrets(normalize_whitespace(matched_signal))
    return bool(visible_signal) and visible_signal.casefold() in excerpt.casefold()


def adjusted_confidence(base_confidence: str, *, direct: bool) -> str:
    if direct:
        return base_confidence
    if base_confidence == "high":
        return "medium"
    return base_confidence


def normalize_evidence_sources(evidence_by_type: dict[str, str] | Sequence[EvidenceSource]) -> list[EvidenceSource]:
    if not isinstance(evidence_by_type, dict):
        return list(evidence_by_type)

    ordered: list[tuple[str, str]] = []
    if "exception" in evidence_by_type:
        ordered.append(("exception", evidence_by_type["exception"]))
    ordered.extend(
        (artifact_type, text)
        for artifact_type, text in evidence_by_type.items()
        if artifact_type != "exception"
    )
    return [
        EvidenceSource(
            artifact_type=artifact_type,
            artifact_id="",
            source_rank=index,
            text=text,
        )
        for index, (artifact_type, text) in enumerate(ordered)
        if text
    ]


def rule_matches(evidence_sources: Sequence[EvidenceSource]) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    for source in evidence_sources:
        for rule in RULES:
            earliest: re.Match[str] | None = None
            earliest_signal: SignalPattern | None = None
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
                        matched_signal=redact_secrets(normalize_whitespace(earliest.group(0)))[:120],
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
            CATEGORY_PRIORITY.get(match.category, 99),
            -CONFIDENCE_RANK[match.confidence],
            match.evidence_source_rank,
            match.start,
            match.category,
        ),
    )


def classify_exception(
    *,
    target_row: dict[str, Any],
    evidence_by_type: dict[str, str] | Sequence[EvidenceSource],
    fetch_notes: Sequence[str] = (),
) -> Classification:
    evidence_sources = normalize_evidence_sources(evidence_by_type)
    evidence_text = "\n".join(source.text for source in evidence_sources if source.text)
    matches = rule_matches(evidence_sources)
    band = runtime_band(target_row.get("runtime_seconds"))
    runtime_note = f"runtime_band={band}"
    notes = [runtime_note, *fetch_notes]

    if not matches:
        excerpt = safe_excerpt(evidence_text)
        notes.append("no deterministic rule matched")
        return Classification(
            primary_category="unknown_exception",
            secondary_category="",
            confidence="low",
            needs_manual_review=True,
            matched_signal="",
            matched_pattern="",
            evidence_artifact_type="",
            evidence_artifact_id="",
            evidence_source_rank="",
            classification_reason="No deterministic direct signal matched; manual review required.",
            evidence_excerpt=excerpt,
            recommended_next_step="Manually inspect exception, result, transcript, and trial log artifacts.",
            notes="; ".join(note for note in notes if note),
        )

    primary = matches[0]
    secondary = next((match for match in matches[1:] if match.category != primary.category), None)
    excerpt = safe_excerpt(primary.source_text, start=primary.start, end=primary.end)
    direct_signal_visible = primary.direct and excerpt_contains_signal(excerpt, primary.matched_signal)
    confidence = primary.confidence
    if confidence == "high" and not direct_signal_visible:
        confidence = "medium"
    needs_manual_review = confidence == "low" or not direct_signal_visible
    notes.append(f"matched_rule={primary.matched_pattern}")
    notes.append(f"direct_signal_visible={str(direct_signal_visible).lower()}")
    if secondary:
        notes.append(f"secondary_rule={secondary.matched_pattern}")
        notes.append(f"secondary_signal={secondary.matched_signal}")
    classification_reason = (
        f"{confidence} confidence from "
        f"{'direct visible' if direct_signal_visible else 'indirect or non-visible'} "
        f"signal `{primary.matched_signal}` "
        f"in {primary.evidence_artifact_type or 'unknown'} artifact"
    )

    return Classification(
        primary_category=primary.category,
        secondary_category=secondary.category if secondary else "",
        confidence=confidence,
        needs_manual_review=needs_manual_review,
        matched_signal=primary.matched_signal,
        matched_pattern=primary.matched_pattern,
        evidence_artifact_type=primary.evidence_artifact_type,
        evidence_artifact_id=primary.evidence_artifact_id,
        evidence_source_rank=primary.evidence_source_rank,
        classification_reason=classification_reason,
        evidence_excerpt=excerpt,
        recommended_next_step=primary.recommended_next_step,
        notes="; ".join(note for note in notes if note),
    )


def parse_r2_uri(value: str | None) -> tuple[str, str] | None:
    if not value:
        return None
    match = re.match(r"^r2://([^/]+)/(.+)$", value)
    if not match:
        return None
    return match.group(1), match.group(2)


def aws_encode(value: str) -> str:
    return urllib.parse.quote(value, safe="-_.~")


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hmac_bytes(key: bytes | str, value: str) -> bytes:
    if isinstance(key, str):
        key = key.encode("utf-8")
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()


def hmac_hex(key: bytes | str, value: str) -> str:
    if isinstance(key, str):
        key = key.encode("utf-8")
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class R2Config:
    endpoint_url: str
    access_key_id: str
    secret_access_key: str
    region: str


class R2Client:
    def __init__(self, config: R2Config) -> None:
        self.config = config

    @classmethod
    def from_env(cls) -> "R2Client":
        missing = [
            name
            for name in ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")
            if not os.getenv(name)
        ]
        if missing:
            raise SystemExit(f"Missing required R2 environment variable(s): {', '.join(missing)}")
        return cls(
            R2Config(
                endpoint_url=os.environ["R2_ENDPOINT_URL"],
                access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
                region=os.getenv("R2_REGION", "auto"),
            )
        )

    def object_url(self, bucket: str, key: str) -> urllib.parse.ParseResult:
        endpoint = urllib.parse.urlparse(self.config.endpoint_url)
        base_path = endpoint.path.rstrip("/")
        key_path = "/".join(aws_encode(part) for part in key.split("/"))
        path = f"{base_path}/{aws_encode(bucket)}/{key_path}"
        return endpoint._replace(path=path, params="", query="", fragment="")

    def signed_headers(self, *, method: str, parsed_url: urllib.parse.ParseResult, byte_range: str) -> dict[str, str]:
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = amz_date[:8]
        service = "s3"
        credential_scope = f"{date_stamp}/{self.config.region}/{service}/aws4_request"
        host = parsed_url.netloc
        headers = {
            "host": host,
            "range": byte_range,
            "x-amz-content-sha256": "UNSIGNED-PAYLOAD",
            "x-amz-date": amz_date,
        }
        signed_headers = ";".join(sorted(headers))
        canonical_headers = "".join(f"{key}:{headers[key]}\n" for key in sorted(headers))
        canonical_request = "\n".join(
            [
                method,
                parsed_url.path,
                "",
                canonical_headers,
                signed_headers,
                "UNSIGNED-PAYLOAD",
            ]
        )
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                sha256_hex(canonical_request),
            ]
        )
        date_key = hmac_bytes(f"AWS4{self.config.secret_access_key}", date_stamp)
        date_region_key = hmac_bytes(date_key, self.config.region)
        date_region_service_key = hmac_bytes(date_region_key, service)
        signing_key = hmac_bytes(date_region_service_key, "aws4_request")
        signature = hmac_hex(signing_key, string_to_sign)
        authorization = (
            "AWS4-HMAC-SHA256 "
            f"Credential={self.config.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        return {
            "Range": byte_range,
            "x-amz-content-sha256": "UNSIGNED-PAYLOAD",
            "x-amz-date": amz_date,
            "Authorization": authorization,
        }

    def fetch_text(self, r2_uri: str, *, max_bytes: int = MAX_ARTIFACT_BYTES) -> tuple[str | None, str | None]:
        parsed = parse_r2_uri(r2_uri)
        if not parsed:
            return None, "invalid r2_uri"
        bucket, key = parsed
        parsed_url = self.object_url(bucket, key)
        byte_range = f"bytes=0-{max_bytes - 1}"
        headers = self.signed_headers(method="GET", parsed_url=parsed_url, byte_range=byte_range)
        request = urllib.request.Request(urllib.parse.urlunparse(parsed_url), headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read(max_bytes)
        except urllib.error.HTTPError as exc:
            return None, f"r2_http_{exc.code}"
        except urllib.error.URLError as exc:
            return None, f"r2_request_failed:{exc.reason}"
        except TimeoutError:
            return None, "r2_request_timeout"
        return data.decode("utf-8", errors="replace"), None


def read_targets(path: Path, *, focus_tasks: Sequence[str], limit: int | None) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"Targets file not found: {path}")
    focus = set(focus_tasks)
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if focus and row.get("task_id") not in focus:
                continue
            rows.append(dict(row))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def bool_from_text(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def dashboard_url(base_url: str, path: str | None) -> str:
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


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
          size_bytes::int
        from benchmark.benchmark_artifacts
        where trial_id::text = any(%s)
          and artifact_type = any(%s)
          and r2_uri is not null
        order by trial_id::text, artifact_type, created_at nulls last, id
    """
    try:
        with psycopg.connect(db_url, row_factory=dict_row, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (list(trial_ids), list(RELATED_ARTIFACT_TYPES)))
                rows = list(cur.fetchall())
    except Exception as exc:  # pragma: no cover - live database availability only
        return {}, f"related artifact lookup failed: {type(exc).__name__}"

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_types: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["trial_id"], row["artifact_type"])
        if key in seen_types:
            continue
        seen_types.add(key)
        grouped[row["trial_id"]].append(dict(row))
    return grouped, None


def evidence_for_target(
    *,
    target: dict[str, str],
    r2: R2Client,
    related_artifacts: Sequence[dict[str, Any]],
) -> tuple[list[EvidenceSource], list[str]]:
    evidence: list[EvidenceSource] = []
    notes: list[str] = []
    exception_text, error = r2.fetch_text(target.get("r2_uri", ""))
    if exception_text is not None:
        evidence.append(
            EvidenceSource(
                artifact_type="exception",
                artifact_id=target.get("exception_artifact_id", ""),
                source_rank=0,
                text=exception_text,
            )
        )
    elif error:
        notes.append(f"exception_artifact_fetch={error}")

    seen_types = {source.artifact_type for source in evidence}
    for rank, artifact in enumerate(related_artifacts, start=1):
        artifact_type = str(artifact.get("artifact_type") or "")
        if not artifact_type or artifact_type in seen_types:
            continue
        text, related_error = r2.fetch_text(str(artifact.get("r2_uri") or ""))
        if text is not None:
            evidence.append(
                EvidenceSource(
                    artifact_type=artifact_type,
                    artifact_id=str(artifact.get("artifact_id") or ""),
                    source_rank=rank,
                    text=text,
                )
            )
            seen_types.add(artifact_type)
        elif related_error:
            notes.append(f"{artifact_type}_fetch={related_error}")
    return evidence, notes


def classification_row(
    *,
    target: dict[str, str],
    classification: Classification,
    evidence_types: Sequence[str],
    base_url: str,
) -> dict[str, Any]:
    return {
        "suite_id": target.get("suite_id", ""),
        "arm_id": target.get("arm_id", ""),
        "run_label": target.get("run_label", ""),
        "task_id": target.get("task_id", ""),
        "attempt_index": target.get("attempt_index", ""),
        "trial_id": target.get("trial_id", ""),
        "exception_artifact_id": target.get("exception_artifact_id", ""),
        "exception_artifact_dashboard_path": dashboard_url(base_url, target.get("exception_artifact_dashboard_path", "")),
        "exception_type": target.get("exception_type", ""),
        "missing_cost": bool_from_text(target.get("missing_cost", "")),
        "reward": target.get("reward", ""),
        "runtime_seconds": target.get("runtime_seconds", ""),
        "runtime_band": runtime_band(target.get("runtime_seconds")),
        "primary_category": classification.primary_category,
        "secondary_category": classification.secondary_category,
        "confidence": classification.confidence,
        "needs_manual_review": classification.needs_manual_review,
        "matched_signal": classification.matched_signal,
        "matched_pattern": classification.matched_pattern,
        "evidence_artifact_type": classification.evidence_artifact_type,
        "evidence_artifact_id": classification.evidence_artifact_id,
        "evidence_source_rank": classification.evidence_source_rank,
        "classification_reason": classification.classification_reason,
        "evidence_source_artifact_types": ",".join(evidence_types),
        "evidence_excerpt": classification.evidence_excerpt,
        "recommended_next_step": classification.recommended_next_step,
        "notes": classification.notes,
    }


def build_summary_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[
            (
                str(row.get("arm_id") or ""),
                str(row.get("primary_category") or ""),
                str(row.get("runtime_band") or ""),
            )
        ].append(row)

    summary: list[dict[str, Any]] = []
    for (arm_id, category, band), group in sorted(grouped.items()):
        confidence_floor_rank = min(CONFIDENCE_RANK[str(row.get("confidence") or "low")] for row in group)
        representative_tasks = sorted({str(row.get("task_id") or "") for row in group if row.get("task_id")})[:5]
        representative_signals: list[str] = []
        for row in group:
            signal_text = str(row.get("matched_signal") or "")
            if signal_text and signal_text not in representative_signals:
                representative_signals.append(signal_text)
            if len(representative_signals) >= 5:
                break
        summary.append(
            {
                "arm_id": arm_id,
                "primary_category": category,
                "runtime_band": band,
                "count": len(group),
                "missing_cost_count": sum(1 for row in group if bool_from_text(row.get("missing_cost"))),
                "needs_manual_review_count": sum(
                    1 for row in group if bool_from_text(row.get("needs_manual_review"))
                ),
                "representative_tasks": ",".join(representative_tasks),
                "representative_matched_signals": ",".join(representative_signals),
                "confidence_floor": CONFIDENCE_BY_RANK[confidence_floor_rank],
            }
        )
    return summary


def generated_paths(output_dir: Path, datestamp: str) -> tuple[Path, Path]:
    return (
        output_dir / f"phase3_exception_classification_{datestamp}.tsv",
        output_dir / f"phase3_exception_classification_summary_{datestamp}.tsv",
    )


def markdown_table(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def category_counts(rows: Sequence[dict[str, Any]]) -> list[tuple[str, int, int, str, str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("primary_category") or "")].append(row)
    result = []
    for category, group in grouped.items():
        confidence_floor_rank = min(CONFIDENCE_RANK[str(row.get("confidence") or "low")] for row in group)
        signals: list[str] = []
        for row in group:
            signal_text = str(row.get("matched_signal") or "")
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


def classification_section(
    *,
    classification_path: Path,
    summary_path: Path,
    rows: Sequence[dict[str, Any]],
    summary_rows: Sequence[dict[str, Any]],
) -> str:
    high_confidence_categories = sorted(
        {str(row.get("primary_category")) for row in rows if row.get("confidence") == "high"}
    )
    manual_categories = sorted(
        {str(row.get("primary_category")) for row in rows if bool_from_text(row.get("needs_manual_review"))}
    )
    sonnet_rows = [row for row in rows if row.get("arm_id") == "router-anthropic-sonnet"]
    sonnet_counts = category_counts(sonnet_rows)
    direct_high_rows = [
        row
        for row in rows
        if row.get("confidence") == "high"
        and not bool_from_text(row.get("needs_manual_review"))
        and row.get("matched_signal")
    ]
    manual_rows = [row for row in rows if bool_from_text(row.get("needs_manual_review"))]
    category_table = markdown_table(
        ["Primary category", "Count", "Manual-review flagged", "Confidence floor", "Matched signals"],
        category_counts(rows),
    )
    sonnet_table = markdown_table(
        ["Primary category", "Count", "Manual-review flagged", "Confidence floor", "Matched signals"],
        sonnet_counts,
    )
    runtime_table = markdown_table(
        [
            "Arm",
            "Category",
            "Runtime band",
            "Count",
            "Missing cost",
            "Manual review",
            "Confidence floor",
            "Matched signals",
        ],
        [
            (
                row["arm_id"],
                row["primary_category"],
                row["runtime_band"],
                row["count"],
                row["missing_cost_count"],
                row["needs_manual_review_count"],
                row["confidence_floor"],
                row["representative_matched_signals"],
            )
            for row in summary_rows
        ],
    )
    high_text = ", ".join(f"`{category}`" for category in high_confidence_categories) or "none"
    manual_text = ", ".join(f"`{category}`" for category in manual_categories) or "none"
    classification_rel = classification_path.as_posix()
    summary_rel = summary_path.as_posix()

    return f"""## Automated First-Pass Exception Classification

Source files:

- `{classification_rel}`
- `{summary_rel}`

This is deterministic, rule-based, evidence-assisted first-pass classification from exception artifacts and related same-trial artifacts when available. It now records matched signals and source artifacts for traceability. It is not final human judgment; the output should guide manual spot checks and root-cause review.

Summary by category:

{category_table}

Summary by category and runtime band:

{runtime_table}

High-confidence direct categories observed: {high_text} ({len(direct_high_rows)} rows).

Categories marked `needs_manual_review`: {manual_text} ({len(manual_rows)} rows).

Sonnet-specific observations:

{sonnet_table}
"""


def upsert_markdown_section(report_path: Path, section: str) -> None:
    header = "## Automated First-Pass Exception Classification"
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
    for target in targets:
        notes = [related_lookup_note] if related_lookup_note else []
        related_artifacts = related_lookup.get(target.get("trial_id", ""), [])
        evidence, fetch_notes = evidence_for_target(target=target, r2=r2, related_artifacts=related_artifacts)
        classification = classify_exception(
            target_row=target,
            evidence_by_type=evidence,
            fetch_notes=[*notes, *fetch_notes],
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
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--date", default=utc_datestamp(), help="UTC datestamp in YYYYMMDD format.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--docs-report", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--focus-task", action="append", default=[])
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--include-related-artifacts", action=argparse.BooleanOptionalAction, default=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    docs_report = args.docs_report or Path(f"docs/reports/phase3/PHASE3_ARTIFACT_QUALITATIVE_REVIEW_{args.date}.md")
    targets = read_targets(args.targets, focus_tasks=args.focus_task, limit=args.limit)
    r2 = R2Client.from_env()
    related_lookup: dict[str, list[dict[str, Any]]] = {}
    related_note = None
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
