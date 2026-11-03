# -*- coding: utf-8 -*-
"""PDF 요약 보고서 만들기 (한글 폰트는 fonts 폴더의 나눔고딕 사용).
PDF 양식(제목, 표 구성, 색)을 바꾸려면 이 파일을 고치세요."""
import io
import os
from datetime import datetime

import pandas as pd
from xml.sax.saxutils import escape as xml_escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import config
from core.format import strip_lead

_REG = os.path.join(config.FONT_DIR, "NanumGothic.ttf")
_BOLD = os.path.join(config.FONT_DIR, "NanumGothicBold.ttf")


def _fonts():
    if "NanumGothic" in pdfmetrics.getRegisteredFontNames():
        return "NanumGothic", "NanumGothic-Bold"
    if os.path.exists(_REG) and os.path.exists(_BOLD):
        pdfmetrics.registerFont(TTFont("NanumGothic", _REG))
        pdfmetrics.registerFont(TTFont("NanumGothic-Bold", _BOLD))
        return "NanumGothic", "NanumGothic-Bold"
    return "Helvetica", "Helvetica-Bold"   # 폰트 파일이 없으면 한글이 깨집니다


def _cell(v):
    if isinstance(v, bool) or v is None:
        return str(v)
    if isinstance(v, int) or (isinstance(v, float) and float(v).is_integer()):
        return f"{int(v):,}"
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)


def _flow_table(table, font, bold, navy):
    """PDF 에 넣을 표 (제목 줄은 남색, 줄무늬)"""
    data = [list(table.columns)] + [[_cell(v) for v in row] for row in table.itertuples(index=False)]
    t = Table(data, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font), ("FONTNAME", (0, 0), (-1, 0), bold),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), navy), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
    ]))
    return t


def build_tables(meta_line: str, insights: list, tables: list) -> bytes:
    """범용 PDF 보고서: 제목 + 한 줄 정보 + 요약 문장 + 여러 표. tables = [(제목, DataFrame)]"""
    font, bold = _fonts()
    navy = colors.HexColor(config.THEME["NAVY"])
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm, title=config.REPORT_TITLE)
    ss = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=ss["Title"], fontName=bold, fontSize=18)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName=bold, fontSize=13, spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle("b", parent=ss["Normal"], fontName=font, fontSize=10, leading=15)
    els = [Paragraph(xml_escape(config.REPORT_TITLE), title), Paragraph(xml_escape(meta_line), body),
           Spacer(1, 8), Paragraph("1. 요약", h2)]
    for line in insights:
        els.append(Paragraph("• " + xml_escape(strip_lead(line)), body))
    for n, (name, table) in enumerate(tables, 2):
        if table is None or table.empty:
            continue
        els += [Spacer(1, 6), Paragraph(xml_escape(f"{n}. {name}"), h2), _flow_table(table, font, bold, navy)]
    doc.build(els)
    return buf.getvalue()


def build(raw: pd.DataFrame, stats_tables: list, insights: list, period: str) -> bytes:
    font, bold = _fonts()
    navy = colors.HexColor(config.THEME["NAVY"])
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm, title=config.REPORT_TITLE)
    ss = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=ss["Title"], fontName=bold, fontSize=18)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName=bold, fontSize=13, spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle("b", parent=ss["Normal"], fontName=font, fontSize=10, leading=15)

    els = [Paragraph(xml_escape(config.REPORT_TITLE), title),
           Paragraph(xml_escape(f"생성일시: {datetime.now():%Y-%m-%d %H:%M} · 대상 기간: {period} · 총 청구건수: {len(raw):,}건"), body),
           Spacer(1, 8), Paragraph("1. 요약", h2)]
    for line in insights:
        els.append(Paragraph("• " + xml_escape(strip_lead(line)), body))

    n = 2
    for stat, table in stats_tables:
        if not stat.in_table or table.empty:
            continue
        els += [Spacer(1, 6), Paragraph(xml_escape(f"{n}. {stat.title} 통계"), h2)]
        t = _flow_table(table, font, bold, navy)
        els.append(t)
        n += 1
    doc.build(els)
    return buf.getvalue()
