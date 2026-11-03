# -*- coding: utf-8 -*-
"""프로토타입 전용 화면 부품: 샘플 시작 버튼 2개(청구 내역 / 통계표)와 '샘플 끄기' 버튼 (streamlit 사용)"""
import os

import streamlit as st

from prototype import SAMPLE_PATH, SAMPLE_TABLE_PATH
from ui.components import wide_button


def active_kind():
    """지금 보고 있는 샘플 종류: "claims" / "table" / None"""
    v = st.session_state.get("use_sample")
    if v is True:
        v = "claims"
    return v if v in ("claims", "table") else None


def sample_active() -> bool:
    return active_kind() is not None


def render_empty_actions():
    """파일을 올리기 전 안내 화면 아래의 샘플 시작 버튼"""
    have_claims, have_table = os.path.exists(SAMPLE_PATH), os.path.exists(SAMPLE_TABLE_PATH)
    if not (have_claims or have_table):
        return
    _, a, b, _ = st.columns([1, 1.3, 1.3, 1])
    with a:
        if have_claims and wide_button(st.button, "샘플 데이터로 시작", type="primary", key="btn_sample_on"):
            st.session_state["use_sample"] = "claims"
            st.rerun()
    with b:
        if have_table and wide_button(st.button, "샘플 통계표로 시작", key="btn_sample_table_on"):
            st.session_state["use_sample"] = "table"
            st.rerun()


def render_sidebar_actions():
    """샘플을 보고 있을 때 사이드바의 안내와 '샘플 데이터 끄기' 버튼"""
    st.caption("샘플(가상) 데이터를 보고 있습니다.")
    if wide_button(st.button, "샘플 데이터 끄기", key="btn_sample_off"):
        st.session_state["use_sample"] = None
        st.rerun()
