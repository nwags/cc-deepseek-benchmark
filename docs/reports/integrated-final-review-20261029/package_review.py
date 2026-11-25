#!/usr/bin/env python3
"""Package the unpublished report/site review without changing either Git index.

Requires the validated, pinned local checkouts. Copies only an explicit earlier
review archive and current website diff/overlay; no provider or DB operations.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
BENCHMARK = HERE.parents[2]
WORKSPACE = BENCHMARK.parent
SITE = WORKSPACE / "nwags-website-review"
OUT = WORKSPACE / "deliverables/cc_backend_benchmark_report_website_review_20261030.zip"
BASE = "79f790fdd9067e33a29e0409c15f8890068ff22d"
SITE_BASE = "83fd7cbe047c06de3f1fd057d4f7a9627c712992"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root)


def scan_text(name: str, text: str) -> None:
    patterns = [r"\bsk-ant-api\d+-[A-Za-z0-9_-]{40,}",
                r"\bsk-[A-Za-z0-9_-]{32,}\b",
                r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
                r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{30,}"]
    if any(re.search(pattern, text) for pattern in patterns):
        raise AssertionError(f"Possible credential pattern in {name}; value withheld")


def scan_bytes(name: str, raw: bytes, counts: dict, depth: int = 0) -> None:
    if name.endswith(".zip"):
        assert depth < 4, "Unexpected nested archive depth"
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            assert z.testzip() is None
            for entry in z.infolist():
                if not entry.is_dir():
                    scan_bytes(name + "/" + entry.filename, z.read(entry), counts, depth + 1)
    elif name.endswith(".pdf"):
        counts["pdf_files"] += 1
        scan_text(name, "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(raw)).pages))
    elif Path(name).suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        counts["text_files"] += 1
        scan_text(name, raw.decode("utf-8"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def main() -> None:
    assert git(BENCHMARK, "rev-parse", "HEAD").decode().strip() == BASE
    assert git(SITE, "rev-parse", "HEAD").decode().strip() == SITE_BASE
    assert not git(BENCHMARK, "diff", "HEAD", "--name-only").strip()
    assert not git(SITE, "diff", "--cached", "--name-only").strip()
    validation = json.loads((HERE / "validation/website_validation.json").read_text())
    assert validation["status"] == "PASS" and validation["checks_passed"] == 525
    assert validation["scientific_field_mismatches"] == 0
    assert json.loads((HERE / "validation/browser_review.json").read_text())["status"] == "PASS"
    observed = json.loads((HERE / "validation/live_main_checks.json").read_text())
    assert [r["head"] for r in observed] == [BASE, SITE_BASE]

    tracked = git(SITE, "diff", "--name-only", "HEAD").decode().splitlines()
    added = git(SITE, "ls-files", "--others", "--exclude-standard").decode().splitlines()
    assert len(tracked) == 7 and len(added) == 16
    patch = git(SITE, "diff", "--binary", "HEAD")

    # Verify the tracked patch against original baseline bytes, entirely in /tmp.
    with tempfile.TemporaryDirectory(prefix="benchmark-site-overlay-") as td:
        clean = Path(td)
        for name in tracked:
            target = clean / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(git(SITE, "show", "HEAD:" + name))
            target.chmod(int(git(SITE, "ls-tree", "HEAD", name).split()[0], 8) & 0o777)
        subprocess.run(["git", "apply", "--check", "-"], input=patch, cwd=clean, check=True)
        subprocess.run(["git", "apply", "-"], input=patch, cwd=clean, check=True)
        for name in tracked:
            assert (clean / name).read_bytes() == (SITE / name).read_bytes()

    payload: dict[str, bytes] = {}
    modes: dict[str, int] = {}
    previous = WORKSPACE / "deliverables/cc_backend_benchmark_revised_review_20261027.zip"
    with zipfile.ZipFile(previous) as z:
        assert z.testzip() is None
        for entry in z.infolist():
            assert not entry.is_dir()
            raw = z.read(entry)
            if entry.filename.startswith("docs/"):
                assert (BENCHMARK / entry.filename).read_bytes() == raw
            payload["benchmark-additions/" + entry.filename] = raw
            modes["benchmark-additions/" + entry.filename] = (entry.external_attr >> 16) & 0o777 or 0o644
    payload["website-tracked-changes.patch"] = patch
    for name in tracked + added:
        p = SITE / name
        assert p.is_file() and not p.is_symlink()
        assert not set(Path(name).parts) & {".git", ".secrets", "__pycache__"}
        assert not name.endswith((".env", ".pyc"))
        payload["website-overlay/" + name] = p.read_bytes()
        modes["website-overlay/" + name] = p.stat().st_mode & 0o777

    public_paths = ["website-overlay/docs/coding-agent-benchmark/index.html",
                    "website-overlay/docs/coding-agent-benchmark/report/index.html",
                    "website-overlay/docs/coding-agent-benchmark/report/INTEGRATED_FINAL_REPORT_REVISED_20261027.md"]
    for name in public_paths:
        assert not re.search(r"career-search|BENCHMARK_TWO_INCIDENTS|WORK_RESULTS_RECONCILIATION",
                             payload[name].decode(), re.I)
    counts = {"text_files": 0, "pdf_files": 0}
    for name, raw in payload.items():
        scan_bytes(name, raw, counts)

    write_json(HERE / "validation/package_validation.json", {
        "status": "PASS", "review_date": "2026-10-30",
        "benchmark_head": BASE, "website_head": SITE_BASE,
        "website_modified_files": len(tracked), "website_new_files": len(added),
        "tracked_patch_applies_to_baseline": True,
        "tracked_patch_output_matches_overlay": True,
        "prior_review_archive_members_preserved": 104,
        "credential_pattern_scan": "PASS; text, extracted PDF text, nested ZIP members",
        "scan_counts_before_current_handoff": counts,
        "public_private_lead_exclusion_check": "PASS",
        "git_indexes_untouched": True, "publication_performed": False,
        "archive_integrity_record": "archive_validation.json, emitted after archive verification"
    })
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.name != "archive_validation.json":
            payload["benchmark-additions/" + str(p.relative_to(BENCHMARK))] = p.read_bytes()
    payload["README_REVIEW_PACKAGE.md"] = ("""# Integrated report and website review candidate

Completed October 30, 2026. Revised review draft; publication is not authorized.

Start with [the completion handoff](benchmark-additions/docs/reports/integrated-final-review-20261029/CONTROLLER_HANDOFF.md).

- [Read the full paper](website-overlay/docs/coding-agent-benchmark/report/index.html).
- [Read the 28-page PDF](website-overlay/docs/coding-agent-benchmark/report/CLAUDE_CODE_BACKEND_BENCHMARK_REVISED_REVIEW_20261027.pdf).
- [Read the website summary](website-overlay/docs/coding-agent-benchmark/index.html).
- [Inspect automated checks](benchmark-additions/docs/reports/integrated-final-review-20261029/validation/website_validation.json).
- [Inspect browser checks](benchmark-additions/docs/reports/integrated-final-review-20261029/validation/browser_review.json).

The website overlay is relative to nwags/nwags.github.io at 83fd7cbe047c06de3f1fd057d4f7a9627c712992.
It contains seven modified and sixteen new files; it is an overlay, not a standalone full website.
Use the exact baseline checkout to supply unchanged styles and homepage assets.
The tracked-only patch omits new files; the overlay includes all 23 candidate files.
The existing paper and PDF remain byte-for-byte the October 27 review draft.
Earlier report packages are preserved under benchmark-additions.

Verification: 525 automated website checks; 176 scientific fields; zero mismatches.
Desktop and embedded 375px/768px browser checks and the PDF link passed.
All sixteen live benchmark dashboard surfaces and live DB/R2 checks remain unavailable.
Controller/human acceptance and a final manuscript/PDF release remain pending.
Nothing was committed, pushed, merged, or published. No paid experiment was run.

PACKAGE_CONTENTS_SHA256.csv fingerprints every other archive member.
""").encode()

    for name, raw in payload.items():
        if name not in {"website-tracked-changes.patch"}:
            scan_bytes(name, raw, {"text_files": 0, "pdf_files": 0})
        parts = Path(name).parts
        assert not Path(name).is_absolute() and ".." not in parts
        assert not set(parts) & {".git", ".secrets", "__pycache__"}
    manifest = io.StringIO(newline="")
    writer = csv.writer(manifest)
    writer.writerow(["archive_path", "bytes", "sha256", "file_mode"])
    writer.writerows((name, len(raw), digest(raw), format(modes.get(name, 0o644), "04o")) for name, raw in sorted(payload.items()))
    payload["PACKAGE_CONTENTS_SHA256.csv"] = manifest.getvalue().encode()

    OUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=8) as z:
        for name, raw in sorted(payload.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = modes.get(name, 0o644) << 16
            z.writestr(entry, raw)
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None
        assert set(z.namelist()) == set(payload)
        for row in csv.DictReader(io.StringIO(z.read("PACKAGE_CONTENTS_SHA256.csv").decode())):
            raw = z.read(row["archive_path"])
            assert len(raw) == int(row["bytes"]) and digest(raw) == row["sha256"]
            assert (z.getinfo(row["archive_path"]).external_attr >> 16) & 0o777 == int(row["file_mode"], 8)
    summary = {"status": "PASS", "archive": str(OUT), "archive_bytes": OUT.stat().st_size,
               "archive_sha256": digest(OUT.read_bytes()), "archive_members": len(payload),
               "archive_crc_and_fingerprints_verified": True, "website_overlay_files": 23,
               "credential_pattern_scan": "PASS", "private_lead_exclusion": "PASS",
               "scientific_fields": 176, "scientific_mismatches": 0,
               "automated_website_checks": 525, "publication_performed": False}
    write_json(HERE / "validation/archive_validation.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
