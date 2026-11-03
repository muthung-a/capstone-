import plotly.express as px
import streamlit as st
from ui import components as C


def render(nurse):
    if nurse.empty:
        st.info("'간호등급 (YYYYQ)' 시트가 없습니다.")
        return
    jobs = [c for c in nurse.columns if c not in ("연도", "분기", "월", "재직인원", "기준")]
    with C.card("월별 간호인력 재직 인원", "매월 15일 기준"):
        f = px.bar(nurse, x="기준", y=jobs)
        f.update_layout(height=340, legend_title_text="", xaxis_title="", yaxis_title="명")
        st.plotly_chart(f, key="nurse")
    with C.card("분기 평균 재직 인원"):
        q = nurse.groupby(["연도", "분기"])["재직인원"].mean().round(1).rename("평균 재직인원").reset_index()
        st.dataframe(q, hide_index=True)
