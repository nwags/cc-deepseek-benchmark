#!/usr/bin/env python3
"""Verify manuscript/data alignment, figure integrity, PDF text, and preservation.

No network, model execution, migrations, or database operations. Run after
validate_report.py, analyze_revision.py, build_figures.py, and build_pdf.py.
"""
from __future__ import annotations
import ast
import csv
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pdfplumber
from PIL import Image
from pypdf import PdfReader

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
VAL=HERE/"validation"
MD=HERE/"INTEGRATED_FINAL_REPORT_REVISED_20261027.md"
PDF=HERE/"output/pdf/CLAUDE_CODE_BACKEND_BENCHMARK_REVISED_REVIEW_20261027.pdf"
BASE="79f790fdd9067e33a29e0409c15f8890068ff22d"
CHECKS=[]


def check(name,condition,detail=None):
    CHECKS.append({"check":name,"passed":bool(condition),"detail":detail})
    if not condition:raise AssertionError(f"{name}: {detail}")


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path):
    with path.open(newline="") as f:return list(csv.DictReader(f))


def write_csv(name,data):
    with (VAL/name).open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)


def text(nodes):
    out=""
    for n in nodes:
        t,c=n["t"],n.get("c")
        if t=="Str":out+=c
        elif t in {"Space","SoftBreak","LineBreak"}:out+=" "
        elif t=="Code":out+=c[1]
        elif t in {"Strong","Emph"}:out+=text(c)
        elif t in {"Link","Image"}:out+=text(c[1])
        elif t=="Span":out+=text(c[1])
        else:raise ValueError(t)
    return out


def tables(doc):
    out=[]
    for b in doc["blocks"]:
        if b["t"]!="Table":continue
        c=b["c"];rows=c[3][1]+[r for body in c[4] for r in body[2]+body[3]]+c[5][1]
        out.append([[" ".join(text(block["c"]) for block in cell[4] if block["t"] in {"Para","Plain"}) for cell in row[1]] for row in rows])
    return out


def money(value):return "$"+format(Decimal(value).quantize(Decimal(".01"),rounding=ROUND_HALF_UP),",.2f")


def main():
    source=MD.read_text()
    doc=json.loads(subprocess.check_output(["pandoc","-f","gfm-tex_math_dollars","-t","json",str(MD)],text=True))
    tab=tables(doc)
    check("required paper structure",all(h in source for h in ["## Abstract","## 1. Introduction","## 2. Methods","## 3. Results","## 4. Discussion","## 5. Challenges","## 6. Conclusion"]))
    check("main paper ends in conclusion before appendices",source.index("## 6. Conclusion")<source.index("## Appendix A"))
    figures=re.findall(r'!\[[^\]]*\]\(([^)]+)\)',source)
    check("seven embedded figures",len(figures)==len(set(figures))==7)
    check("sequential figure captions",re.findall(r'\*Figure (\d+)\.',source)==list("1234567"))
    amounts=re.findall(r'\$\d[\d,]*(?:\.\d+)?',source)
    check("all displayed manuscript costs have exactly two decimals",bool(amounts) and all(re.fullmatch(r'\$\d[\d,]*\.\d{2}',a) for a in amounts),len(amounts))
    refs=json.loads((VAL/"source_reference_map.json").read_text())
    inventory={r["path"]:r for r in csv_rows(VAL/"source_inventory.csv")}
    definitions=dict(re.findall(r'^\[(S\d+)\]: (\S+)$',source,re.M))
    check("41 unique reference definitions",len(refs)==len(definitions)==41 and refs.keys()==definitions.keys())
    for ref,path in refs.items():
        expected=f"https://github.com/nwags/cc-deepseek-benchmark/blob/{BASE}/{path}"
        check(f"pinned reference and source hash: {ref}",definitions[ref]==expected and (ROOT/path).is_file() and inventory[path]["sha256"]==sha(ROOT/path))
    cost_table=next(t for t in tab if t[0][:2]==["Arm","Selected arm cost"])
    arms=csv_rows(VAL/"arm_comparison.csv")
    check("all 16 arm cost/clean ratios round from exact calculations",len(cost_table)==17 and all(
        row[1]==money(arm["selected_cost_usd"]) and row[3]==money(arm["cost_per_clean_success_ratio_usd"])
        for row,arm in zip(cost_table[1:],arms)))
    totals=json.loads((VAL/"validation_summary.json").read_text())
    check("headline totals remain reproduced",totals["scopes"]["phase3-core"]["trials"]==900 and totals["scopes"]["phase3-core"]["outcomes"]["success"]==515 and totals["scopes"]["phase3-extended"]["trials"]==960 and totals["raw_outcomes"]["success"]==562 and totals["scopes"]["phase3-extended"]["clean_successes"]==543)
    check("selected total is rounded after summing",money(totals["scopes"]["phase3-extended"]["selected_cost_usd"])=="$343.45" and "$343.45" in source)
    for p in figures:
        with Image.open(HERE/p) as im:im.load();check(f"PNG decodes: {p}",im.width>1500 and im.height>800)
    for entry in json.loads((VAL/"figure_manifest.json").read_text()):
        p=HERE/entry["file"]
        check(f"figure manifest: {p.name}",p.stat().st_size==entry["bytes"] and sha(p)==entry["sha256"])
        if p.suffix==".svg":ET.parse(p)
    output=csv_rows(VAL/"output_tokens_by_outcome.csv")
    output_table=next(t for t in tab if t[0][:2]==["Arm","Success observations"])
    name_map={"DeepSeek Flash":"router-deepseek-flash","GPT-5.5":"router-gpt-5.5","Haiku (sanitized)":"router-anthropic-haiku-sanitized","Fable 5":"router-anthropic-fable-5"}
    for row in output_table[1:]:
        aid=name_map[row[0]]
        sr=next(r for r in output if r["arm_id"]==aid and r["raw_outcome_group"]=="success")
        fr=next(r for r in output if r["arm_id"]==aid and r["raw_outcome_group"]=="non_success")
        check(f"output medians and denominators: {aid}",row[1]==f"{sr['positive_retained_usage_trials']}/{sr['selected_trials_in_group']}" and row[3]==f"{fr['positive_retained_usage_trials']}/{fr['selected_trials_in_group']}" and Decimal(row[2].replace(",",""))==Decimal(sr["median_output_tokens_given_positive_retained_usage"]) and Decimal(row[4].replace(",",""))==Decimal(fr["median_output_tokens_given_positive_retained_usage"]))
    claims=next(t for t in tab if t[0][0]=="Claim")
    check("23 evidence/claim rows",len(claims)==24 and [re.match(r'C\d+',r[0])[0] for r in claims[1:]]==[f"C{i:02}" for i in range(1,24)])
    claim_rows=[]
    for row in claims[1:]:
        source_refs=[r for r in re.findall(r'\bS\d{2}\b',row[2]) if r in refs]
        paths=[refs[r] for r in source_refs]
        claim_rows.append(dict(zip(["claim","status","authority_reproduction","practical_limit"],row))|{
            "source_paths":";".join(paths),"last_change_commits":";".join(inventory[p]["last_change_commit"] for p in paths),"baseline_commit":BASE})
    write_csv("evidence_claim_matrix.csv",claim_rows)
    tests=next(t for t in tab if t[0][0]=="Question")
    checks_table=next(t for t in tab if t[0][0]=="Check")
    write_csv("tested_not_tested_matrix.csv",[{"kind":"experiment","question_check":r[0],"status_or_coverage":r[1],"evidence_limit":""} for r in tests[1:]]+[{"kind":"review","question_check":r[0],"status_or_coverage":r[1],"evidence_limit":r[2]} for r in checks_table[1:]])
    check("sixteen dashboard surfaces remain unavailable",len(csv_rows(VAL/"dashboard_surface_review.csv"))==16 and all(r["live_rendered_status"]=="unavailable" for r in csv_rows(VAL/"dashboard_surface_review.csv")))
    check("private recollections and private repository paths excluded",not re.search(r'career-search|BENCHMARK_TWO_INCIDENTS|WORK_RESULTS_RECONCILIATION|sponsor.?remark',source,re.I))
    reader=PdfReader(PDF)
    pdftext="\n".join(p.extract_text() or "" for p in reader.pages).replace("\u200b","")
    check("PDF contains every major section",all(s in pdftext for s in ["Abstract","1. Introduction","2. Methods","3. Results","4. Discussion","5. Challenges","6. Conclusion","Appendix B","Appendix D"]))
    check("PDF retains headline and token findings",all(s in pdftext for s in ["$343.45","562","543","868","35,036","5,442.5"]))
    check("PDF displayed currency precision",all(re.fullmatch(r'\$\d[\d,]*\.\d{2}',a) for a in re.findall(r'\$\d[\d,]*(?:\.\d+)?',pdftext)))
    embedded_images=sum(len(p.images) for p in reader.pages)
    check("PDF contains seven figures",embedded_images==7,embedded_images)
    uris={str(a.get_object().get("/A",{}).get("/URI")) for p in reader.pages for a in p.get("/Annots",[])}
    check("all 41 public source links embedded in PDF",set(definitions.values()).issubset(uris),len(uris))
    overflow=[]
    with pdfplumber.open(PDF) as p:
        for i,page in enumerate(p.pages,1):
            for char in page.chars:
                if char["text"].strip() and (char["x0"]<39 or char["x1"]>page.width-39 or char["top"]<12 or char["bottom"]>page.height-10):
                    overflow.append({"page":i,"text":char["text"],"x0":char["x0"],"x1":char["x1"]})
    check("PDF text stays within page boundaries",not overflow,overflow[:10])
    original=ROOT/"docs/reports/integrated-final-review-20261024"
    preserved=csv_rows(original/"PACKAGE_CONTENTS_SHA256.csv")
    for entry in preserved:
        path=entry.get("repository_relative_path") or entry.get("path") or entry.get("file") or entry.get("relative_path")
        target=(ROOT/path) if entry.get("repository_relative_path") else (original/path)
        check(f"original review preserved: {path}",sha(target)==entry["sha256"])
    check("tracked sources and frozen outputs unchanged",not subprocess.check_output(["git","diff","HEAD","--name-only"],cwd=ROOT,text=True).strip())
    for p in HERE.glob("*.py"):ast.parse(p.read_text());check(f"Python syntax: {p.name}",True)
    summary={"status":"PASS","checks_passed":len(CHECKS),"manuscript_words":len(source.split()),"figures":7,"pdf_pages":len(reader.pages),"source_references":41,"claim_matrix_rows":23,
             "displayed_currency_policy":"nearest_cent_decimal_half_up; full precision retained in machine-readable evidence",
             "tracked_source_changes":[],"original_review_preserved":True,"paid_or_database_operations":False,
             "visual_review_record":"visual_review.json (manual rendered-page assessment, separate from these automated checks)"}
    (VAL/"presentation_validation.json").write_text(json.dumps(summary,indent=2)+"\n")
    (VAL/"presentation_checks.json").write_text(json.dumps(CHECKS,indent=2)+"\n")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
