from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs/reports/phase3/PHASE3_CLOSEOUT_INDEX_20260714.md"
OUT = ROOT / "results/phase3/reporting/phase3_closeout_artifact_audit_20260715.tsv"

PATTERN = re.compile(r"`([^`]+\.(?:md|pdf|tsv|csv|svg|png|html))`")

def main() -> None:
    text = INDEX.read_text()
    refs = sorted(set(PATTERN.findall(text)))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as handle:
        handle.write("path\texists\tsize_bytes\n")
        missing = []
        for ref in refs:
            path = ROOT / ref
            exists = path.exists()
            size = path.stat().st_size if exists else 0
            handle.write(f"{ref}\t{str(exists).lower()}\t{size}\n")
            if not exists:
                missing.append(ref)

    print(f"audited {len(refs)} referenced artifacts")
    print(f"wrote {OUT}")
    if missing:
        print("missing artifacts:")
        for ref in missing:
            print(f"  {ref}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
