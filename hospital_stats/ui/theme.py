"""전역 CSS — SaaS 관리자 대시보드 스타일 (카드형, 다크 사이드바)"""
import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio
from config.settings import COLORS

CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html, body, [class*="css"], .stMarkdown, button, input { font-family: 'Pretendard', 'Malgun Gothic', sans-serif !important; }
.block-container { padding-top: 1.6rem; max-width: 1400px; }
#MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }

/* 사이드바 */
section[data-testid="stSidebar"] { background: #0F172A; }
section[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #FFFFFF !important; }
section[data-testid="stSidebar"] [role="radiogroup"] label {
  padding: .55rem .8rem; border-radius: 8px; margin-bottom: 2px; width: 100%; }
section[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #1E293B; }
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background: #4F46E5; }
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) * { color: #fff !important; }
section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display: none; }
section[data-testid="stSidebar"] .stDownloadButton button {
  width: 100%; background: #1E293B; border: 1px solid #334155; }
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] { background: #1E293B; }

/* 헤더 */
.page-head { display:flex; justify-content:space-between; align-items:flex-end; margin-bottom: 1.2rem; }
.page-head h1 { font-size: 1.6rem; font-weight: 700; margin: 0; color:#0F172A; }
.page-head p { margin: .2rem 0 0; color:#64748B; font-size:.9rem; }
.badge { background:#EEF2FF; color:#4F46E5; padding:.3rem .7rem; border-radius:999px; font-size:.8rem; font-weight:600; }

/* KPI 카드 */
.kpi { background:#fff; border:1px solid #E2E8F0; border-radius:14px; padding:1rem 1.1rem;
       box-shadow: 0 1px 2px rgba(15,23,42,.04); height: 100%; }
.kpi .top { display:flex; justify-content:space-between; align-items:center; }
.kpi .label { color:#64748B; font-size:.82rem; font-weight:500; }
.kpi .icon { width:32px; height:32px; border-radius:8px; background:#EEF2FF;
             display:flex; align-items:center; justify-content:center; font-size:1rem; }
.kpi .value { font-size:1.55rem; font-weight:700; color:#0F172A; margin:.35rem 0 .15rem; }
.kpi .delta { font-size:.78rem; font-weight:600; padding:.1rem .45rem; border-radius:6px; }
.kpi .up { color:#047857; background:#D1FAE5; } .kpi .down { color:#B91C1C; background:#FEE2E2; }
.kpi .flat { color:#475569; background:#F1F5F9; }
.kpi .sub { color:#94A3B8; font-size:.75rem; margin-left:.3rem; }

/* 일반 카드 (st.container(border=True)) */
div[data-testid="stVerticalBlockBorderWrapper"] { background:#fff; border-radius:14px !important;
  border:1px solid #E2E8F0 !important; box-shadow: 0 1px 2px rgba(15,23,42,.04); }
.card-title { font-weight:700; font-size:1rem; color:#0F172A; margin-bottom:.2rem; }
.card-sub { color:#94A3B8; font-size:.8rem; margin-bottom:.6rem; }
.insight { padding:.5rem .2rem; border-bottom:1px dashed #E2E8F0; font-size:.9rem; color:#334155; }
.insight:last-child { border-bottom:none; }

/* 탭 */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #E2E8F0; }
.stTabs [data-baseweb="tab"] { padding: .5rem 1rem; border-radius: 8px 8px 0 0; }
.stTabs [aria-selected="true"] { color:#4F46E5 !important; }
</style>
"""


def apply():
    st.markdown(CSS, unsafe_allow_html=True)
    t = go.layout.Template(pio.templates["plotly_white"])
    t.layout.colorway = COLORS
    t.layout.font = dict(family="Pretendard, Malgun Gothic, sans-serif", color="#334155", size=12)
    t.layout.margin = dict(l=10, r=10, t=10, b=10)
    t.layout.legend = dict(orientation="h", y=-0.2, x=0)
    t.layout.xaxis = dict(showgrid=False, linecolor="#E2E8F0")
    t.layout.yaxis = dict(gridcolor="#F1F5F9", zeroline=False)
    t.layout.hoverlabel = dict(bgcolor="#0F172A", font_color="#fff")
    pio.templates["hospital"] = t
    pio.templates.default = "hospital"
