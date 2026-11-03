# -*- coding: utf-8 -*-
"""조회 조건 카드 — config.py 의 FILTERS 대로 필터를 그리고, 조건에 맞는 행만 돌려줍니다."""
import pandas as pd
import streamlit as st

import config
from ui.components import card_header


def render(df: pd.DataFrame, sig: str) -> pd.DataFrame:
    specs = [f for f in config.FILTERS if f["column"] in df.columns]
    if not specs:
        return df
    mask = pd.Series(True, index=df.index)

    def widget(f):
        col, kind = f["column"], f["kind"]
        opts = sorted(x for x in df[col].unique() if x != "")
        key = f"flt::{sig}::{col}"
        if kind == "period":
            if len(opts) > 1:
                lo, hi = st.select_slider(f["label"], options=opts, value=(opts[0], opts[-1]), key=key)
                chosen = [x for x in opts if lo <= x <= hi]
            else:
                st.markdown(f"{f['label']}  \n**{opts[0] if opts else '-'}**")
                chosen = opts
        else:
            chosen = st.pills(f["label"], opts, selection_mode="multi", default=opts, key=key) or []
        return df[col].isin(chosen)

    with st.container(key="card-filter"):
        card_header("조회 조건")
        first = [f for f in specs if f["kind"] == "period" or df[f["column"]].nunique() <= 3]
        rest = [f for f in specs if f not in first]
        if first:
            cols = st.columns([1.4 if f["kind"] == "period" else 1 for f in first])
            for c, f in zip(cols, first):
                with c:
                    mask &= widget(f)
        for f in rest:
            mask &= widget(f)
    return df[mask]
