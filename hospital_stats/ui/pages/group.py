"""그룹별 상세 페이지 (환자현황/진료비/재활/운영/인력 공용)"""
import streamlit as st
from config.settings import DEFAULT_PICK
from services import analytics as A
from ui import components as C


def render(ctx, group):
    sub = ctx.df[ctx.df["그룹"] == group]
    opts = sub["라벨"].tolist()
    default = [o for o in opts if o in DEFAULT_PICK.get(group, [])] or opts[:3]
    with C.card("지표 추이", f"{group} · 최근 {len(ctx.period)}개월"):
        c1, c2 = st.columns([5, 1])
        pick = c1.multiselect("지표 선택", opts, default=default, key=f"p_{group}", label_visibility="collapsed")
        kind = c2.segmented_control("차트", ["선", "막대"], default="선", key=f"k_{group}",
                                    label_visibility="collapsed") or "선"
        if pick:
            long = sub[sub["라벨"].isin(pick)].melt(id_vars="라벨", value_vars=ctx.period, var_name="월", value_name="값")
            long["월"] = long["월"].map(lambda m: m.strftime("%Y-%m"))
            C.trend_chart(long, kind, key=f"c_{group}")
    with C.card("상세 통계표"):
        t = A.group_table(ctx, group).set_index(["지표", "세부"])
        t["기간합계"] = t.sum(axis=1, min_count=1)
        C.data_table(t, "{:,.2f}" if group == "환자현황" else "{:,.0f}", height=460)
