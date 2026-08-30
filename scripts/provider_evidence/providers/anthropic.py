from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROVIDER = "anthropic"

API_VERSION = "2023-06-01"

USAGE_ENDPOINT = (
    "https://api.anthropic.com/"
    "v1/organizations/usage_report/messages"
)

COST_ENDPOINT = (
    "https://api.anthropic.com/"
    "v1/organizations/cost_report"
)


class ProviderCollectionError(RuntimeError):
    pass


def credential_preflight(
    environ: Mapping[str, str],
) -> dict[str, Any]:
    """Assess collection eligibility without network access."""

    required_environment = (
        "ANTHROPIC_ADMIN_API_KEY"
    )

    admin_key = environ.get(
        required_environment,
        "",
    )

    base = {
        "provider":
            PROVIDER,
        "required_environment":
            required_environment,
        "network_requests_performed":
            False,
        "credential_value_retained":
            False,
    }

    if not admin_key:
        return {
            **base,
            "credential_available":
                False,
            "credential_type_validated":
                False,
            "collection_eligible":
                False,
            "collection_status":
                "unavailable",
            "limitation_code":
                "missing_admin_api_key",
        }

    if not admin_key.startswith(
        "sk-ant-admin01-"
    ):
        return {
            **base,
            "credential_available":
                True,
            "credential_type_validated":
                False,
            "collection_eligible":
                False,
            "collection_status":
                "unavailable",
            "limitation_code":
                "invalid_admin_api_key_type",
        }

    return {
        **base,
        "credential_available":
            True,
        "credential_type_validated":
            True,
        "collection_eligible":
            True,
        "collection_status":
            "eligible",
        "limitation_code":
            None,
    }


RequestJSON = Callable[
    [str, Mapping[str, Any], str, float],
    dict[str, Any],
]


def _parse_timestamp(
    value: str,
) -> datetime:
    text = value.strip()

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        result = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"invalid RFC3339 timestamp: {value}"
        ) from exc

    if result.tzinfo is None:
        raise ValueError(
            "timestamp must include timezone"
        )

    return result.astimezone(timezone.utc)


def validate_window(
    starting_at: str,
    ending_at: str,
) -> None:
    start = _parse_timestamp(starting_at)
    end = _parse_timestamp(ending_at)

    if end <= start:
        raise ValueError(
            "ending_at must be after starting_at"
        )


def _format_utc(
    value: datetime,
) -> str:
    return (
        value.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _cost_window(
    starting_at: str,
    ending_at: str,
) -> tuple[str, str]:
    start = _parse_timestamp(
        starting_at
    )
    end = _parse_timestamp(
        ending_at
    )

    cost_start = start.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    end_day = end.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    if end == end_day:
        cost_end = end_day
    else:
        cost_end = (
            end_day
            + timedelta(days=1)
        )

    if cost_end <= cost_start:
        cost_end = (
            cost_start
            + timedelta(days=1)
        )

    return (
        _format_utc(cost_start),
        _format_utc(cost_end),
    )


def request_plan(
    *,
    starting_at: str,
    ending_at: str,
    usage_bucket_width: str = "1m",
) -> dict[str, Any]:
    validate_window(
        starting_at,
        ending_at,
    )

    (
        cost_starting_at,
        cost_ending_at,
    ) = _cost_window(
        starting_at,
        ending_at,
    )

    if usage_bucket_width not in {
        "1m",
        "1h",
        "1d",
    }:
        raise ValueError(
            "unsupported Anthropic usage bucket width"
        )

    return {
        "schema_version": 1,
        "provider": PROVIDER,
        "credential_env":
            "ANTHROPIC_ADMIN_API_KEY",
        "requests": [
            {
                "evidence_kind": "usage",
                "method": "GET",
                "endpoint": USAGE_ENDPOINT,
                "params": {
                    "starting_at":
                        starting_at,
                    "ending_at":
                        ending_at,
                    "bucket_width":
                        usage_bucket_width,
                    "limit": (
                        1440
                        if usage_bucket_width == "1m"
                        else (
                            168
                            if usage_bucket_width == "1h"
                            else 31
                        )
                    ),
                    "group_by[]": [
                        "api_key_id",
                        "workspace_id",
                        "model",
                    ],
                },
            },
            {
                "evidence_kind": "cost",
                "method": "GET",
                "endpoint": COST_ENDPOINT,
                "params": {
                    "starting_at":
                        cost_starting_at,
                    "ending_at":
                        cost_ending_at,
                    "bucket_width":
                        "1d",
                    "limit": 31,
                    "group_by[]": [
                        "workspace_id",
                        "description",
                    ],
                },
            },
        ],
        "authority_note": (
            "collection_is_provider_evidence_not_run_"
            "attribution_or_automatic_selected_authority"
        ),
    }


def _http_get_json(
    endpoint: str,
    params: Mapping[str, Any],
    admin_key: str,
    timeout: float,
) -> dict[str, Any]:
    query = urlencode(
        list(params.items()),
        doseq=True,
    )

    request = Request(
        f"{endpoint}?{query}",
        headers={
            "anthropic-version":
                API_VERSION,
            "x-api-key":
                admin_key,
            "accept":
                "application/json",
            "User-Agent":
                "cc-deepseek-bench-provider-evidence/0.1",
        },
        method="GET",
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            payload = response.read()
    except HTTPError as exc:
        raise ProviderCollectionError(
            "Anthropic Admin API HTTP failure "
            f"(status={exc.code})"
        ) from exc
    except URLError as exc:
        raise ProviderCollectionError(
            "Anthropic Admin API transport failure"
        ) from exc

    try:
        result = json.loads(
            payload.decode("utf-8")
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ProviderCollectionError(
            "Anthropic Admin API returned "
            "invalid JSON"
        ) from exc

    if not isinstance(result, dict):
        raise ProviderCollectionError(
            "Anthropic Admin API response "
            "is not an object"
        )

    return result


def _page_sha256(
    payload: Mapping[str, Any],
) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def collect_paginated(
    *,
    endpoint: str,
    params: Mapping[str, Any],
    admin_key: str,
    timeout: float = 30.0,
    request_json: RequestJSON = _http_get_json,
) -> list[dict[str, Any]]:
    if not admin_key:
        raise ValueError(
            "Anthropic Admin API key is empty"
        )

    pages: list[dict[str, Any]] = []
    page_token: str | None = None

    for page_number in range(1, 101):
        query = dict(params)

        if page_token is not None:
            query["page"] = page_token

        payload = request_json(
            endpoint,
            query,
            admin_key,
            timeout,
        )

        if not isinstance(
            payload.get("data"),
            list,
        ):
            raise ProviderCollectionError(
                "Anthropic Admin API page "
                "has invalid data field"
            )

        has_more = payload.get(
            "has_more"
        )

        if not isinstance(
            has_more,
            bool,
        ):
            raise ProviderCollectionError(
                "Anthropic Admin API page "
                "has invalid has_more field"
            )

        pages.append(
            {
                "page_number":
                    page_number,
                "sha256":
                    _page_sha256(payload),
                "response":
                    payload,
            }
        )

        if not has_more:
            return pages

        next_page = payload.get(
            "next_page"
        )

        if (
            not isinstance(
                next_page,
                str,
            )
            or not next_page
        ):
            raise ProviderCollectionError(
                "Anthropic Admin API pagination "
                "is incomplete"
            )

        page_token = next_page

    raise ProviderCollectionError(
        "Anthropic Admin API pagination "
        "exceeded safety limit"
    )


def collect(
    *,
    starting_at: str,
    ending_at: str,
    admin_key: str,
    usage_bucket_width: str = "1m",
    timeout: float = 30.0,
    request_json: RequestJSON = _http_get_json,
) -> dict[str, Any]:
    plan = request_plan(
        starting_at=starting_at,
        ending_at=ending_at,
        usage_bucket_width=(
            usage_bucket_width
        ),
    )

    requests = {
        row["evidence_kind"]: row
        for row in plan["requests"]
    }

    usage = requests["usage"]
    cost = requests["cost"]

    usage_pages = collect_paginated(
        endpoint=usage["endpoint"],
        params=usage["params"],
        admin_key=admin_key,
        timeout=timeout,
        request_json=request_json,
    )

    cost_pages = collect_paginated(
        endpoint=cost["endpoint"],
        params=cost["params"],
        admin_key=admin_key,
        timeout=timeout,
        request_json=request_json,
    )

    return {
        "schema_version": 1,
        "provider": PROVIDER,
        "collection_type":
            "provider_admin_api",
        "starting_at": starting_at,
        "ending_at": ending_at,
        "usage_bucket_width":
            usage_bucket_width,
        "credential_reference":
            "ANTHROPIC_ADMIN_API_KEY",
        "credential_value_retained":
            False,
        "request_plan":
            plan,
        "usage_pages":
            usage_pages,
        "cost_pages":
            cost_pages,
        "authority_note": (
            "first_party_provider_evidence_requires_"
            "allocation_concurrency_review_and_reconciliation"
        ),
    }
