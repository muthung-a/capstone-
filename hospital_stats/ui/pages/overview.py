"""개요 페이지: KPI + 자동 요약 + 핵심 차트"""
import pandas as pd
import plotly.express as px
import streamlit as st
from services import analytics as A
from ui import components as C


def render(ctx):
    C.kpi_row(A.kpi_summary(ctx))
    st.write("")
    left, right = st.columns([3, 2])
    with left:
        with C.card("보험종류별 청구금액 추이", f"최근 {len(ctx.period)}개월 · 단위 원"):
            labels = [f"총진료비 | 청구금액(입원+외래) > {x}" for x in ("공단", "보호", "자보")]
            long = pd.DataFrame([{"월": m.strftime("%Y-%m"), "보험": l.split("> ")[-1], "값": A.series(ctx.df, l, [m]).iloc[0]}
                                 for l in labels for m in ctx.period])
            f = px.bar(long, x="월", y="값", color="보험")
            f.update_layout(height=330, legend_title_text="")
            st.plotly_chart(f, key="ov_claim")
    with right:
        with C.card("자동 요약", "전월 대비 주요 변동"):
            C.insight_list(A.summary_lines(ctx))
    l2, r2 = st.columns(2)
    with l2:
        with C.card("병상가동률 · 재원환자", "최근 12개월"):
            s = A.series(ctx.df, "병상가동율 | %", ctx.last12) * 100
            f = px.area(x=[m.strftime("%Y-%m") for m in ctx.last12], y=s.values, labels={"x": "", "y": "%"})
            f.update_layout(height=260)
            st.plotly_chart(f, key="ov_bed")
    with r2:
        with C.card("환자군 구성", ctx.base.strftime("%Y-%m")):
            g = ctx.df[(ctx.df["지표"] == "환자군수") & (ctx.df["세부"] != "합계")]
            f = px.pie(g, names="세부", values=ctx.base, hole=.6)
            f.update_layout(height=260, legend=dict(orientation="v", x=1, y=.5))
            st.plotly_chart(f, key="ov_pie")
