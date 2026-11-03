"""사이드바: 업로드 / 메뉴 / 조회조건 / 내보내기"""
import streamlit as st
from config.settings import APP_TITLE, GROUP_MAP

MENU = ["📊 개요"] + [f"📁 {g}" for g in GROUP_MAP] + ["💊 약품 처방", "👩‍⚕️ 간호인력", "⚙️ 사용자 지표"]


def upload():
    st.sidebar.markdown(f"### 🏥 {APP_TITLE}")
    return st.sidebar.file_uploader("엑셀 업로드", type=["xlsx"], label_visibility="collapsed")


def menu():
    st.sidebar.markdown("**메뉴**")
    return st.sidebar.radio("메뉴", MENU, label_visibility="collapsed")


def filters(months):
    st.sidebar.markdown("**조회 조건**")
    base = st.sidebar.selectbox("기준월", months[::-1], format_func=lambda m: m.strftime("%Y-%m"))
    span = st.sidebar.slider("조회 기간(개월)", 3, 24, 6)
    return base, span


def exports(xlsx: bytes, pdf: bytes, tag: str):
    st.sidebar.markdown("**보고서 내보내기**")
    st.sidebar.download_button("📥 엑셀 다운로드", xlsx, f"통계보고서_{tag}.xlsx")
    st.sidebar.download_button("📄 PDF 다운로드", pdf, f"통계보고서_{tag}.pdf", "application/pdf")
    st.sidebar.caption("🔒 모든 처리는 이 PC 안에서만 수행됩니다.")
