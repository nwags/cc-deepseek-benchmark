#!/usr/bin/env python3
"""Read-only scientific/content checks for the local website review candidate.

Writes validation results only beside this script. It makes no network calls,
runs no benchmark/provider/DB action, and does not publish or modify site files.
"""
from __future__ import annotations
import argparse
import ast
import csv
import hashlib
import json
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image
from pypdf import PdfReader

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/"validation"
REPORT=ROOT/"docs/reports/integrated-final-review-20261027"
BASE="79f790fdd9067e33a29e0409c15f8890068ff22d"
SITE_BASE="83fd7cbe047c06de3f1fd057d4f7a9627c712992"
CHECKS=[]


def check(name,condition,detail=None):
    CHECKS.append({"check":name,"passed":bool(condition),"detail":detail})
    if not condition:raise AssertionError(f"{name}: {detail}")


def rows(path):
    with path.open(newline="") as f:return list(csv.DictReader(f))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def money(value):return "$"+format(Decimal(value).quantize(Decimal(".01"),rounding=ROUND_HALF_UP),",.2f")


class Page(HTMLParser):
    def __init__(self,path):
        super().__init__(convert_charrefs=True)
        self.path=path;self.refs=[];self.ids=set();self.images=[];self.text=[];self.scripts=[];self.in_script=False;self.in_style=False
        self.current_script=[];self.current_row=None;self.current_cell=None;self.arm_rows={};self.figures=0
        self.feed(path.read_text())
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get("id"):self.ids.add(a["id"])
        if tag in {"a","link"} and a.get("href"):self.refs.append(a["href"])
        if tag=="img":self.images.append(a);self.refs.append(a["src"])
        if tag=="figure":self.figures+=1
        if tag=="script":self.in_script=True;self.current_script=[]
        if tag=="style":self.in_style=True
        if tag=="tr" and a.get("data-arm"):self.current_row=(a["data-arm"],[])
        if tag=="td" and self.current_row:self.current_cell=[]
    def handle_data(self,data):
        if self.in_script:self.current_script.append(data)
        elif not self.in_style:self.text.append(data)
        if self.current_cell is not None:self.current_cell.append(data)
    def handle_endtag(self,tag):
        if tag=="script":self.scripts.append("".join(self.current_script));self.in_script=False
        if tag=="style":self.in_style=False
        if tag=="td" and self.current_cell is not None:
            self.current_row[1].append(" ".join(self.current_cell).strip());self.current_cell=None
        if tag=="tr" and self.current_row:
            self.arm_rows[self.current_row[0]]=self.current_row[1];self.current_row=None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root",type=Path,required=True)
    args=parser.parse_args();site=args.site_root.resolve();OUT.mkdir(exist_ok=True)
    check("benchmark remains on pinned live baseline",subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==BASE)
    check("website remains based on inspected main",subprocess.check_output(["git","rev-parse","HEAD"],cwd=site,text=True).strip()==SITE_BASE)
    check("tracked benchmark/frozen sources unchanged",not subprocess.check_output(["git","diff","HEAD","--name-only"],cwd=ROOT,text=True).strip())
    for dirname in ["integrated-final-review-20261024","integrated-final-review-20261027"]:
        for entry in rows(ROOT/"docs/reports"/dirname/"PACKAGE_CONTENTS_SHA256.csv"):
            p=ROOT/entry["repository_relative_path"]
            check("preserved report file: "+str(p.relative_to(ROOT)),sha(p)==entry["sha256"])
    reportroot=site/"docs/coding-agent-benchmark/report"
    manifest=json.loads((reportroot/"report-manifest.json").read_text())
    check("review gate remains visible in metadata",manifest["publication_authorized"] is False and manifest["report_status"]=="revised_review_draft_pending_controller_human")
    for entry in manifest["files"]:
        p=reportroot/entry["path"]
        check("website report fingerprint: "+entry["path"],p.stat().st_size==entry["bytes"] and sha(p)==entry["sha256"])
    check("PDF identity and page count",len(PdfReader(reportroot/"CLAUDE_CODE_BACKEND_BENCHMARK_REVISED_REVIEW_20261027.pdf").pages)==28 and manifest["source_pdf_sha256"]==sha(REPORT/"output/pdf/CLAUDE_CODE_BACKEND_BENCHMARK_REVISED_REVIEW_20261027.pdf"))
    check("manuscript identity",manifest["source_report_sha256"]==sha(REPORT/"INTEGRATED_FINAL_REPORT_REVISED_20261027.md"))

    authority=json.loads(subprocess.check_output(["git","show",BASE+":results/phase3/reporting/phase3_current_reviewed_comparison_20260825.json"],cwd=ROOT,text=True))
    public=json.loads((site/"docs/coding-agent-benchmark/public-benchmark-data.json").read_text())
    pub={r["armId"]:r for r in public["arms"]};auth={r["armId"]:r for r in authority["scopes"]["phase3-extended"]["arms"]}
    fields=["trialCount","successCount","cleanSuccessCount","passRate","selectedCostUsd","selectedCostRelation","selectedCostBasis","selectedCostConfidence","providerBillingReconciliationStatus","selectedTrialCostAllocationStatus","selectedOutcomeCostAllocationStatus"]
    check("exact 16-arm public membership",pub.keys()==auth.keys() and len(pub)==16)
    for aid in pub:
        for field in fields:check(f"scientific field unchanged: {aid}/{field}",pub[aid][field]==auth[aid][field])
        check(f"canonical provider ID unchanged: {aid}",pub[aid]["provider"]==auth[aid]["provider"])
    check("both Kimi display aliases normalized",pub["router-kimi-k3"]["providerLabel"]==pub["router-kimi-k2.6"]["providerLabel"]=="Moonshot / Kimi")
    check("extended quality and selected cost totals",sum(r["successCount"] for r in pub.values())==562 and sum(r["cleanSuccessCount"] for r in pub.values())==543 and sum(Decimal(r["selectedCostUsd"]) for r in pub.values())==Decimal("343.4494304572"))
    check("report relation counts preserved",Counter(r["selectedCostRelation"] for r in pub.values())=={"exact":4,"estimate":7,"lower_bound":5})
    check("two billed exact relations",sum(r["selectedCostRelation"]=="exact" and r["selectedCostBasis"]=="provider_billed" for r in pub.values())==2)

    pages={}
    def page(path):
        if path not in pages:pages[path]=Page(path)
        return pages[path]
    inspect=[site/"index.html",site/"resume.html",site/"docs/coding-agent-benchmark/index.html",reportroot/"index.html",site/"docs/coding-agent-benchmark/phase3-selected-cost-frontier.html",site/"docs/coding-agent-benchmark/phase3-adjusted-cost-frontier.html"]
    for p in inspect:
        doc=page(p)
        for ref in doc.refs:
            u=urlsplit(ref)
            if u.scheme or u.netloc:continue
            target=(site/unquote(u.path).lstrip("/")) if u.path.startswith("/") else ((p.parent/unquote(u.path)) if u.path else p)
            target=target.resolve()
            if target.is_dir():target=target/"index.html"
            check(f"local link/asset: {p.relative_to(site)} -> {ref}",target.is_file(),str(target.relative_to(site)) if target.is_relative_to(site) else str(target))
            if u.fragment and target.suffix==".html":check(f"section target: {ref}",unquote(u.fragment) in page(target).ids)
        for image in doc.images:
            check("image alternative text: "+image["src"],bool(image.get("alt")))
        if p.is_relative_to(site/"docs/coding-agent-benchmark"):
            amounts=re.findall(r'\$\d[\d,]*(?:\.\d+)?'," ".join(doc.text))
            check("visible benchmark cost precision: "+str(p.relative_to(site)),all(re.fullmatch(r'\$\d[\d,]*\.\d{2}',v) for v in amounts),len(amounts))
    paper=page(reportroot/"index.html")
    summary=page(site/"docs/coding-agent-benchmark/index.html")
    check("full paper contains seven figures",paper.figures==7 and len(paper.images)==7)
    check("paper section links include conclusion and matrices",all(x in paper.ids for x in ["abstract","2-methods","6-conclusion","appendix-b-evidence-and-claim-matrix","appendix-c-tested-and-not-tested-matrix"]))
    check("summary and paper content have no JavaScript dependency",not summary.scripts and not paper.scripts)
    check("all 16 static comparison rows",len(summary.arm_rows)==16 and set(summary.arm_rows)==set(pub))
    armrows={r["arm_id"]:r for r in rows(REPORT/"validation/arm_comparison.csv")}
    for aid,cells in summary.arm_rows.items():
        a=pub[aid];r=armrows[aid]
        check("static table numbers and label: "+aid,cells[1]==a["providerLabel"] and cells[2]==str(a["successCount"]) and cells[3]==str(a["cleanSuccessCount"]) and cells[4]==money(a["selectedCostUsd"]) and cells[5]==money(r["cost_per_clean_success_ratio_usd"]))
    check("failure and access limits retained",all(t in " ".join(summary.text) for t in ["370 explicit raw failures","28 not-recorded outcomes","19 timeout-bearing trials succeeded","all 16 live dashboard surfaces"]))
    check("thinking/final-token limit retained",all(t in " ".join(summary.text) for t in ["868 of 960","reasoning-versus-final-answer token split","not token counts"]))
    check("private leads not copied into website",not re.search(r'career-search|BENCHMARK_TWO_INCIDENTS|WORK_RESULTS_RECONCILIATION|sponsor.?remark'," ".join(summary.text+paper.text),re.I))

    for p in (reportroot/"figures").glob("*.png"):
        with Image.open(p) as im:im.load();check("report figure decodes: "+p.name,im.width>1500)
    svg=ET.parse(site/"assets/coding-agent-benchmark/phase3-selected-cost-frontier-preview.svg").getroot()
    point_nodes=[g for g in svg if g.tag.endswith("}g") and len(g)>1 and g[0].tag.endswith("}title")]
    check("static preview has 16 points",len(point_nodes)==16)
    shapes=Counter("circle" if n[1].tag.endswith("}circle") else "diamond" if n[1].get("transform","").startswith("rotate") else "square" if n[1].tag.endswith("}rect") else "triangle" for n in point_nodes)
    check("static marker evidence classes",shapes=={"circle":2,"square":2,"diamond":7,"triangle":5},dict(shapes))
    kimi=[n for n in point_nodes if (n[0].text or "").startswith(("Kimi K3:","Kimi K2.6:"))]
    check("static Kimi colors match",len(kimi)==2 and all(n[1].get("fill")=="#c2410c" for n in kimi))
    with zipfile.ZipFile(reportroot/"analysis-data.zip") as z:
        check("analytical ZIP integrity and membership",z.testzip() is None and len(z.infolist())==19)
        for entry in z.infolist():check("analytical ZIP preserves source: "+entry.filename,z.read(entry)==(REPORT/entry.filename).read_bytes())

    with tempfile.TemporaryDirectory(prefix="benchmark-site-js-") as temp:
        for i,script in enumerate(page(site/"docs/coding-agent-benchmark/phase3-selected-cost-frontier.html").scripts):
            path=Path(temp)/f"script-{i}.js";path.write_text(script)
            proc=subprocess.run(["node","--check",str(path)],capture_output=True,text=True)
            check("interactive JavaScript syntax",proc.returncode==0,proc.stderr or None)
    for p in [site/"scripts/generate_coding_agent_benchmark_public.py",site/"scripts/prepare_integrated_benchmark_report.py"]:
        ast.parse(p.read_text());check("Python syntax: "+p.name,True)
    for name,command in [
        ("V4 generator",["python3","scripts/generate_coding_agent_benchmark_public.py","--benchmark-repo",str(ROOT),"--check"]),
        ("integrated report builder",["python3","scripts/prepare_integrated_benchmark_report.py","--benchmark-repo",str(ROOT),"--report-dir",str(REPORT),"--check"]),
    ]:
        p=subprocess.run(command,cwd=site,capture_output=True,text=True)
        check("deterministic read-only check: "+name,p.returncode==0,p.stderr.strip() or p.stdout.strip())
    proc=subprocess.run(["git","diff","--check"],cwd=site,capture_output=True,text=True)
    check("website diff whitespace check",proc.returncode==0,proc.stdout or proc.stderr or None)
    summary_out={"status":"PASS","review_date":"2026-10-30","checks_passed":len(CHECKS),"scientific_fields_checked":16*len(fields),"scientific_field_mismatches":0,
                 "report_md_pdf_unchanged":True,"report_figures":7,"pdf_pages":28,"public_site_changed":False,"website_branch":"review/benchmark-report-alignment-20261029",
                 "benchmark_base":BASE,"website_base":SITE_BASE,"static_evidence_markers":dict(shapes),"live_dashboard_surfaces_reviewed":0,"live_dashboard_surfaces_unavailable":16,
                 "browser_qa":"Recorded separately in browser_review.json","release_gate":"Original no-push/no-merge/no-publication restriction remains in force"}
    (OUT/"website_validation.json").write_text(json.dumps(summary_out,indent=2)+"\n")
    (OUT/"website_checks.json").write_text(json.dumps(CHECKS,indent=2)+"\n")
    print(json.dumps(summary_out,indent=2))


if __name__=="__main__":main()
