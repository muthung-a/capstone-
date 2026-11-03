# -*- coding: utf-8 -*-
"""화면에서 반복해서 쓰는 작은 부품: 상단 바, 카드 제목, KPI 카드, 표, 버튼"""
from contextlib import contextmanager

import pandas as pd
import streamlit as st

import config
import hooks
from core.format import esc, strip_lead


def top_bar(right_html=""):
    badge = f'<span class="chip chip-demo">{esc(hooks.badge_text())}</span>' if hooks.badge_text() else ""
    st.markdown(
        f'<div class="gnb"><div><span class="gnb-title">{config.APP_TITLE}</span>'
        f'<span class="gnb-sub">{config.APP_SUBTITLE}</span></div>'
        f'<div class="gnb-right">{badge}{right_html}</div></div>',
        unsafe_allow_html=True)


def chip(text):
    """상단 바의 회색 알약. 파일 이름 같은 외부 글자는 여기서 이스케이프됩니다."""
    return f'<span class="chip chip-data">{esc(text)}</span>'


def warn_line(text):
    st.markdown(f'<div class="warn-line">• {esc(text)}</div>', unsafe_allow_html=True)


def insight_list(lines):
    items = "".join(f"<li>{esc(strip_lead(line))}</li>" for line in lines)
    st.markdown(f'<ul class="insights">{items}</ul>', unsafe_allow_html=True)


@contextmanager
def guard(label):
    """한 영역에서 오류가 나도 화면 전체가 멈추지 않게 격리합니다 (오류 내용은 그 자리에 경고로 표시)."""
    try:
        yield
    except Exception as e:  # noqa: BLE001  (st.stop/st.rerun 은 Exception 이 아니라 여기서 잡히지 않음)
        st.warning(f"'{label}' 영역을 표시하지 못했습니다: {type(e).__name__}: {e}")


def card_header(title, sub=""):
    sub_html = f'<div class="card-sub">{sub}</div>' if sub else ""
    st.markdown(f'<div class="card-title">{title}</div>{sub_html}', unsafe_allow_html=True)


def kpi_html(label, value, unit, delta_text=None, tone="flat", vs_text="", foot="", over=False):
    cls = "kpi over" if over else "kpi"
    vcls = "kpi-value over" if over else "kpi-value"
    if delta_text is None:
        delta = '<span class="kpi-delta tone-flat">비교할 전월 없음</span>'
    else:
        delta = f'<span class="kpi-delta tone-{tone}">{delta_text}</span><span class="kpi-vs">{vs_text}</span>'
    return (f'<div class="{cls}"><div class="kpi-label">{label}</div>'
            f'<div class="{vcls}">{value}<span class="kpi-unit">{unit}</span></div>'
            f'<div>{delta}</div><div class="kpi-foot">{foot}</div></div>')


def wide_button(fn, *args, **kwargs):
    """버튼을 칸 너비에 꽉 차게 (스트림릿 버전에 따라 옵션 이름이 달라 둘 다 시도)"""
    try:
        return fn(*args, width="stretch", **kwargs)
    except TypeError:
        return fn(*args, use_container_width=True, **kwargs)


def show_table(df: pd.DataFrame, height=None):
    """표 출력 (숫자에 천 단위 쉼표). 실패하면 기본 표로 출력"""
    try:
        cfg = {}
        for c in df.columns:
            if pd.api.types.is_integer_dtype(df[c]):
                cfg[c] = st.column_config.NumberColumn(format="%,d")
            elif pd.api.types.is_float_dtype(df[c]):
                cfg[c] = st.column_config.NumberColumn(format="%.2f")
        kwargs = {"hide_index": True, "column_config": cfg}
        if height:
            kwargs["height"] = height
        st.dataframe(df, **kwargs)
    except Exception:
        st.dataframe(df, hide_index=True)
