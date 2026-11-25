#!/usr/bin/env python3
"""Render the authoritative Markdown manuscript and its figures as a PDF.

Requires pandoc (GFM parser), reportlab, Pillow. No network or benchmark calls.
"""
from __future__ import annotations
import html
import json
import re
import subprocess
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage
import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

HERE = Path(__file__).resolve().parent
MD = HERE / "INTEGRATED_FINAL_REPORT_20261124.md"
OUT = HERE / "output" / "pdf" / "CLAUDE_CODE_BACKEND_BENCHMARK_FINAL_20261124.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)
PAGE_W, PAGE_H = A4
LEFT, RIGHT, TOP, BOTTOM = 48, 48, 49, 44
WIDTH = PAGE_W - LEFT - RIGHT
INK = colors.HexColor("#19334a")
BLUE = colors.HexColor("#215b85")

font_dir = Path("/usr/share/fonts/truetype/dejavu")
for name, file in [("Paper", "DejaVuSans.ttf"), ("Paper-Bold", "DejaVuSans-Bold.ttf"),
                   ("Paper-Italic", "DejaVuSans-Oblique.ttf"), ("Paper-BoldItalic", "DejaVuSans-BoldOblique.ttf")]:
    font_path = font_dir / file
    if not font_path.is_file():
        font_path = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / file
    pdfmetrics.registerFont(TTFont(name, str(font_path)))
pdfmetrics.registerFontFamily("Paper", normal="Paper", bold="Paper-Bold", italic="Paper-Italic", boldItalic="Paper-BoldItalic")
styles = {
    "body": ParagraphStyle("body", fontName="Paper", fontSize=9.5, leading=13.5, textColor=INK, spaceAfter=8, splitLongWords=True),
    "caption": ParagraphStyle("caption", fontName="Paper", fontSize=8.1, leading=11, textColor=colors.HexColor("#405e73"), spaceAfter=13),
    "abstract": ParagraphStyle("abstract", fontName="Paper", fontSize=9.2, leading=13, textColor=INK, spaceAfter=10),
    "h1": ParagraphStyle("h1", fontName="Paper-Bold", fontSize=21, leading=25, textColor=INK, spaceAfter=12, keepWithNext=True),
    "h2": ParagraphStyle("h2", fontName="Paper-Bold", fontSize=14, leading=18, textColor=BLUE, spaceBefore=14, spaceAfter=8, keepWithNext=True),
    "h3": ParagraphStyle("h3", fontName="Paper-Bold", fontSize=11.5, leading=15, textColor=INK, spaceBefore=12, spaceAfter=6, keepWithNext=True),
    "h4": ParagraphStyle("h4", fontName="Paper-Bold", fontSize=10, leading=14, textColor=INK, spaceBefore=10, spaceAfter=5, keepWithNext=True),
    "cell": ParagraphStyle("cell", fontName="Paper", fontSize=8, leading=10.7, textColor=INK, splitLongWords=True),
    "cell_small": ParagraphStyle("cell_small", fontName="Paper", fontSize=7.3, leading=9.7, textColor=INK, splitLongWords=True),
    "reference": ParagraphStyle("reference", fontName="Paper", fontSize=8.1, leading=11.3, textColor=INK, spaceAfter=5, splitLongWords=True),
}


def plain(inlines):
    result = ""
    for item in inlines:
        t, c = item["t"], item.get("c")
        if t == "Str": result += c
        elif t in {"Space", "SoftBreak", "LineBreak"}: result += " "
        elif t in {"Strong", "Emph", "SmallCaps", "Strikeout"}: result += plain(c)
        elif t == "Code": result += c[1]
        elif t in {"Link", "Image"}: result += plain(c[1])
    return result


def inline(inlines):
    result = ""
    for item in inlines:
        t, c = item["t"], item.get("c")
        if t == "Str": result += html.escape(c)
        elif t in {"Space", "SoftBreak"}: result += " "
        elif t == "LineBreak": result += "<br/>"
        elif t in {"Strong", "Emph"}: result += ("<b>" if t=="Strong" else "<i>") + inline(c) + ("</b>" if t=="Strong" else "</i>")
        elif t == "Code":
            # Paths/hashes may break across lines; the original Markdown keeps
            # their exact uninterrupted bytes for reproducibility.
            s = c[1]
            s = "\u200b".join(s[i:i+18] for i in range(0,len(s),18)) if len(s)>24 else s
            result += '<font color="#365d76">' + html.escape(s) + '</font>'
        elif t == "Link": result += '<link href="' + html.escape(c[2][0],quote=True) + '" color="#215b85">' + inline(c[1]) + '</link>'
        elif t == "Quoted": result += '&quot;' + inline(c[1]) + '&quot;'
        elif t == "Span": result += inline(c[1])
        else:
            raise ValueError(f"Unsupported inline: {t}")
    return result


def block_text(blocks):
    return "<br/>".join(inline(b["c"]) for b in blocks if b["t"] in {"Plain","Para"})


def table_rows(block):
    c=block["c"]
    head=c[3][1]
    body=[r for tb in c[4] for r in tb[2]+tb[3]]
    foot=c[5][1]
    return head+body+foot, len(head)


def table(block):
    raw, nhead=table_rows(block)
    text_rows=[[block_text(cell[4]) for cell in row[1]] for row in raw]
    n=len(text_rows[0]); headers=[re.sub('<[^>]+>','',s) for s in text_rows[0]]
    weights=None
    if headers[:2]==["Setting","Retained evidence and interpretation"]:weights=[1.1,4]
    elif headers[0]=="Cost term":weights=[1.35,3.75]
    elif headers[0]=="Reviewed scope":weights=[1.15,.4,.5,1.0,.85,1.0,1.0]
    elif headers[0]=="Arm" and n==6:weights=[1.55,.95,.95,.85,.8,1.0]
    elif headers[0]=="Arm" and headers[1]=="Success obs.":weights=[1.4,1.05,1.4,1.15,1.4]
    elif headers[0]=="Arm" and n==5:weights=[1.05,.8,2.4,.8,1.45]
    elif headers[0]=="Claim":weights=[1.7,1.35,1.8,1.7]
    elif headers[0].startswith("Challenge"):weights=[1.2,2.0,1.85]
    elif headers[0]=="Surface":weights=[1.0,1.2,2.4,1.2]
    elif headers[0]=="Phase":weights=[.65,1.65,.75,1.2,.8,1.1]
    elif headers[0]=="Evidence milestone":weights=[1.8,3.2]
    elif headers[0]=="Selected arm" and n==5:weights=[1.05,1.0,.9,1.0,2.0]
    if weights is None:
        weights=[max(6,min(26,len(h)*.4+sum(min(len(re.sub('<[^>]+>','',r[i])),140) for r in text_rows)/len(text_rows)*.25)) for i,h in enumerate(headers)]
    assert len(weights)==n,(headers,weights)
    widths=[WIDTH*w/sum(weights) for w in weights]
    style=styles["cell_small"] if n>=6 else styles["cell"]
    data=[[Paragraph(("<b>"+v+"</b>") if j<nhead else v,style) for v in row] for j,row in enumerate(text_rows)]
    t=Table(data,colWidths=widths,repeatRows=nhead,hAlign="LEFT",splitByRow=1)
    t.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(-1,nhead-1),colors.HexColor("#dce8f0")),
        ("LINEBELOW",(0,nhead-1),(-1,nhead-1),.65,BLUE),("ROWBACKGROUNDS",(0,nhead),(-1,-1),[colors.white,colors.HexColor("#f4f7f9")]),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LINEBELOW",(0,-1),(-1,-1),.4,colors.HexColor("#c1d1dc")),
    ]))
    return [t,Spacer(1,10)]


class Paper(BaseDocTemplate):
    def __init__(self):
        super().__init__(str(OUT),pagesize=A4,leftMargin=LEFT,rightMargin=RIGHT,topMargin=TOP,bottomMargin=BOTTOM,
                         title="Claude Code backend benchmark: quality, cost, and operational risk",author="Claude Code Backend Benchmark project",
                         subject="Retrospective research edition; pinned public evidence; November 24, 2026")
        frame=Frame(LEFT,BOTTOM,WIDTH,PAGE_H-TOP-BOTTOM,id="body",leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="paper",frames=[frame],onPage=self.decorate))
        self.heading_id=0

    def decorate(self,canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor("#ccd9e2"));canvas.setLineWidth(.5)
        canvas.line(LEFT,PAGE_H-32,PAGE_W-RIGHT,PAGE_H-32)
        canvas.setFont("Paper",7.3);canvas.setFillColor(colors.HexColor("#526d80"))
        canvas.drawString(LEFT,PAGE_H-24,"CLAUDE CODE BACKEND BENCHMARK")
        canvas.drawRightString(PAGE_W-RIGHT,PAGE_H-24,"RESEARCH EDITION | 24 NOV 2026")
        canvas.line(LEFT,30,PAGE_W-RIGHT,30)
        canvas.drawString(LEFT,18,"Evidence baseline: main@79f790f | Historical reviewed evidence")
        canvas.drawRightString(PAGE_W-RIGHT,18,str(doc.page));canvas.restoreState()

    def afterFlowable(self,flowable):
        if isinstance(flowable,Paragraph) and flowable.style.name in {"h2","h3"}:
            key=f"section-{self.heading_id}";self.heading_id+=1
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.getPlainText(),key,0 if flowable.style.name=="h2" else 1,False)


def main():
    ast=json.loads(subprocess.check_output(["pandoc","--from=gfm-tex_math_dollars","--to=json",str(MD)],text=True))
    story=[];blocks=ast["blocks"];abstract=False;references=False;index=0
    while index<len(blocks):
        b=blocks[index];t=b["t"];c=b.get("c")
        if t=="Header":
            level=c[0];text=plain(c[2]);abstract=text=="Abstract";references=text=="References"
            if level==2 and text.startswith("Appendix A"):
                story.append(PageBreak())
            story.append(Paragraph(inline(c[2]),styles[f"h{level}"]))
        elif t in {"Para","Plain"}:
            if len(c)==1 and c[0]["t"]=="Image":
                path=HERE/c[0]["c"][2][0]
                with PILImage.open(path) as im:
                    w,h=im.size
                    # Decode once and remove an unnecessary alpha channel before
                    # ReportLab's lazy image reader. Keep source figure intact.
                    rgb=im.convert("RGB")
                    image_bytes=BytesIO()
                    rgb.save(image_bytes,format="PNG")
                    image_bytes.seek(0)
                width=WIDTH;image=Image(image_bytes,width=width,height=width*h/w,lazy=0)
                group=[Spacer(1,7),image,Spacer(1,5)]
                if index+1<len(blocks) and blocks[index+1]["t"]=="Para":
                    caption=blocks[index+1]["c"]
                    if plain(caption).startswith("Figure "):
                        group.append(Paragraph(inline(caption),styles["caption"]));index+=1
                story.append(KeepTogether(group))
            else:story.append(Paragraph(inline(c),styles["abstract"] if abstract else styles["body"]))
        elif t=="Table":story+=table(b)
        elif t=="BulletList":
            for entry in c:
                for bb in entry:
                    if bb["t"] in {"Plain","Para"}:story.append(Paragraph("- "+inline(bb["c"]),styles["reference"] if references else styles["body"]))
                    else:raise ValueError(f"Unsupported list block {bb['t']}")
        else:raise ValueError(f"Unsupported block {t}")
        index+=1
    doc=Paper();doc.build(story)
    print(OUT)


if __name__=="__main__":main()
