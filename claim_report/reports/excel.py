# -*- coding: utf-8 -*-
"""Excel 보고서 만들기 — 표지 / 요약코멘트 / 통계별 시트 / 원본데이터.
보고서 양식(시트 구성, 순서, 서식)을 병원 양식에 맞추려면 이 파일을 고치세요."""
import io
import re
from datetime import datetime

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill

import config


def sheet_name(title: str, used: set) -> str:
    """엑셀 시트 이름 규칙(31자 제한, 금지 글자 제거, 중복 방지)에 맞게 정리"""
    name = re.sub(r"[\[\]:*?/\\]", "", title)[:28] or "시트"
    base, i = name, 2
    while name in used:
        name, i = f"{base}{i}", i + 1
    used.add(name)
    return name


def _guard_formulas(ws):
    """데이터 값이 '=' 로 시작하면 openpyxl 이 수식으로 저장합니다(수식 주입). 모두 '글자'로 되돌립니다."""
    for row in ws.iter_rows():
        for c in row:
            if c.data_type == "f":
                c.data_type = "s"
                c.quotePrefix = True


def _style(ws):
    head_fill = PatternFill("solid", fgColor=config.THEME["NAVY"].lstrip("#"))
    for cell in ws[1]:
        cell.font = Font(name="맑은 고딕", bold=True, color="FFFFFF")
        cell.fill = head_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for col in ws.columns:
        width = max((len(str(c.value)) if c.value is not None else 0) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max(width * 1.6 + 2, 10), 48)
        for c in col[1:]:
            if isinstance(c.value, int):
                c.number_format = "#,##0"
            elif isinstance(c.value, float):
                c.number_format = "#,##0.00"
    ws.freeze_panes = "A2"


def finish(book):
    """모든 시트에 수식 주입 방어와 서식을 적용 (엑셀 보고서를 만드는 곳에서는 반드시 마지막에 호출)"""
    for ws in book.worksheets:
        _guard_formulas(ws)
        _style(ws)


_sheet_name = sheet_name


def build(raw: pd.DataFrame, stats_tables: list, insights: list, period: str) -> bytes:
    """stats_tables: [(Stat, DataFrame), ...]"""
    buf = io.BytesIO()
    used = set()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        cover = pd.DataFrame({
            "항목": ["보고서명", "생성일시", "대상 기간", "총 청구건수"],
            "값": [config.REPORT_TITLE, datetime.now().strftime("%Y-%m-%d %H:%M"), period, f"{len(raw):,}"],
        })
        cover.to_excel(w, sheet_name=_sheet_name("표지", used), index=False)
        pd.DataFrame({"자동 요약 코멘트": insights}).to_excel(w, sheet_name=_sheet_name("요약코멘트", used), index=False)
        for stat, table in stats_tables:
            if stat.in_table:
                table.to_excel(w, sheet_name=_sheet_name(stat.title, used), index=False)
        raw.to_excel(w, sheet_name=_sheet_name("원본데이터", used), index=False)
        finish(w.book)
    return buf.getvalue()
