"""재사용 UI 컴포넌트"""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from config.settings import PRIMARY
from core.utils import fmt_value


def page_header(title, subtitle="", badge=""):
    st.markdown(f"""<div class="page-head"><div><h1>{title}</h1><p>{subtitle}</p></div>
    {f'<span class="badge">{badge}</span>' if badge else ''}</div>""", unsafe_allow_html=True)


def kpi_card(k: dict):
    d, unit = k["증감률(%)"], k["단위"]
    if unit == "%" and k["전월"] is not None and k["기준월"] is not None:
        diff = (k["기준월"] - k["전월"]) * 100
        cls, txt = ("up" if diff > 0 else "down" if diff < 0 else "flat"), f"{diff:+.1f}%p"
    elif d is None:
        cls, txt = "flat", "-"
    else:
        cls, txt = ("up" if d > 0 else "down" if d < 0 else "flat"), f"{'▲' if d > 0 else '▼' if d < 0 else ''} {abs(d):.1f}%"
    st.markdown(f"""<div class="kpi"><div class="top"><span class="label">{k['지표']}</span>
      <span class="icon">{k['아이콘']}</span></div>
      <div class="value">{fmt_value(k['기준월'], unit)}</div>
      <span class="delta {cls}">{txt}</span><span class="sub">전월 대비</span></div>""",
                unsafe_allow_html=True)
    if k["추이"]:
        fig = go.Figure(go.Scatter(y=k["추이"], mode="lines", line=dict(color=PRIMARY, width=2),
                                   fill="tozeroy", fillcolor="rgba(79,70,229,.08)", hoverinfo="skip"))
        fig.update_layout(height=46, xaxis_visible=False, yaxis_visible=False,
                          margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
        st.plotly_chart(fig, config={"displayModeBar": False}, key=f"spark_{k['지표']}")


def kpi_row(kpis: list[dict]):
    for col, k in zip(st.columns(len(kpis)), kpis):
        with col:
            kpi_card(k)


def card(title, subtitle=""):
    """with card('제목'): ... 형태로 사용"""
    c = st.container(border=True)
    c.markdown(f'<div class="card-title">{title}</div>' +
               (f'<div class="card-sub">{subtitle}</div>' if subtitle else ""), unsafe_allow_html=True)
    return c


def insight_list(lines: list[str]):
    if not lines:
        st.caption("비교할 전월 데이터가 없습니다.")
    for l in lines:
        st.markdown(f'<div class="insight">{l}</div>', unsafe_allow_html=True)


def trend_chart(long_df, kind="선", height=360, key=None):
    f = (px.line(long_df, x="월", y="값", color="라벨", markers=True) if kind == "선"
         else px.bar(long_df, x="월", y="값", color="라벨", barmode="group"))
    f.update_layout(height=height, legend_title_text="")
    st.plotly_chart(f, key=key)


def data_table(df, fmt="{:,.0f}", height=None):
    st.dataframe(df.style.format(fmt, na_rep="-"), height=height or "auto")
