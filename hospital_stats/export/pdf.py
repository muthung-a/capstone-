import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
import pandas as pd
from config.settings import GROUP_MAP
from services import analytics as A

pdfmetrics.registerFont(UnicodeCIDFont("HYGothic-Medium"))
F = "HYGothic-Medium"
H1 = ParagraphStyle("h1", fontName=F, fontSize=16, leading=22)
H2 = ParagraphStyle("h2", fontName=F, fontSize=12, leading=18, spaceBefore=6)
B = ParagraphStyle("b", fontName=F, fontSize=9, leading=13)


def _n(x):
    return "-" if x is None or pd.isna(x) else (f"{x:,.2f}" if abs(x) < 10 else f"{x:,.0f}")


def _tbl(data, widths, small=False):
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), F, 7 if small else 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    return t


def build_pdf(ctx) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    el = [Paragraph(f"월간 통계 보고서 — 기준월 {ctx.base:%Y-%m}", H1), Spacer(1, 8), Paragraph("핵심 지표", H2)]
    rows = [["지표", "기준월", "전월", "증감률"]] + [
        [k["지표"], _n(k["기준월"]), _n(k["전월"]), "-" if k["증감률(%)"] is None else f"{k['증감률(%)']:+.1f}%"]
        for k in A.kpi_summary(ctx)]
    el += [_tbl(rows, [140, 120, 120, 80]), Spacer(1, 6), Paragraph("자동 요약", H2)]
    el += [Paragraph(l.replace("▲", "(+)").replace("▼", "(-)"), B) for l in A.summary_lines(ctx)]
    pp = ctx.period[-6:]
    for g in GROUP_MAP:
        t = A.group_table(ctx, g, pp)
        data = [list(t.columns)] + [[r["지표"][:14], r["세부"][:26]] + [_n(x) for x in r.iloc[2:]] for _, r in t.iterrows()]
        el += [PageBreak(), Paragraph(f"{g} (최근 {len(pp)}개월)", H2), _tbl(data, [90, 170] + [85] * len(pp), True)]
    doc.build(el)
    return buf.getvalue()
