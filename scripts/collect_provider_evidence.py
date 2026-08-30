#!/usr/bin/env python3
"""Collect read-only provider billing/usage evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


# Support both:
#   python scripts/collect_provider_evidence.py
#   python -m scripts.collect_provider_evidence
try:
    from scripts.provider_evidence.capability import (
        get_capability,
    )
    from scripts.provider_evidence.providers import anthropic
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise

    from provider_evidence.capability import (
        get_capability,
    )
    from provider_evidence.providers import anthropic


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    parser.add_argument(
        "--provider",
        required=True,
        choices=["anthropic"],
    )
    parser.add_argument(
        "--starting-at",
        required=True,
    )
    parser.add_argument(
        "--ending-at",
        required=True,
    )
    parser.add_argument(
        "--usage-bucket-width",
        choices=[
            "1m",
            "1h",
            "1d",
        ],
        default="1m",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
    )
    parser.add_argument(
        "--output",
    )

    mode = parser.add_mutually_exclusive_group(
        required=True
    )

    mode.add_argument(
        "--plan",
        action="store_true",
    )
    mode.add_argument(
        "--collect",
        action="store_true",
    )

    args = parser.parse_args(argv)

    if args.timeout <= 0:
        parser.error(
            "--timeout must be positive"
        )

    if args.collect and not args.output:
        parser.error(
            "--collect requires --output"
        )

    return args


def _write_private_json(
    path: Path,
    payload: object,
) -> str:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    encoded = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
    )

    try:
        fd = os.open(
            path,
            flags,
            0o600,
        )
    except FileExistsError as exc:
        raise FileExistsError(
            f"refusing to overwrite {path}"
        ) from exc

    with os.fdopen(
        fd,
        "wb",
    ) as handle:
        handle.write(encoded)

    return hashlib.sha256(
        encoded
    ).hexdigest()


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(argv)

    capability = get_capability(
        args.provider
    )

    if args.provider != "anthropic":
        raise RuntimeError(
            "unsupported provider"
        )

    plan = anthropic.request_plan(
        starting_at=args.starting_at,
        ending_at=args.ending_at,
        usage_bucket_width=(
            args.usage_bucket_width
        ),
    )

    preflight = anthropic.credential_preflight(
        os.environ
    )

    if args.plan:
        print(
            json.dumps(
                {
                    "capability":
                        capability.__dict__,
                    "request_plan":
                        plan,
                    "credential_preflight":
                        preflight,
                    "network_requests_performed":
                        False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    admin_key = (
        os.getenv(
            capability.credential_env
        )
        if preflight[
            "collection_eligible"
        ]
        else None
    )

    if not admin_key:
        print(
            json.dumps(
                {
                    "status":
                        "provider_evidence_unavailable",
                    "provider":
                        args.provider,
                    "required_environment":
                        capability.credential_env,
                    "credential_preflight":
                        preflight,
                    "collection_status":
                        "unavailable",
                    "limitation_code":
                        preflight[
                            "limitation_code"
                        ],
                    "network_requests_performed":
                        False,
                },
                sort_keys=True,
            )
        )
        return 2

    try:
        bundle = anthropic.collect(
            starting_at=args.starting_at,
            ending_at=args.ending_at,
            admin_key=admin_key,
            usage_bucket_width=(
                args.usage_bucket_width
            ),
            timeout=args.timeout,
        )

        output = Path(args.output)

        digest = _write_private_json(
            output,
            bundle,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "provider":
                        args.provider,
                    "error_type":
                        type(exc).__name__,
                },
                sort_keys=True,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "status": "collected",
                "provider":
                    args.provider,
                "output":
                    str(output),
                "sha256":
                    digest,
                "mode":
                    oct(
                        output.stat().st_mode
                        & 0o777
                    ),
                "usage_page_count":
                    len(
                        bundle[
                            "usage_pages"
                        ]
                    ),
                "cost_page_count":
                    len(
                        bundle[
                            "cost_pages"
                        ]
                    ),
                "credential_value_retained":
                    False,
            },
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
