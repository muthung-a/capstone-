# -*- coding: utf-8 -*-
"""
대시보드 화면 조립.  위에서부터: 자동 요약 → (경고) → KPI 카드 → 차트 → 상세 통계표 → 보고서 내보내기
무엇을 보여줄지는 config.py(KPIS, DASHBOARD_LAYOUT)와 stats_config.py 가 정하므로 보통 이 파일은 고치지 않습니다.
"""
import hashlib
from datetime import datetime

import pandas as pd
import streamlit as st

import config
import stats_config
from core.format import arrow, esc, fmt_value, fmt_won, fmt_won_text
from reports import excel as excel_report
from reports import pdf as pdf_report
from ui import charts
from ui.components import card_header, guard, insight_list, kpi_html, show_table, wide_button


@st.cache_data(show_spinner="Excel 보고서를 만드는 중입니다...")
def _excel_bytes(key, _df, _stats_tables, insights, period):
    return excel_report.build(_df, _stats_tables, list(insights), period)


@st.cache_data(show_spinner="PDF 보고서를 만드는 중입니다...")
def _pdf_bytes(key, _df, _stats_tables, insights, period):
    return pdf_report.build(_df, _stats_tables, list(insights), period)


def _report_key(ctx):
    """같은 조건이면 같은 값 → 보고서를 다시 만들지 않고 저장해 둔 것을 재사용"""
    h = int(pd.util.hash_pandas_object(ctx["df"], index=False).sum())
    raw = f"{len(ctx['df'])}|{h}|{list(ctx['df'].columns)}|{'|'.join(ctx['insights'])}|{ctx['period']}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _download(kind, label, builder, key, ctx, stamp, ext, mime, primary):
    """행이 많으면(config.REPORT_AUTO_MAX_ROWS 초과) 버튼을 눌렀을 때만 보고서를 만듭니다."""
    flag = f"rep_ok::{kind}::{key}"
    big = len(ctx["df"]) > config.REPORT_AUTO_MAX_ROWS
    if big and not st.session_state.get(flag):
        if wide_button(st.button, f"{label} 만들기", key=f"mk_{kind}",
                       help=f"조회된 행이 {len(ctx['df']):,}개로 많아 만드는 데 시간이 걸립니다. 한 번 만들면 같은 조건에서는 바로 받을 수 있어요."):
            st.session_state[flag] = True
            st.rerun()
        return
    data = builder(key, ctx["df"], ctx["stats_tables"], tuple(ctx["insights"]), ctx["period"])
    wide_button(st.download_button, f"{label} 내려받기", data=data, file_name=f"심사청구_통계보고서_{stamp}.{ext}",
                mime=mime, type="primary" if primary else "secondary", key=f"dl_{kind}")


def _delta(kind, cur, prev, bad_if_up):
    if prev is None:
        return None, "flat"
    d = cur - prev
    if d == 0:
        return "– 변동 없음", "flat"
    tone = ("bad" if d > 0 else "good") if bad_if_up else "neutral"
    if kind == "count":
        txt = f"{abs(d):,.0f}건"
    elif kind == "won":
        txt = fmt_won_text(abs(d))
    else:
        txt = f"{abs(d):.2f}%p"
    return f"{arrow(d)} {txt}", tone


def _kpis(ctx):
    """맨 위 숫자 카드. 반환: 경고 기준을 판단할 때 쓴 필드 이름(없으면 None)"""
    stat = stats_config.STATS_BY_ID.get(config.KPI_STAT)
    table = ctx["tables"].get(config.KPI_STAT)
    if stat is None or table is None or table.empty:
        return None
    t = table.sort_values(stat.group_by).reset_index(drop=True)
    last = t.iloc[-1]
    prev = t.iloc[-2] if len(t) >= 2 else None
    total = ctx["totals"].get(config.KPI_STAT)
    cards = [k for k in config.KPIS if k["field"] in t.columns]
    if not cards:
        return None

    alert_field, over_any, alert_msg = None, False, ""
    for k in cards:
        if k.get("alert") and float(last[k["field"]]) > ctx["threshold"]:
            alert_field, over_any = k["field"], True
            alert_msg = (f'<b>기준 초과</b>&nbsp; {esc(last[stat.group_by])} {esc(k["label"])} {last[k["field"]]}%가 '
                         f'경고 기준 {ctx["threshold"]}%를 넘었습니다. 아래 통계를 확인해 보세요.')
    if over_any:
        st.markdown(f'<div class="alert">{alert_msg}</div>', unsafe_allow_html=True)

    cap = f"{last[stat.group_by]} 실적" + (f" · 전월({prev[stat.group_by]}) 대비 증감" if prev is not None else "")
    st.markdown(f'<div class="kpi-caption">{esc(cap)}</div>', unsafe_allow_html=True)
    cols = st.columns(len(cards))
    for col, k in zip(cols, cards):
        f, kind = k["field"], k["kind"]
        cur = float(last[f])
        pv = None if prev is None else float(prev[f])
        delta_text, tone = _delta(kind, cur, pv, k.get("bad_if_up", False))
        if kind == "won":
            value, unit = fmt_won(cur)
        elif kind == "count":
            value, unit = f"{cur:,.0f}", "건"
        else:
            value, unit = f"{cur:g}", "%"
        tot = None if total is None or f not in total.index else float(total[f])
        if kind == "percent":
            foot = (f'경고 기준 <b>{ctx["threshold"]}%</b> · ' if k.get("alert") else "") + \
                   (f'기간 전체 <b>{tot:.2f}%</b>' if tot is not None else "")
        else:
            foot = f'기간 합계 <b>{fmt_value(tot, kind)}</b>' if tot is not None else ""
        with col:
            st.markdown(kpi_html(k["label"], value, unit, delta_text, tone, "전월 대비" if prev is not None else "",
                                 foot, over=bool(k.get("alert")) and over_any), unsafe_allow_html=True)
    st.markdown('<div class="kpi-gap"></div>', unsafe_allow_html=True)
    return alert_field or next((k["field"] for k in cards if k.get("alert")), None)


def render(ctx):
    """ctx: df, stats, tables, totals, insights, threshold, period"""
    # 1) 자동 요약 (가장 위)
    with st.container(key="card-insight"):
        card_header("자동 요약", "조회 조건에 맞춰 통계에서 자동으로 만든 문장입니다.")
        with guard("자동 요약"):
            insight_list(ctx["insights"])

    # 2) KPI 카드
    alert_field = None
    with guard("숫자 카드"):
        alert_field = _kpis(ctx)
    chart_ctx = {"alert_threshold": ctx["threshold"], "alert_field": alert_field}

    # 3) 차트 (config.DASHBOARD_LAYOUT 순서대로)
    by_id = {s.id: s for s in ctx["stats"]}
    if charts.export_hint() and any(s.chart is not None for s in ctx["stats"]):
        st.caption(charts.export_hint())
    for row in config.DASHBOARD_LAYOUT:
        items = [(by_id[i], w) for i, w in row if i in by_id and by_id[i].chart is not None]
        if not items:
            continue
        cols = st.columns([w for _, w in items])
        for col, (stat, _) in zip(cols, items):
            with col:
                with st.container(key=f"card-chart-{stat.id}"):
                    card_header(stat.chart.title, stat.chart.subtitle)
                    with guard(stat.chart.title):
                        charts.render(stat, ctx["tables"][stat.id], chart_ctx)

    # 4) 상세 통계표
    table_stats = [s for s in ctx["stats"] if s.in_table]
    with st.container(key="card-table"):
        card_header("상세 통계표", "숫자 열 제목을 누르면 정렬할 수 있습니다.")
        tabs = st.tabs([s.title for s in table_stats] + ["원본 데이터"])
        for tab, s in zip(tabs, table_stats):
            with tab, guard(s.title):
                show_table(ctx["tables"][s.id])
        with tabs[-1], guard("원본 데이터"):
            n_all = len(ctx["df"])
            if n_all > config.RAW_PREVIEW_ROWS:
                st.caption(f"화면에는 앞의 {config.RAW_PREVIEW_ROWS:,}행만 보여줍니다. (전체 {n_all:,}행은 Excel 보고서에 들어 있어요)")
            show_table(ctx["df"].head(config.RAW_PREVIEW_ROWS), height=360)

    # 5) 보고서 내보내기
    ctx["stats_tables"] = [(s, ctx["tables"][s.id]) for s in ctx["stats"]]
    key = _report_key(ctx)
    with st.container(key="card-export"):
        e0, e1, e2 = st.columns([3, 1, 1], vertical_alignment="center")
        with e0:
            card_header("보고서 내보내기",
                        "현재 조회 조건 기준으로 만들어집니다. Excel은 상세 데이터까지, PDF는 인쇄·공유용 요약본입니다.")
        stamp = datetime.now().strftime("%Y%m%d")
        with e1, guard("Excel 보고서"):
            _download("excel", "Excel", _excel_bytes, key, ctx, stamp, "xlsx",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", True)
        with e2, guard("PDF 보고서"):
            _download("pdf", "PDF", _pdf_bytes, key, ctx, stamp, "pdf", "application/pdf", False)
