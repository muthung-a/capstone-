# -*- coding: utf-8 -*-
"""
통계표 모드 대시보드 (항목 × 기간 표용).  위에서부터:
  조회 조건(기간·항목·세부구분) → 자동 요약 → 숫자 카드(전기 대비) → 항목별 추이 차트 → 상세 표 → 보고서 내보내기
항목 이름 같은 '파일에서 온 글자'는 화면 HTML 에 넣기 전에 항상 이스케이프합니다.
"""
import hashlib
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

import config
import hooks
from core import table_stats as ts
from core.format import arrow, esc
from core.table_mode import ITEM, PERIOD, SUB, VALUE
from reports import table_report
from ui import charts, components
from ui.components import card_header, guard, insight_list, kpi_html, show_table, wide_button
from ui.table_panel import TableLoaded


TOTAL_WORDS = ("합계", "전체", "계", "총계")
MAX_LINES = 10                                                    # 한 차트에 그리는 선(구분)의 최대 개수


@st.cache_data(show_spinner="Excel 보고서를 만드는 중입니다...")
def _excel(key, _long, _mat, _summ, insights, meta):
    return table_report.build_excel(_long, _mat, _summ, list(insights), meta)


@st.cache_data(show_spinner="PDF 보고서를 만드는 중입니다...")
def _pdf(key, _mat, _summ, insights, meta):
    return table_report.build_pdf(_mat, _summ, list(insights), meta)


def _select_filters(p, sig):
    """조회 조건 카드. 반환: (선택한 기간들, 선택한 시리즈 [(항목, 하위구분)])"""
    h = hashlib.md5(("|".join(p.items) + "#" + "|".join(p.periods)).encode("utf-8")).hexdigest()[:6]
    with st.container(key="card-filter"):
        card_header("조회 조건", "항목을 고르면 아래의 요약·차트·표·보고서가 모두 그 항목 기준으로 바뀝니다.")
        if len(p.periods) > 1:
            lo, hi = st.select_slider("기간", options=p.periods, value=(p.periods[0], p.periods[-1]), key=f"tp::{sig}::{h}")
            periods = p.periods[p.periods.index(lo): p.periods.index(hi) + 1]
        else:
            periods = list(p.periods)
        default = p.items if len(p.items) <= config.TABLE_DEFAULT_ITEMS + 2 else p.items[:config.TABLE_DEFAULT_ITEMS]
        items = st.multiselect(f"항목 (전체 {len(p.items):,}개)", p.items, default=default, key=f"ti::{sig}::{h}",
                               help="입력해서 검색할 수 있어요.")
        subs_all = list(dict.fromkeys(s for it, s in p.series if it in items and s))
        subs = subs_all
        if subs_all:
            if len(subs_all) <= 10:
                subs = st.pills("세부 구분", subs_all, selection_mode="multi", default=subs_all, key=f"ts::{sig}::{h}") or []
            else:
                subs = st.multiselect("세부 구분", subs_all, default=subs_all, key=f"ts::{sig}::{h}")
    series = [(it, sb) for it, sb in p.series if it in items and (sb == "" or not subs_all or sb in subs)]
    include_total = True
    if any(sb in TOTAL_WORDS for _, sb in series) and any(sb not in TOTAL_WORDS for _, sb in series):
        tot = p.long[p.long[SUB].isin(TOTAL_WORDS)][VALUE].abs().median()
        oth = p.long[~p.long[SUB].isin(TOTAL_WORDS)][VALUE].abs().median()
        auto = not (oth > 0 and tot / oth > 3)                     # 합계가 다른 선보다 3배 넘게 크면 기본은 끔
        with st.container(key="card-filter-total"):
            include_total = st.checkbox("합계 선도 차트에 그리기", value=auto, key=f"tt::{sig}::{h}",
                                        help="합계는 구분들을 더한 값이라 훨씬 클 수 있어요. 구분끼리 비교하려면 끄세요. (숫자 카드에는 합계가 그대로 나옵니다)")
    return periods, series, include_total


def _representatives(summ):
    """항목마다 대표 시리즈 하나: 세부 구분 중 '합계/전체/계'가 있으면 그것, 없으면 첫 번째"""
    picks = []
    for it, g in summ.groupby(ITEM, sort=False):
        total = g[g[SUB].isin(["합계", "전체", "계", "총계"])]
        picks.append((total if not total.empty else g).iloc[0])
    return pd.DataFrame(picks)


def _kpis(summ, pct_series):
    cards = _representatives(summ).head(4)
    if cards.empty:
        return
    st.markdown(f'<div class="kpi-caption">{esc("선택한 항목의 최근 값 · 직전 값 대비 증감")}</div>', unsafe_allow_html=True)
    cols = st.columns(len(cards))
    for col, (_, r) in zip(cols, cards.iterrows()):
        pct = (r[ITEM], r[SUB]) in pct_series
        d = r["증감"]
        if pd.isna(d):
            delta, tone, vs = None, "flat", ""
        elif d == 0:
            delta, tone, vs = "– 변동 없음", "flat", f"직전({esc(r['직전기간'])})"
        else:
            delta = f"{arrow(d)} {ts.fmt_num(abs(d), pct)}"
            tone = "neutral"
            vs = f"직전({esc(r['직전기간'])}) 대비 " + ("" if pd.isna(r["증감률(%)"]) else f"{r['증감률(%)']:+.1f}%")
        with col:
            st.markdown(kpi_html(esc(ts.label_of(r[ITEM], "" if r[SUB] in ("합계", "전체", "계", "총계") else r[SUB])), ts.fmt_num(r["최근값"]), "%" if pct else "", delta, tone, vs,
                                 f"{esc(r['최근기간'])} · 평균 <b>{ts.fmt_num(r['평균'], pct)}</b>"), unsafe_allow_html=True)
    st.markdown('<div class="kpi-gap"></div>', unsafe_allow_html=True)


def _charts(mat, series, periods, pct_series, include_total=True):
    hint = charts.export_hint()
    if hint:
        st.caption(hint)
    items = list(dict.fromkeys(it for it, _ in series))
    shown = items[:config.TABLE_MAX_CHARTS]
    if len(items) > len(shown):
        st.caption(f"차트는 앞의 {len(shown)}개 항목만 그립니다. (선택한 항목 {len(items)}개 · 아래 표에는 모두 나옵니다)")
    for start in range(0, len(shown), 3):
        row = shown[start:start + 3]
        cols = st.columns(3)
        for i, (col, it) in enumerate(zip(cols, row)):
            with col, st.container(key=f"card-tchart-{start + i}"):
                card_header(esc(it))
                with guard(it):
                    allks = [k for k in series if k[0] == it]
                    totals = [k for k in allks if k[1] in TOTAL_WORDS]
                    others = [k for k in allks if k not in totals]
                    pool = (totals if (include_total or not others) else []) + others
                    ks = pool[:MAX_LINES]
                    if len(pool) > MAX_LINES:                                         # 실제로 10개를 넘어서 잘릴 때만 안내
                        st.caption(f"선은 {MAX_LINES}개까지만 그립니다. (이 항목의 구분 {len(pool)}개 · 위 '세부 구분'에서 보고 싶은 것만 고르세요)")
                    lines = {(sb or it): mat.loc[(it, sb)].to_numpy(dtype=float) for it, sb in ks if (it, sb) in mat.index}
                    charts.trend(it, periods, lines, pct=all((it, sb) in pct_series for it, sb in ks),
                                 emphasize=tuple(sb for _, sb in ks if sb in TOTAL_WORDS))
                    mags = [float(np.nanmedian(np.abs(v[v != 0]))) for v in lines.values() if np.any(np.nan_to_num(v) != 0)]
                    if len(mags) >= 2 and max(mags) / max(min(mags), 1e-12) > 30:
                        st.caption("선마다 값 크기가 크게 달라 작은 값이 거의 안 보일 수 있어요. 항목과 구분이 반대로 읽힌 것일 수 있으니 "
                                   "왼쪽 '항목 열 순서 바꾸기'를 켜 보세요.")


def _tables(mat, summ, pct_series):
    with st.container(key="card-table"):
        card_header("상세 표", "항목별 최근 값과 직전 값 비교, 그리고 기간별 값입니다.")
        t1, t2 = st.tabs(["항목별 요약", "기간별 값"])
        with t1, guard("항목별 요약"):
            show = summ.copy()
            for c in ("최근값", "직전값", "증감", "평균", "최대", "최소"):
                show[c] = [ts.fmt_num(v, (it, sb) in pct_series) for v, it, sb in zip(show[c], show[ITEM], show[SUB])]
            show = show.drop(columns=["값개수"] + ([SUB] if (show[SUB] == "").all() else []))
            try:
                st.dataframe(show, hide_index=True, column_config={"증감률(%)": st.column_config.NumberColumn(format="%.1f")})
            except Exception:
                st.dataframe(show, hide_index=True)
        with t2, guard("기간별 값"):
            piv = mat.reset_index()
            for c in piv.columns[2:]:
                piv[c] = [ts.fmt_num(v, (it, sb) in pct_series) for v, it, sb in zip(piv[c], piv[ITEM], piv[SUB])]
            if (piv[SUB] == "").all():
                piv = piv.drop(columns=[SUB])
            st.dataframe(piv, hide_index=True)


def _export(long_sel, mat, summ, insights, meta):
    meta = dict(meta)
    key = hashlib.md5((str(int(pd.util.hash_pandas_object(long_sel, index=False).sum())) + "|".join(insights) + str(meta)).encode("utf-8")).hexdigest()
    stamp = datetime.now().strftime("%Y%m%d")
    with st.container(key="card-export"):
        e0, e1, e2 = st.columns([3, 1, 1], vertical_alignment="center")
        with e0:
            card_header("보고서 내보내기", "현재 선택한 항목·기간 기준으로 만들어집니다. Excel 은 모든 값까지, PDF 는 인쇄·공유용 요약본입니다.")
        with e1, guard("Excel 보고서"):
            wide_button(st.download_button, "Excel 내려받기", data=_excel(key, long_sel, mat, summ, tuple(insights), meta),
                        file_name=f"통계표_보고서_{stamp}.xlsx", type="primary", key="tdl_excel",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with e2, guard("PDF 보고서"):
            wide_button(st.download_button, "PDF 내려받기", data=_pdf(key, mat, summ, tuple(insights), meta),
                        file_name=f"통계표_보고서_{stamp}.pdf", mime="application/pdf", key="tdl_pdf")


def render(tl: TableLoaded):
    p = tl.parsed
    period_txt = f"{p.periods[0]} ~ {p.periods[-1]}" if p.periods else ""
    components.top_bar(components.chip(tl.name) + components.chip(f"항목 {len(p.items):,}개")
                       + (components.chip(period_txt) if period_txt else ""))
    for w in p.warnings:
        components.warn_line(w)
    if p.long.empty:
        st.error("읽은 값이 없습니다. 왼쪽 '표 읽기 설정'에서 항목 열 / 값 열 / 기간 이름 줄을 확인해 주세요. "
                 "(표가 가로세로 반대라면 '가로↔세로 바꿔서 읽기'를 켜 보세요)")
        return

    periods, series, include_total = _select_filters(p, tl.sig)
    if not series or not periods:
        st.info("조회 조건에서 항목을 하나 이상 선택해 주세요.")
        return
    sel = set(series)
    long_sel = p.long[p.long[PERIOD].isin(periods)]
    long_sel = long_sel[[(a, b) in sel for a, b in zip(long_sel[ITEM], long_sel[SUB])]]
    mat = ts.matrix(long_sel, series, periods)
    summ = ts.summary(mat)
    insights = ts.sentences(summ, periods)

    with st.container(key="card-insight"):
        card_header("자동 요약", "선택한 항목과 기간에 맞춰 자동으로 만든 문장입니다.")
        with guard("자동 요약"):
            insight_list(insights)
    with guard("숫자 카드"):
        _kpis(summ, p.pct_series)
    with guard("추이 차트"):
        _charts(mat, series, periods, p.pct_series, include_total)
    _tables(mat, summ, p.pct_series)
    _export(long_sel, mat, summ, insights, {"period": f"{periods[0]} ~ {periods[-1]}", "n_items": len(set(i for i, _ in series))})
    if hooks.foot_note():
        st.markdown(f'<div class="foot-note">{esc(hooks.foot_note())}</div>', unsafe_allow_html=True)
