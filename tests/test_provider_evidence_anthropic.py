from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


from scripts.collect_provider_evidence import (
    _write_private_json,
    main,
)
from scripts.provider_evidence.capability import (
    get_capability,
)
from scripts.provider_evidence.providers import anthropic


ROOT = Path(__file__).resolve().parents[1]


def test_anthropic_capability_is_explicit():
    capability = get_capability(
        "anthropic"
    )

    assert (
        capability.credential_env
        == "ANTHROPIC_ADMIN_API_KEY"
    )
    assert capability.actual_usage_api
    assert capability.actual_cost_api
    assert capability.cost_amount_unit == "cent"

    assert (
        "api_key_id"
        in capability.usage_allocation_dimensions
    )
    assert (
        "workspace_id"
        in capability.cost_allocation_dimensions
    )


def test_anthropic_capability_fails_closed_on_ambiguous_allocation():
    capability = get_capability(
        "anthropic"
    )

    limitations = set(
        capability.limitations
    )

    assert (
        "usage_run_attribution_requires_distinguishable_"
        "allocation_dimensions"
        in limitations
    )

    assert (
        "cost_run_attribution_requires_workspace_day_"
        "isolation_or_independent_allocation"
        in limitations
    )

    assert (
        "overlapping_indistinguishable_runs_must_not_be_"
        "allocated"
        in limitations
    )


def test_anthropic_plan_has_no_secret():
    plan = anthropic.request_plan(
        starting_at=(
            "2026-06-01T00:00:00Z"
        ),
        ending_at=(
            "2026-06-02T00:00:00Z"
        ),
    )

    rendered = json.dumps(plan)

    assert (
        "ANTHROPIC_ADMIN_API_KEY"
        in rendered
    )

    assert "sk-ant-" not in rendered

    usage, cost = plan["requests"]

    assert (
        usage["endpoint"]
        == anthropic.USAGE_ENDPOINT
    )
    assert (
        usage["params"][
            "bucket_width"
        ]
        == "1m"
    )
    assert (
        usage["params"][
            "group_by[]"
        ]
        == [
            "api_key_id",
            "workspace_id",
            "model",
        ]
    )

    assert (
        cost["endpoint"]
        == anthropic.COST_ENDPOINT
    )
    assert (
        cost["params"][
            "group_by[]"
        ]
        == [
            "workspace_id",
            "description",
        ]
    )


def test_anthropic_plan_aligns_cost_to_utc_day():
    plan = anthropic.request_plan(
        starting_at=(
            "2026-06-27T01:30:00Z"
        ),
        ending_at=(
            "2026-06-27T10:27:00Z"
        ),
        usage_bucket_width="1m",
    )

    usage, cost = plan["requests"]

    assert (
        usage["params"]["starting_at"]
        == "2026-06-27T01:30:00Z"
    )
    assert (
        usage["params"]["ending_at"]
        == "2026-06-27T10:27:00Z"
    )

    assert (
        cost["params"]["starting_at"]
        == "2026-06-27T00:00:00Z"
    )
    assert (
        cost["params"]["ending_at"]
        == "2026-06-28T00:00:00Z"
    )


def test_anthropic_cost_window_preserves_exact_day_end():
    plan = anthropic.request_plan(
        starting_at=(
            "2026-06-27T23:30:00Z"
        ),
        ending_at=(
            "2026-06-28T00:00:00Z"
        ),
        usage_bucket_width="1m",
    )

    usage, cost = plan["requests"]

    assert (
        usage["params"]["ending_at"]
        == "2026-06-28T00:00:00Z"
    )

    assert (
        cost["params"]["starting_at"]
        == "2026-06-27T00:00:00Z"
    )
    assert (
        cost["params"]["ending_at"]
        == "2026-06-28T00:00:00Z"
    )


def test_credential_preflight_does_not_substitute_inference_key():
    result = anthropic.credential_preflight(
        {
            "ANTHROPIC_API_KEY":
                "standard-inference-key-placeholder",
        }
    )

    assert result[
        "credential_available"
    ] is False

    assert result[
        "credential_type_validated"
    ] is False

    assert result[
        "collection_eligible"
    ] is False

    assert result[
        "collection_status"
    ] == "unavailable"

    assert result[
        "limitation_code"
    ] == "missing_admin_api_key"

    assert result[
        "network_requests_performed"
    ] is False


def test_credential_preflight_rejects_wrong_admin_key_type():
    result = anthropic.credential_preflight(
        {
            "ANTHROPIC_ADMIN_API_KEY":
                "not-an-admin-key",
        }
    )

    assert result[
        "credential_available"
    ] is True

    assert result[
        "credential_type_validated"
    ] is False

    assert result[
        "collection_eligible"
    ] is False

    assert result[
        "limitation_code"
    ] == "invalid_admin_api_key_type"

    assert result[
        "network_requests_performed"
    ] is False


def test_credential_preflight_accepts_admin_key_shape():
    admin_key = (
        "sk-ant-admin01-"
        + ("x" * 12)
    )

    result = anthropic.credential_preflight(
        {
            "ANTHROPIC_ADMIN_API_KEY":
                admin_key,
        }
    )

    assert result[
        "credential_available"
    ] is True

    assert result[
        "credential_type_validated"
    ] is True

    assert result[
        "collection_eligible"
    ] is True

    assert result[
        "collection_status"
    ] == "eligible"

    assert result[
        "limitation_code"
    ] is None

    rendered = json.dumps(
        result,
        sort_keys=True,
    )

    assert admin_key not in rendered


def test_plan_reports_missing_admin_without_using_inference_key(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv(
        "ANTHROPIC_API_KEY",
        "standard-inference-key-placeholder",
    )

    monkeypatch.delenv(
        "ANTHROPIC_ADMIN_API_KEY",
        raising=False,
    )

    result = main(
        [
            "--provider",
            "anthropic",
            "--starting-at",
            "2026-06-27T01:30:00Z",
            "--ending-at",
            "2026-06-27T10:27:00Z",
            "--usage-bucket-width",
            "1m",
            "--plan",
        ]
    )

    captured = capsys.readouterr()

    assert result == 0

    payload = json.loads(
        captured.out
    )

    preflight = payload[
        "credential_preflight"
    ]

    assert preflight[
        "required_environment"
    ] == "ANTHROPIC_ADMIN_API_KEY"

    assert preflight[
        "credential_available"
    ] is False

    assert preflight[
        "collection_eligible"
    ] is False

    assert preflight[
        "collection_status"
    ] == "unavailable"

    assert preflight[
        "limitation_code"
    ] == "missing_admin_api_key"

    assert preflight[
        "network_requests_performed"
    ] is False


def test_collect_missing_admin_fails_closed_without_output(
    monkeypatch,
    capsys,
    tmp_path: Path,
):
    monkeypatch.setenv(
        "ANTHROPIC_API_KEY",
        "standard-inference-key-placeholder",
    )

    monkeypatch.delenv(
        "ANTHROPIC_ADMIN_API_KEY",
        raising=False,
    )

    output = (
        tmp_path
        / "should-not-exist.json"
    )

    result = main(
        [
            "--provider",
            "anthropic",
            "--starting-at",
            "2026-06-27T01:30:00Z",
            "--ending-at",
            "2026-06-27T10:27:00Z",
            "--usage-bucket-width",
            "1m",
            "--collect",
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr()

    assert result == 2
    assert not output.exists()

    payload = json.loads(
        captured.out
    )

    assert (
        payload["status"]
        == "provider_evidence_unavailable"
    )

    assert (
        payload["collection_status"]
        == "unavailable"
    )

    assert (
        payload["limitation_code"]
        == "missing_admin_api_key"
    )

    assert (
        payload["network_requests_performed"]
        is False
    )


def test_collect_wrong_admin_type_fails_closed_without_output(
    monkeypatch,
    capsys,
    tmp_path: Path,
):
    monkeypatch.setenv(
        "ANTHROPIC_ADMIN_API_KEY",
        "not-an-admin-key",
    )

    output = (
        tmp_path
        / "should-not-exist.json"
    )

    result = main(
        [
            "--provider",
            "anthropic",
            "--starting-at",
            "2026-06-27T01:30:00Z",
            "--ending-at",
            "2026-06-27T10:27:00Z",
            "--usage-bucket-width",
            "1m",
            "--collect",
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr()

    assert result == 2
    assert not output.exists()

    payload = json.loads(
        captured.out
    )

    assert (
        payload["status"]
        == "provider_evidence_unavailable"
    )

    assert (
        payload["collection_status"]
        == "unavailable"
    )

    assert (
        payload["limitation_code"]
        == "invalid_admin_api_key_type"
    )

    assert (
        payload["network_requests_performed"]
        is False
    )


def test_anthropic_pagination_is_complete():
    calls = []

    def fake_request(
        endpoint,
        params,
        admin_key,
        timeout,
    ):
        calls.append(
            (
                endpoint,
                dict(params),
                admin_key,
                timeout,
            )
        )

        if "page" not in params:
            return {
                "data": [
                    {"value": 1}
                ],
                "has_more": True,
                "next_page": "page-2",
            }

        assert (
            params["page"]
            == "page-2"
        )

        return {
            "data": [
                {"value": 2}
            ],
            "has_more": False,
            "next_page": None,
        }

    pages = anthropic.collect_paginated(
        endpoint="https://example.invalid",
        params={
            "starting_at":
                "2026-06-01T00:00:00Z",
        },
        admin_key="synthetic-secret",
        timeout=4.0,
        request_json=fake_request,
    )

    assert len(pages) == 2
    assert len(calls) == 2

    assert (
        "page"
        not in calls[0][1]
    )
    assert (
        calls[1][1]["page"]
        == "page-2"
    )


def test_collection_retains_no_credential_value():
    def fake_request(
        endpoint,
        params,
        admin_key,
        timeout,
    ):
        assert (
            admin_key
            == "synthetic-secret"
        )

        return {
            "data": [],
            "has_more": False,
            "next_page": None,
        }

    bundle = anthropic.collect(
        starting_at=(
            "2026-06-01T00:00:00Z"
        ),
        ending_at=(
            "2026-06-02T00:00:00Z"
        ),
        admin_key="synthetic-secret",
        request_json=fake_request,
    )

    rendered = json.dumps(bundle)

    assert (
        "synthetic-secret"
        not in rendered
    )

    assert (
        bundle[
            "credential_value_retained"
        ]
        is False
    )


def test_private_bundle_is_mode_600(
    tmp_path: Path,
):
    path = (
        tmp_path
        / "anthropic-provider-evidence.json"
    )

    digest = _write_private_json(
        path,
        {"safe": True},
    )

    assert len(digest) == 64

    assert (
        path.stat().st_mode
        & 0o777
    ) == 0o600
def test_private_bundle_refuses_dangling_symlink(
    tmp_path: Path,
):
    target = (
        tmp_path
        / "target.json"
    )

    output = (
        tmp_path
        / "bundle.json"
    )

    output.symlink_to(
        target
    )

    try:
        _write_private_json(
            output,
            {
                "provider":
                    "anthropic",
            },
        )
    except FileExistsError:
        pass
    else:
        raise AssertionError(
            "expected dangling symlink output "
            "to be rejected"
        )

    assert not target.exists()


def test_cli_direct_script_plan_mode_is_network_free():
    script = (
        ROOT
        / "scripts/collect_provider_evidence.py"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--provider",
            "anthropic",
            "--starting-at",
            "2026-06-01T00:00:00Z",
            "--ending-at",
            "2026-06-02T00:00:00Z",
            "--usage-bucket-width",
            "1m",
            "--plan",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, (
        result.stderr
    )

    payload = json.loads(
        result.stdout
    )

    assert (
        payload[
            "network_requests_performed"
        ]
        is False
    )

    assert (
        payload["capability"][
            "credential_env"
        ]
        == "ANTHROPIC_ADMIN_API_KEY"
    )

    assert (
        len(
            payload[
                "request_plan"
            ]["requests"]
        )
        == 2
    )
