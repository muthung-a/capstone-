import plotly.express as px
import streamlit as st
from core.drug_loader import drug_by_dept
from ui import components as C


def render(drugs):
    if drugs.empty:
        st.info("약품 시트(이름이 숫자인 시트: 6, 7, …)가 없습니다.")
        return
    dept = drug_by_dept(drugs)
    dept.index = [f"{i}월" for i in dept.index]
    with C.card("진료과별 약품 처방금액", "월별 누적 · 단위 원"):
        f = px.bar(dept, barmode="stack")
        f.update_layout(height=340, legend_title_text="", xaxis_title="", yaxis_title="")
        st.plotly_chart(f, key="drug_dept")
        C.data_table(dept)
    with C.card("처방금액 TOP 10"):
        m = st.pills("월", sorted(drugs["월"].unique()), default=drugs["월"].max(),
                     format_func=lambda x: f"{x}월", key="drug_m") or drugs["월"].max()
        top = drugs[drugs["월"] == m].nlargest(10, "총금액")[["약품명", "제약회사", "처방횟수", "총금액"]]
        st.dataframe(top.style.format({"총금액": "{:,.0f}", "처방횟수": "{:,.0f}"}), hide_index=True)
