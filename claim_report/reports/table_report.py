# -*- coding: utf-8 -*-
"""통계표 모드의 Excel / PDF 보고서. 양식을 병원 양식에 맞추려면 이 파일을 고치세요."""
import io
from datetime import datetime

import pandas as pd

import config
from core.table_mode import ITEM, SUB
from core.table_stats import fmt_num
from reports import excel, pdf


def build_excel(long: pd.DataFrame, mat: pd.DataFrame, summ: pd.DataFrame, insights: list, meta: dict) -> bytes:
    buf = io.BytesIO()
    used = set()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame({"항목": ["보고서명", "생성일시", "대상 기간", "항목 수"],
                      "값": [config.REPORT_TITLE, datetime.now().strftime("%Y-%m-%d %H:%M"), meta.get("period", ""),
                             f"{meta.get('n_items', 0):,}"]}).to_excel(w, sheet_name=excel.sheet_name("표지", used), index=False)
        pd.DataFrame({"자동 요약 코멘트": insights}).to_excel(w, sheet_name=excel.sheet_name("요약코멘트", used), index=False)
        summ.to_excel(w, sheet_name=excel.sheet_name("요약", used), index=False)
        mat.reset_index().to_excel(w, sheet_name=excel.sheet_name("기간별", used), index=False)
        long.to_excel(w, sheet_name=excel.sheet_name("원본(긴형태)", used), index=False)
        excel.finish(w.book)
    return buf.getvalue()


def build_pdf(mat: pd.DataFrame, summ: pd.DataFrame, insights: list, meta: dict) -> bytes:
    show = summ.copy()
    for c in ("최근값", "직전값", "증감", "평균", "최대", "최소"):
        show[c] = show[c].map(fmt_num)
    show["증감률(%)"] = show["증감률(%)"].map(lambda v: "-" if pd.isna(v) else f"{v:+.1f}")
    show = show.drop(columns=["값개수"] + ([SUB] if (show[SUB] == "").all() else []))
    tables = [("항목별 요약 (최근 값과 직전 값 비교)", show)]
    if mat.shape[1] <= 8:                                         # 기간이 너무 많으면 PDF 폭을 넘으므로 Excel 로만 제공
        piv = mat.reset_index()
        for c in piv.columns[2:]:
            piv[c] = piv[c].map(fmt_num)
        if (piv[SUB] == "").all():
            piv = piv.drop(columns=[SUB])
        tables.append(("기간별 값", piv))
    meta_line = f"생성일시: {datetime.now():%Y-%m-%d %H:%M} · 대상 기간: {meta.get('period', '')} · 항목 {meta.get('n_items', 0):,}개"
    return pdf.build_tables(meta_line, insights, tables)
