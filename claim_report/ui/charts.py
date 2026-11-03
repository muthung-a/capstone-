# -*- coding: utf-8 -*-
"""
차트 그리기 — 통계 정의(Stat.chart)의 kind 에 따라 알맞은 차트를 그립니다.
새 차트 종류를 만들려면: ① 아래에 render_xxx 함수를 추가하고(마지막 줄은 _show(fig, c)) ② 맨 아래 RENDERERS 에 이름을 등록하세요.
(그 뒤 stats_config.py 의 Chart(kind="xxx") 로 쓰면 됩니다)
"""
import math
import re

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import config
from core.format import esc, fmt_value
from core.table_stats import fmt_num
from ui.theme import FONT_STACK

T = config.THEME
EXTRA_COLOR = T["GRAY"]          # 심사결과 목록에 없는 값(도넛 차트)의 색


def export_enabled() -> bool:
    return bool(getattr(config, "CHART_IMAGE_EXPORT", True))


def export_hint() -> str:
    """차트 위에 보여줄 안내 문구 (저장 기능을 끄면 빈 문자열)"""
    return "차트 오른쪽 위의 카메라 아이콘을 누르면 그 차트를 이미지(PNG)로 저장합니다." if export_enabled() else ""


def plot_config(title: str) -> dict:
    """차트의 저장 버튼 설정. 켜져 있으면 오른쪽 위에 '이미지(PNG) 저장' 카메라 버튼만 보입니다.
    저장은 브라우저 안에서 이뤄져서 추가 라이브러리/인터넷이 필요 없고, 화면에 보이는 모양 그대로 저장됩니다."""
    if not export_enabled():
        return {"displayModeBar": False}
    name = re.sub(r'[\\/:*?"<>|]+', " ", str(title)).strip() or "chart"      # 파일 이름에 쓸 수 없는 글자 제거
    return {"displayModeBar": True, "displaylogo": False, "modeBarButtons": [["toImage"]],
            "toImageButtonOptions": {"format": "png", "filename": name, "scale": 2}}


def _show(fig, chart):
    """★ 모든 차트가 화면에 나가는 유일한 출구. 새 차트 종류도 반드시 이 함수로 내보내세요 (점검.bat 이 확인합니다)."""
    st.plotly_chart(fig, config=plot_config(chart.title))


def _style(fig, height, legend=False):
    fig.update_layout(
        height=height, margin=dict(l=6, r=6, t=10, b=6),
        paper_bgcolor="#FFFFFF", plot_bgcolor="rgba(0,0,0,0)",      # 저장되는 이미지 배경이 투명하지 않게 흰색
        font=dict(family=FONT_STACK, size=12, color=T["TEXT"]),
        hoverlabel=dict(bgcolor="#fff", bordercolor=T["LINE"], font_size=12),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font_size=12),
    )
    fig.update_xaxes(showline=False, zeroline=False, gridcolor=T["GRID"], tickfont=dict(color=T["MUTED"]))
    fig.update_yaxes(showline=False, zeroline=False, gridcolor=T["GRID"], tickfont=dict(color=T["MUTED"]))
    return fig


def render_combo(stat, table, ctx):
    """막대(value) + 선(line). ctx['alert_field'] 가 선 열이면 경고 기준선도 그립니다."""
    c, g = stat.chart, stat.group_by
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=table[g].astype(str).map(esc), y=table[c.value], name=c.value, marker_color="#C9D9F1",
        text=[f"{v:,.0f}" for v in table[c.value]], textposition="inside", insidetextanchor="start",
        textfont=dict(color=T["BLUE_DARK"], size=11),
        hovertemplate="%{x}<br>" + c.value + " %{y:,}<extra></extra>"), secondary_y=False)
    if c.line and c.line in table.columns:
        fig.add_trace(go.Scatter(
            x=table[g].astype(str).map(esc), y=table[c.line], name=c.line, mode="lines+markers+text",
            line=dict(color=T["BAD"], width=2.5),
            marker=dict(size=7, color="#fff", line=dict(color=T["BAD"], width=2)),
            text=[f"{v}%" for v in table[c.line]], textposition="top center",
            textfont=dict(color=T["BAD"], size=11),
            hovertemplate="%{x}<br>" + c.line + " %{y}<extra></extra>"), secondary_y=True)
        top_val = float(table[c.line].max())
        thr = ctx.get("alert_threshold") if ctx.get("alert_field") == c.line else None
        if thr is not None:
            fig.add_hline(y=thr, line_dash="dot", line_color=T["GRAY"], secondary_y=True)
            top_val = max(top_val, thr)
        top = max(math.ceil(top_val * 1.5), 2)
        fig.update_yaxes(secondary_y=True, range=[0, top], dtick=1 if top <= 10 else 2, tickformat=".0f",
                         showgrid=False, ticksuffix="%")
    fig.update_xaxes(type="category")
    fig.update_yaxes(secondary_y=False, rangemode="tozero")
    _style(fig, c.height, legend=True)
    _show(fig, c)


def render_donut(stat, table, ctx):
    c, g = stat.chart, stat.group_by
    total = float(table[c.value].sum()) or 1.0
    shares = table[c.value] / total * 100
    colors = [config.RESULT_COLORS.get(k, EXTRA_COLOR) for k in table[g]]
    fig = go.Figure(go.Pie(
        labels=[f"{esc(k)} {s:.1f}%" for k, s in zip(table[g], shares)], values=table[c.value], hole=0.64, sort=False,
        marker=dict(colors=colors, line=dict(color="#fff", width=2)), direction="clockwise", textinfo="none",
        hovertemplate="%{label}<br>%{value:,}건<extra></extra>"))
    if c.center_key and (table[g] == c.center_key).any():
        v = float(table.loc[table[g] == c.center_key, c.value].iloc[0]) / total * 100
        fig.add_annotation(
            text=f"<b>{v:.1f}%</b><br><span style='font-size:12px;color:{T['MUTED']}'>{c.center_caption}</span>",
            showarrow=False, font=dict(size=22, color=T["TEXT"]))
    _style(fig, c.height, legend=True)
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="center", x=0.5))
    _show(fig, c)


def render_hbar(stat, table, ctx):
    c, g = stat.chart, stat.group_by
    t = table.sort_values(c.value, ascending=False)
    if c.top_n:
        t = t.head(c.top_n)
    t = t.iloc[::-1]                      # 가로 막대는 아래에서 위로 그려지므로 뒤집기
    color = T.get(c.color, c.color) if c.color else T["BLUE"]
    fig = go.Figure(go.Bar(
        x=t[c.value], y=t[g].astype(str).map(esc), orientation="h", marker_color=color,
        text=[fmt_value(v, c.value_format) for v in t[c.value]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>"))
    fig.update_xaxes(showticklabels=False, showgrid=False, range=[0, float(t[c.value].max() or 1) * 1.25])
    fig.update_yaxes(showgrid=False, tickfont=dict(color=T["TEXT"], size=12))
    _style(fig, c.height)
    _show(fig, c)


def trend(title: str, periods: list, lines: dict, pct: bool = False, height: int = 260, emphasize: tuple = ()):
    """통계표 모드: 항목 하나의 기간별 추이. lines = {선 이름: [기간마다의 값 또는 NaN]}
    선이 하나면 마지막 값만 숫자로 표시하고(여러 개면 범례로 구분), 나머지는 마우스를 올리면 보입니다."""
    from types import SimpleNamespace
    palette = [T["BLUE"], T["BAD"], T["OK"], T["WARN"], T["GRAY"], "#7B5EA7", "#17A2B8", "#E67E22", "#6C757D", "#A0522D"]
    xs = [esc(p) for p in periods]
    many = len(lines) > 3
    dense = len(periods) > 30                                  # 기간이 길면 점 없이 선만
    fig = go.Figure()
    big, color_i = False, 0
    for k, (name, vals) in enumerate(lines.items()):
        em = name in emphasize                                  # 합계처럼 강조할 선은 진한 색 + 굵게
        y = [None if (v is None or v != v) else float(v) for v in vals]
        known = [i for i, t in enumerate(y) if t is not None]
        big = big or (bool(known) and max(abs(y[i]) for i in known) >= 1e5)
        text = [""] * len(y)
        if len(lines) == 1 and known:
            text[known[-1]] = fmt_num(y[known[-1]], pct)
        color = T["NAVY"] if em else palette[color_i % len(palette)]
        color_i += 0 if em else 1
        fig.add_trace(go.Scatter(
            x=xs, y=y, name=esc(name), mode=("lines" if (dense and len(lines) > 1) else "lines+markers") + "+text",
            text=text, textposition="top left", cliponaxis=False,
            line=dict(color=color, width=4 if em else (1.8 if many else 2.5)), marker=dict(size=5 if many else 6), textfont=dict(size=11),
            connectgaps=False, hovertemplate="%{x}<br>%{y:,.2f}" + ("%" if pct else "") + "<extra>" + esc(name) + "</extra>"))
    fig.update_xaxes(type="category")
    if len(periods) > 12:                                   # 기간이 많으면(예: 53개월) 글자가 겹치지 않게 일정 간격으로만 표시
        fig.update_xaxes(tickmode="linear", tick0=0, dtick=math.ceil(len(periods) / 8), tickangle=-45)
    _style(fig, height, legend=len(lines) > 1)
    fig.update_layout(margin=dict(l=6, r=22, t=10, b=6))
    if big:
        fig.update_yaxes(tickformat=",.0f")
    _show(fig, SimpleNamespace(title=title))


RENDERERS = {"combo": render_combo, "donut": render_donut, "hbar": render_hbar}


def render(stat, table, ctx):
    fn = RENDERERS.get(stat.chart.kind)
    if fn is None:
        st.caption(f"알 수 없는 차트 종류입니다: {stat.chart.kind}")
    elif table.empty:
        st.caption("표시할 데이터가 없습니다.")
    else:
        fn(stat, table, ctx)
