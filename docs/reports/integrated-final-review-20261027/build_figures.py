#!/usr/bin/env python3
"""Generate publication figures from the companion offline analytical tables."""
from __future__ import annotations
import csv
import hashlib
import json
import os
from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.ticker import FuncFormatter

HERE = Path(__file__).resolve().parent
VAL = HERE / "validation"
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 14, "axes.titlesize": 18,
                     "axes.labelsize": 14, "axes.spines.top": False, "axes.spines.right": False,
                     "svg.fonttype": "none", "savefig.facecolor": "white"})
BLUE, TEAL, INK = "#215b85", "#198078", "#19334a"
NAMES = {
    "router-kimi-k3": "Kimi K3", "router-gpt-5.5": "GPT-5.5", "router-deepseek-flash": "DeepSeek Flash",
    "router-anthropic-fable-5": "Fable 5", "router-anthropic-opus": "Opus", "router-gpt-5.4": "GPT-5.4",
    "router-gemini-3.1-pro": "Gemini 3.1 Pro", "router-glm-5.2": "GLM 5.2", "router-deepseek-pro": "DeepSeek Pro",
    "router-glm-5.1": "GLM 5.1", "router-grok-build-0.1": "Grok Build 0.1", "router-qwen-3.7-plus": "Qwen 3.7 Plus",
    "router-kimi-k2.6": "Kimi K2.6", "router-anthropic-sonnet": "Sonnet", "router-anthropic-haiku-sanitized": "Haiku (sanitized)",
    "router-gemini-flash": "Gemini Flash",
}


def rows(name):
    with (VAL / name).open(newline="") as f:
        return list(csv.DictReader(f))


def save(fig, stem):
    for ext in ["png", "svg"]:
        buffer = BytesIO()
        fig.savefig(buffer, format=ext, dpi=210, bbox_inches="tight", pad_inches=0.13)
        data = buffer.getvalue()
        dest = FIG / (stem + "." + ext)
        temp = dest.with_suffix(dest.suffix + ".tmp")
        with temp.open("wb") as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        temp.replace(dest)
        if dest.read_bytes() != data:
            raise IOError(f"Figure write verification failed: {dest}")
    plt.close(fig)


def architecture():
    fig, ax = plt.subplots(figsize=(11.5, 6.1))
    ax.set(xlim=(0, 11.5), ylim=(0, 6.1)); ax.axis("off")
    def box(x, y, w, h, text, color="#edf3f7"):
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.08", facecolor=color, edgecolor="#9ab1c1", lw=1)
        ax.add_patch(p); ax.text(x+w/2, y+h/2, text, ha="center", va="center", color=INK, fontsize=12.50)
    def arrow(a, b, dashed=False):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=13, lw=1.2, color="#526d80", linestyle="--" if dashed else "-"))
    ax.text(.1, 5.84, "Execution and scoring", fontsize=18.85, fontweight="bold", color=INK)
    box(.1,4.35,1.8,1.0,"Phase, arm\nand task\nconfiguration")
    box(2.35,4.35,1.8,1.0,"Harbor\nTrial\norchestration")
    box(4.6,4.35,1.8,1.0,"Claude Code\nagent in\ncontainer")
    box(6.85,4.35,1.8,1.0,"LiteLLM\ngateway\nHaiku proxy*")
    box(9.1,4.35,2.1,1.0,"Backend\nprovider API\n(model)")
    for x in [1.9,4.15,6.4,8.65]: arrow((x,4.85),(x+.43,4.85))
    ax.text(7.95,4.05,"Model responses return to the agent",ha="center",fontsize=12.32,color="#526d80")
    box(4.6,2.7,1.8,.9,"Terminal tools\nTask workspace", "#edf5f1")
    box(6.85,2.7,1.8,.9,"Task-specific\nverifier tests", "#edf5f1")
    box(9.1,2.7,2.1,.9,"Raw reward\nand exceptions", "#edf5f1")
    arrow((5.5,4.35),(5.5,3.65)); arrow((6.4,3.15),(6.82,3.15)); arrow((8.65,3.15),(9.07,3.15))
    ax.text(.1,2.0,"Evidence and presentation",fontsize=18.85,fontweight="bold",color=INK)
    box(.1,.65,2.0,1.0,"Results and logs\nTranscripts\nTrajectories")
    box(2.75,.65,2.3,1.0,"PostgreSQL\nRun/trial metadata\nR2 artifact storage")
    box(5.7,.65,2.3,1.0,"Frozen reviews\nUsage and cost\nreconciliation")
    box(8.65,.65,2.55,1.0,"Reports\nDashboard\nEvidence display")
    for a,b in [(2.1,2.72),(5.05,5.67),(8,8.62)]: arrow((a,1.15),(b,1.15))
    arrow((10.15,2.7),(3.9,1.7),True)
    ax.text(.1,.18,"* Haiku request proxy precedes LiteLLM. Reports do not rescore trials.",fontsize=12.18,color="#526d80")
    save(fig,"figure_01_architecture")


def outcomes(arms):
    fig, (a,b) = plt.subplots(1,2,figsize=(10.5,7.2),gridspec_kw={"width_ratios":[1.9,1]},sharey=True)
    y=np.arange(len(arms)); names=[NAMES[r["arm_id"]] for r in arms]
    a.barh(y-.16,[int(r["raw_successes"]) for r in arms],height=.29,color=BLUE,label="Raw verifier success")
    a.barh(y+.16,[int(r["clean_successes"]) for r in arms],height=.29,color=TEAL,label="Clean success")
    for i,r in enumerate(arms):
        a.text(int(r["raw_successes"])+.8,i,f"{r['raw_successes']} / {r['clean_successes']}",va="center",fontsize=11.60)
    a.set(yticks=y,yticklabels=names,xlim=(0,60),xlabel="Successes out of 60 selected trials",title="Raw and clean outcomes")
    a.invert_yaxis(); a.grid(axis="x",alpha=.2); a.set_axisbelow(True); a.legend(loc="lower right",fontsize=11.60)
    times=[float(r["median_retained_runtime_seconds"])/60 for r in arms]
    b.scatter(times,y,s=42,color=INK)
    for i,t in enumerate(times):b.text(t+.35,i,f"{t:.1f}",va="center",fontsize=11.60)
    b.set(xlim=(0,19),xlabel="Median runtime (minutes)",title="Trial runtime")
    b.grid(axis="x",alpha=.2); b.tick_params(axis="y",left=False,labelleft=False)
    fig.tight_layout(w_pad=2)
    save(fig,"figure_02_quality_runtime")


def frontier(arms):
    fig,(ax,key)=plt.subplots(1,2,figsize=(11,5.8),gridspec_kw={"width_ratios":[1.9,1]})
    key.axis("off")
    for i,r in enumerate(arms,1):
        x=float(r["selected_cost_usd"]); y=int(r["raw_successes"])/60*100
        billed=bool(r["provider_billed_cost_usd"])
        marker="o" if billed else "s" if r["selected_relation"]=="exact" else "D" if r["selected_relation"]=="estimate" else "^"
        color=TEAL if i in [1,3] else BLUE
        ax.scatter(x,y,marker=marker,s=105,c=color,edgecolor="white",linewidth=.8,zorder=3)
        offsets={4:(8,-14),5:(-12,10),6:(-12,7),7:(-12,-14),8:(-12,8),9:(5,8),10:(-12,8),11:(5,-15)}
        ax.annotate(str(i),(x,y),textcoords="offset points",xytext=offsets.get(i,(6,7)),fontsize=13.05,color=INK)
        key.text(.0,.97-(i-1)*.056,f"{i:>2}   {NAMES[r['arm_id']]}",va="top",fontsize=13.49,color=INK)
    points=[(float(r["selected_cost_usd"]),int(r["raw_successes"])/60*100) for r in arms if r["arm_id"] in ["router-deepseek-flash","router-kimi-k3"]]
    points.sort();ax.plot(*zip(*points),linestyle="--",color=TEAL,lw=1.4,zorder=1)
    ax.set(xscale="log",xlim=(.8,95),ylim=(15,90),xlabel="Selected cost for 60 trials (USD, logarithmic scale)",ylabel="Raw success rate (%)",title="Cost, quality and strength of cost evidence")
    ax.set_xticks([1,2,5,10,20,50]);ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f"${x:.2f}"));ax.grid(alpha=.2)
    handles=[Line2D([0],[0],marker=m,color="none",markerfacecolor=BLUE,label=l,markersize=7) for m,l in [("o","Exact provider bill"),("s","Exact retained-usage reconstruction"),("D","Qualified estimate"),("^","Retained-accounting lower bound")]]
    fig.legend(handles=handles,loc="lower center",bbox_to_anchor=(.5,-.015),ncol=2,fontsize=12.04,frameon=False)
    fig.tight_layout(rect=(0,.09,1,1),w_pad=2)
    save(fig,"figure_04_quality_cost")


def failures(arms):
    cats=[("verifier_task_failure","Verifier/task", "#4477aa"),("timeout_after_meaningful_activity","Timeout after activity", "#ddaa33"),
          ("provider_policy_refusal","Policy refusal", "#bb5566"),("invalid_response_path","Invalid response", "#aa3377"),
          ("missing_required_output","Missing output", "#66ccee"),("extraneous_output_artifacts","Extra artifacts", "#228833"),
          ("unknown_or_incomplete_evidence","Unknown/incomplete", "#9b9b9b")]
    data={(r["arm_id"],r["category"]):int(r["count"]) for r in rows("failure_composition_by_arm.csv")}
    fig,ax=plt.subplots(figsize=(10.8,7.2));y=np.arange(len(arms));left=np.zeros(len(arms))
    for cat,label,color in cats:
        v=np.array([data.get((a["arm_id"],cat),0) for a in arms]);ax.barh(y,v,left=left,color=color,label=label,height=.64)
        for i,n in enumerate(v):
            if n>=3:ax.text(left[i]+n/2,i,str(n),ha="center",va="center",fontsize=11.60,color="white" if color in ["#4477aa","#bb5566","#aa3377","#228833"] else INK)
        left+=v
    for i,a in enumerate(arms):ax.text(left[i]+.6,i,f"{int(left[i])} fail; {a['not_recorded']} NR",va="center",fontsize=11.60)
    ax.set(yticks=y,yticklabels=[NAMES[a["arm_id"]] for a in arms],xlim=(0,58),xlabel="Explicit raw failures out of 60 selected trials",title="Failure mechanisms vary across routes")
    ax.invert_yaxis();ax.grid(axis="x",alpha=.15);ax.set_axisbelow(True)
    ax.legend(loc="upper center",bbox_to_anchor=(.5,-.10),ncol=3,fontsize=11.60,frameon=False)
    fig.tight_layout(rect=(0,.06,1,1))
    save(fig,"figure_03_failure_composition")


def families(arms):
    names=["build-packaging","concurrency-async","data-processing","database-storage","language-implementation","ml-scientific","optimization-finance","security-crypto","systems-low-level","web-networking"]
    short=["Build\n(2)","Async\n(1)","Data\n(1)","DB\n(2)","Lang.\n(1)","ML\n(4)","Optim.\n(1)","Sec.\n(4)","Sys.\n(2)","Web\n(2)"]
    data={(r["arm_id"],r["family"]):r for r in rows("task_family_profiles.csv") if r["scope"]=="phase3-extended"}
    v=np.array([[int(data[(a["arm_id"],f)]["raw_successes"])/int(data[(a["arm_id"],f)]["trials"])*100 for f in names] for a in arms])
    fig,ax=plt.subplots(figsize=(11.5,7.2));im=ax.imshow(v,cmap="YlGnBu",vmin=0,vmax=100,aspect="auto")
    for i,a in enumerate(arms):
        for j,f in enumerate(names):
            r=data[(a["arm_id"],f)];ax.text(j,i,f"{r['raw_successes']}/{r['trials']}",ha="center",va="center",fontsize=12.04,color="white" if v[i,j]>=65 else INK)
    ax.set(yticks=np.arange(len(arms)),yticklabels=[NAMES[a["arm_id"]] for a in arms],xticks=np.arange(10),xticklabels=short,title="Task-family profiles: observed raw successes / trials")
    ax.tick_params(axis="x",length=0);ax.tick_params(axis="y",length=0)
    ax.set_xticks(np.arange(-.5,10,1),minor=True);ax.set_yticks(np.arange(-.5,16,1),minor=True);ax.grid(which="minor",color="white",linewidth=1.2);ax.tick_params(which="minor",length=0)
    cb=fig.colorbar(im,ax=ax,fraction=.025,pad=.025);cb.set_label("Raw success (%)")
    fig.tight_layout();save(fig,"figure_05_task_families")


def cache():
    usage=rows("token_usage_scopes.csv");order=["router-gpt-5.4","router-gpt-5.5","router-deepseek-flash","router-deepseek-pro","router-gemini-3.1-pro","router-gemini-flash","router-kimi-k3"]
    usage=sorted(usage,key=lambda r:order.index(r["arm_id"]))
    fig,ax=plt.subplots(figsize=(10.5,4.9));y=np.array([0,1,2,3,4,5,6.65]);labels=[]
    for i,r in enumerate(usage):
        pct=float(r["cache_share_percent"]);provider=r["authority"]=="provider_aggregate";broader=r["scope"]!="selected_run"
        ax.barh(y[i],pct,height=.62,color="#7e8b95" if broader else BLUE if provider else TEAL)
        ax.barh(y[i],100-pct,left=pct,height=.62,color="#e3e9ee")
        ax.text(pct-1.3,y[i],f"{pct:.2f}%",ha="right",va="center",color="white",fontsize=14.50)
        label=NAMES[r["arm_id"]]+(" - provider aggregate" if provider else " - broader log, unallocated" if broader else " - retained harness")
        labels.append(label)
    ax.axhline(5.85,color="#a8b6c1",linestyle="--",lw=1)
    ax.set(yticks=y,yticklabels=labels,xlim=(0,102),xlabel="Cached input as a share of total input (%)",title="Cache use is substantial; evidence scope matters")
    ax.invert_yaxis();ax.grid(axis="x",alpha=.15);ax.set_axisbelow(True)
    fig.tight_layout();save(fig,"figure_06_cache_evidence")


def historical_tokens(arms):
    data={r["arm_id"]:r for r in rows("historical_token_and_spend_shares.csv")};arms=[a for a in arms if a["arm_id"] in data]
    fig,ax=plt.subplots(figsize=(10.5,6.6));y=np.arange(len(arms))
    for i,a in enumerate(arms):
        r=data[a["arm_id"]];tokens=float(r["unclean_token_share"])*100;cost=float(r["unclean_spend_share"])*100
        ax.plot([tokens,cost],[i,i],color="#bdcbd4",lw=2)
        ax.scatter(tokens,i,color=BLUE,marker="o",s=45,label="Input + output token share" if i==0 else None,zorder=3)
        ax.scatter(cost,i,color="#bb5566",marker="D",s=40,label="Historical adjusted cost share" if i==0 else None,zorder=3)
    ax.set(yticks=y,yticklabels=[NAMES[a["arm_id"]] for a in arms],xlim=(0,85),xlabel="Share consumed by non-clean outcomes (%)",title="Token volume and dollar cost tell different stories")
    ax.invert_yaxis();ax.grid(axis="x",alpha=.2);ax.legend(loc="upper center",bbox_to_anchor=(.5,-.12),ncol=2,frameon=False,fontsize=12.32);fig.tight_layout(rect=(0,.05,1,1))
    save(fig,"figure_07_historical_token_spend")


def main():
    arms=rows("arm_comparison.csv")
    architecture();outcomes(arms);frontier(arms);failures(arms);families(arms);cache();historical_tokens(arms)
    manifest=[]
    for p in sorted(FIG.iterdir()):
        if p.suffix in {".png",".svg"}:
            manifest.append({"file": str(p.relative_to(HERE)), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    (VAL/"figure_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(f"Generated {len(manifest)} figure assets (7 PNG + 7 SVG).")


if __name__=="__main__":main()
