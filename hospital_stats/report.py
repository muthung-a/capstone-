"""엑셀 / PDF 보고서 생성"""
import io
import re
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak

import parser as P

pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
KFONT = "HYSMyeongJo-Medium"


def _table(df, period, group):
    sub = df[df["그룹"] == group]
    t = sub[["지표", "세부"] + period].copy()
    t.columns = ["지표", "세부"] + [m.strftime("%Y-%m") for m in period]
    return t


def build_excel(df, period, summary, lines, base):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        s = pd.DataFrame(summary)
        s.to_excel(w, sheet_name="요약", index=False, startrow=2)
        ws = w.sheets["요약"]
        ws["A1"] = f"월간 통계 보고서 - 기준월 {base}"
        ws["A1"].font = Font(size=14, bold=True)
        r = len(s) + 5
        ws.cell(r, 1, "전월 대비 주요 변동").font = Font(bold=True)
        for i, l in enumerate(lines, 1):
            ws.cell(r + i, 1, re.sub(r"[*`]", "", l))
        ws.column_dimensions["A"].width = 18
        for c in "BCD":
            ws.column_dimensions[c].width = 18
        for g in P.GROUP_MAP:
            t = _table(df, period, g)
            t.to_excel(w, sheet_name=g.replace("·", "_"), index=False)
            sh = w.sheets[g.replace("·", "_")]
            for cell in sh[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="2F5597")
                cell.alignment = Alignment(horizontal="center")
            sh.column_dimensions["A"].width = 22
            sh.column_dimensions["B"].width = 34
            for j in range(3, 3 + len(period)):
                sh.column_dimensions[get_column_letter(j)].width = 15
                for row in sh.iter_rows(min_row=2, min_col=j, max_col=j):
                    row[0].number_format = "#,##0.00" if g == "환자현황" else "#,##0"
    return buf.getvalue()


def _num(x):
    if pd.isna(x):
        return "-"
    return f"{x:,.2f}" if abs(x) < 10 else f"{x:,.0f}"


def build_pdf(df, period, summary, lines, base):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    h = ParagraphStyle("h", fontName=KFONT, fontSize=16, leading=22)
    h2 = ParagraphStyle("h2", fontName=KFONT, fontSize=12, leading=18, spaceBefore=6)
    b = ParagraphStyle("b", fontName=KFONT, fontSize=9, leading=13)
    el = [Paragraph(f"월간 통계 보고서 — 기준월 {base}", h), Spacer(1, 8), Paragraph("자동 요약", h2)]
    rows = [["지표", "기준월", "전월", "증감률"]]
    for s in summary:
        rows.append([s["지표"], _num(s["기준월"]), _num(s["전월"]),
                     "-" if s["증감률(%)"] is None else f"{s['증감률(%)']:+.1f}%"])
    el.append(_style(Table(rows, colWidths=[140, 120, 120, 80])))
    el.append(Spacer(1, 6))
    for l in lines:
        el.append(Paragraph(re.sub(r"[*`]", "", l).replace("▲", "(+)").replace("▼", "(-)"), b))
    pp = period[-6:]  # PDF는 최근 6개월만
    for g in P.GROUP_MAP:
        el += [PageBreak(), Paragraph(f"{g} (최근 {len(pp)}개월)", h2)]
        t = _table(df, pp, g)
        data = [["지표", "세부"] + list(t.columns[2:])]
        for _, r in t.iterrows():
            data.append([r["지표"][:14], r["세부"][:26]] + [_num(x) for x in r.iloc[2:]])
        el.append(_style(Table(data, colWidths=[90, 170] + [85] * len(pp), repeatRows=1), small=True))
    doc.build(el)
    return buf.getvalue()


def _style(t, small=False):
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), KFONT, 7 if small else 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2F5597")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
    ]))
    return t
