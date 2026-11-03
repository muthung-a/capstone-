# -*- coding: utf-8 -*-
"""
왼쪽 사이드바: 파일 올리기 → (시트/제목 줄 자동 탐지) → 컬럼 자동 연결 → 경고 기준 슬라이더
반환: (Loaded 또는 None, 경고 기준 값)
"""
import hashlib
from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

import config
import hooks
import stats_config
from core import anonymize, loader
from ui import table_panel


@dataclass
class Loaded:
    df: pd.DataFrame
    name: str
    sig: str                                   # 파일을 구분하는 짧은 코드 (위젯 상태 초기화용)
    mapping: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)   # 사람이 확인하면 좋은 메모
    issues: list = field(default_factory=list)     # [("error"|"warn", 문구)]
    kind: str = "claims"                           # 청구 내역 모드


@st.cache_data(show_spinner=False)
def _layout(name, data):
    return loader.guess_layout(name, data)


@st.cache_data(show_spinner=False)
def _read(name, data, sheet, header_row):
    return loader.read_table(name, data, sheet, header_row)


@st.cache_data(show_spinner="구조 복제본을 만드는 중입니다...")
def _replica(name, data):
    return anonymize.make_replica(name, data)


def _replica_panel(name, data):
    """공유용 '구조 복제본': 이름·값을 전부 가짜로 바꾸고 구조만 남긴 엑셀. 실제 병원 파일 대신 구조 문제를 설명/재현할 때 사용"""
    with st.expander("공유용 구조 복제본 만들기", expanded=False):
        st.caption("원본의 **이름과 값을 전부 가짜로 바꾸고 구조(병합 셀·머리글·반복 모양·서식)만 남긴** 새 엑셀을 만듭니다. "
                   "시트 이름·문서 속성·메모도 들어가지 않습니다. 다만 값 사이의 관계(합계 = 구분의 합 등)와 추세는 남지 않습니다.")
        st.warning("복제본도 병원 파일에서 만든 것입니다. 외부(AI 포함)에 보여주기 전에 **직접 열어서 확인하고, 병원/교수님의 허락**을 받으세요.")
        if st.button("복제본 만들기", key=f"rep::{hashlib.md5(data).hexdigest()[:8]}"):
            rep, report, ok = _replica(name, data)
            for line in report:
                st.write("• " + line)
            if ok and rep:
                st.success("원본 이름이 남아 있지 않은 것을 확인했습니다. 내려받은 파일을 직접 열어 한 번 더 확인하세요.")
                st.download_button("복제본 내려받기 (.xlsx)", data=rep, file_name="구조복제본.xlsx", key=f"repdl::{hashlib.md5(data).hexdigest()[:8]}",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.error("안전하게 만들 수 없어 복제본을 만들지 않았습니다. 위 내용을 확인하세요.")


def _needed_columns():
    need = {f["column"] for f in config.FILTERS}
    for s in stats_config.STATS:
        need |= s.needs(config.COLUMNS.keys())
    return need


def render_sidebar():
    loaded = None

    with st.sidebar:
        st.markdown('<div class="side-title">데이터</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("청구 데이터 파일", type=["xlsx", "csv"], label_visibility="collapsed",
                                    help="엑셀(xlsx) 또는 CSV 파일을 올려주세요. 파일은 이 PC 안에서만 처리됩니다.")
        name = data = None
        if uploaded is not None:
            name, data = uploaded.name, uploaded.getvalue()
        else:
            src = hooks.sample_source_if_active()      # 프로토타입 모드에서만 값이 있음
            if src:
                name, data = src
                hooks.render_sidebar_actions()

        if data is not None:
            loaded = _load_with_controls(name, data)
            _replica_panel(name, data)

        st.markdown('<div class="side-title">경고 기준</div>', unsafe_allow_html=True)
        threshold = st.slider(config.ALERT_LABEL, min_value=config.ALERT_MIN, max_value=config.ALERT_MAX,
                              value=config.ALERT_DEFAULT, step=config.ALERT_STEP,
                              help="최근월 값이 이 기준을 넘으면 경고가 표시됩니다. 실제 병원 기준에 맞게 조정하세요.")
    return loaded, threshold


def _load_with_controls(name, data):
    sig = hashlib.md5(data).hexdigest()[:8]
    try:
        layout = _layout(name, data)
    except Exception as e:
        st.error(f"파일을 읽지 못했습니다: {e}")
        return None
    sheets = list(layout)
    guess_sheet = loader.best_sheet(layout)

    # 데이터 모양: 컬럼 이름이 프로그램 컬럼과 거의 안 맞고, 숫자 열이 여러 개(기간)로 펼쳐진 모양이면 '통계표'를 먼저 추천
    suggest_table = layout[guess_sheet][0] < 3 and table_panel.looks_like_table(name, data, sheets)
    mode = st.radio("데이터 모양", ["청구 내역 (한 줄 = 청구 1건)", "통계표 (항목 × 기간)"], index=1 if suggest_table else 0,
                    key=f"mode::{sig}",
                    help="청구 내역: 청구 한 건이 한 줄인 표.  통계표: 항목 이름이 세로, 기간(월 등)이 가로인 표.  "
                         "파일 모양에 맞춰 자동으로 골라 두었고, 바꿀 수 있어요.")
    if mode.startswith("통계표"):
        return table_panel.render(name, data, sig, sheets)

    with st.expander("읽기 설정 (시트 / 제목 줄)", expanded=False):
        sheet = guess_sheet
        if len(sheets) > 1:
            sheet = st.selectbox("시트", sheets, index=sheets.index(guess_sheet), key=f"sheet::{sig}")
        guess_hdr = layout.get(sheet, (0, 0))[1]
        hdr1 = st.number_input("컬럼 이름이 적힌 줄 번호", min_value=1, max_value=200, value=int(guess_hdr) + 1,
                               step=1, key=f"hdr::{sig}::{sheet}",
                               help="엑셀 맨 위에 제목이나 빈 줄이 있으면 컬럼 이름이 있는 줄 번호를 적어주세요. 자동으로 찾아둔 값이 들어 있어요.")
    try:
        raw = _read(name, data, sheet, int(hdr1) - 1)
    except Exception as e:
        st.error(f"'{sheet}' 시트를 읽지 못했습니다: {e}")
        return None

    auto = loader.auto_map(list(raw.columns))
    need = _needed_columns()
    miss_needed = [c for c in need if auto.get(c) is None]

    with st.expander(f"컬럼 연결 (연결 안 된 필수 컬럼 {len(miss_needed)}개)", expanded=bool(miss_needed)):
        st.caption("엑셀의 컬럼을 프로그램 컬럼에 연결합니다. 이름이 비슷하면 자동으로 맞춰 둡니다.")
        by_str = {str(c): c for c in raw.columns}
        options = ["(연결 안 함)"] + list(by_str)
        mapping = {}
        for logical in config.COLUMNS:
            cur = auto.get(logical)
            idx = options.index(str(cur)) if cur is not None and str(cur) in options else 0
            label = logical + ("  ·  필수" if logical in need else "")
            pick = st.selectbox(label, options, index=idx, key=f"map::{sig}::{sheet}::{int(hdr1)}::{logical}")
            mapping[logical] = by_str.get(pick)

    df, warns = loader.prepare(raw, mapping)
    return Loaded(df=df, name=name, sig=sig, mapping=mapping, warnings=warns, issues=loader.check(df))
