#!/usr/bin/env python3
"""Strict derived-output credential/reasoning scan.

Output intentionally contains only filenames and rule names. Candidate values,
excerpts, and hashes are never printed.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


GENERATOR = Path(__file__).with_name("generate_comprehensive_evidence_review.py")
SPEC = importlib.util.spec_from_file_location("comprehensive_review_scan", GENERATOR)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("unable to load comprehensive review scanner")
review = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = review
SPEC.loader.exec_module(review)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_dir",
        nargs="?",
        type=Path,
        default=review.DEFAULT_OUTPUT,
    )
    args = parser.parse_args()
    findings = review.strict_scan_output_directory(args.output_dir)
    if findings:
        for filename, rules in sorted(findings.items()):
            print(f"{filename}\t{','.join(rules)}")
        return 1
    print("strict_output_scan\tclean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
