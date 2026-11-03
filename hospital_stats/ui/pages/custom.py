"""사용자 지표 — 코드 수정 없이 새 통계 만들기"""
import streamlit as st
from services import analytics as A
from ui import components as C


def render(ctx):
    with C.card("사용자 지표 만들기", "기존 지표 두 개를 조합해 새 통계를 만듭니다"):
        labels = ctx.df["라벨"].tolist()
        c1, c2, c3 = st.columns([3, 1, 3])
        a = c1.selectbox("지표 A", labels, key="ua")
        op = c2.selectbox("연산", ["÷", "+", "−", "×"])
        b = c3.selectbox("지표 B", labels, index=1, key="ub")
        res = A.custom_metric(ctx, a, op, b)
        st.line_chart(res, height=280)
        st.dataframe(res.to_frame("결과").T)
