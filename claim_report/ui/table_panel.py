# -*- coding: utf-8 -*-
"""
통계표 모드의 사이드바 설정: 시트 선택 → 항목 열 / 값(기간) 열 / 기간 이름 줄을 자동으로 찾아 보여주고,
틀리면 직접 고칠 수 있게 합니다. (표가 '항목이 세로, 기간이 가로'인 경우를 위한 모드)
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

from core import loader, table_mode
from core.table_mode import TableSpec, col_letter, letter_index


@dataclass
class TableLoaded:
    parsed: table_mode.Parsed
    name: str
    sig: str
    sheet: str
    kind: str = "table"


@st.cache_data(show_spinner=False)
def _raw(name, data, sheet):
    return loader.read_raw_grid(name, data, sheet)             # 모든 칸을 그대로 읽되, 엑셀의 병합된 칸은 병합 범위 전체에 채움


@st.cache_data(show_spinner=False)
def _sheet_counts(name, data):
    """시트마다 '숫자가 들어 있는 칸' 개수 (통계표가 있는 시트를 고르는 데 도움)"""
    out = {}
    for sh in loader.sheet_names(name, data)[:15]:
        try:
            raw = loader.read_raw_grid(name, data, sh).head(400)
            num, _ = table_mode._numeric(raw)
            out[sh] = int((~np.isnan(num)).sum())
        except Exception:
            out[sh] = 0
    return out


@st.cache_data(show_spinner=False)
def _detect(name, data, sheet, swap):
    raw = _raw(name, data, sheet)
    if swap:
        raw = raw.T.reset_index(drop=True)
    return table_mode.suggest(raw)                              # 같은 항목이 겹치면 블록 이름 읽는 방식까지 자동 선택


def looks_like_table(name, data, sheets) -> bool:
    """통계표(항목 × 기간)처럼 보이는지: 항목 이름 열이 있고, 숫자가 들어 있는 열이 3개 이상(기간이 가로로 놓임)"""
    counts = _sheet_counts(name, data)
    sheet = max(sheets, key=lambda s: counts.get(s, 0))
    try:
        spec = _detect(name, data, sheet, False)
    except Exception:
        return False
    return len(spec.label_cols) >= 1 and len(spec.value_cols) >= 3


def render(name, data, sig, sheets):
    """사이드바 안에서 호출. 반환: TableLoaded 또는 None"""
    counts = _sheet_counts(name, data)
    default = max(sheets, key=lambda s: counts.get(s, 0))
    sheet = default
    with st.expander("표 읽기 설정", expanded=True):
        st.caption("'항목이 세로, 기간이 가로'인 표를 읽습니다. 자동으로 찾아 둔 값이 틀리면 아래에서 고치세요.")
        if len(sheets) > 1:
            sheet = st.selectbox("시트", sheets, index=sheets.index(default), key=f"tsheet::{sig}",
                                 format_func=lambda s: f"{s}  (숫자 {counts.get(s, 0):,}칸)")
        try:
            raw0 = _raw(name, data, sheet)
        except Exception as e:
            st.error(f"'{sheet}' 시트를 읽지 못했습니다: {e}")
            return None
        swap = st.checkbox("표를 가로↔세로 바꿔서 읽기", value=False, key=f"tswap::{sig}::{sheet}",
                           help="항목 이름이 위쪽 줄에 가로로 놓여 있고 기간이 왼쪽 열에 세로로 놓여 있으면 켜세요.")
        raw = raw0.T.reset_index(drop=True) if swap else raw0
        spec0 = _detect(name, data, sheet, swap)
        if spec0.auto_note:
            st.info(spec0.auto_note)
        k = f"{sig}::{sheet}::{int(swap)}"
        letters = [col_letter(i) for i in range(raw.shape[1])]
        lab = st.multiselect("항목 이름이 있는 열", letters, default=[letters[i] for i in spec0.label_cols if i < len(letters)],
                             key=f"tlab::{k}", help="왼쪽부터 '항목 → 세부 구분' 순서로 읽습니다. (열 문자는 엑셀의 A, B, C …)")
        skipped = [letters[j] for j in range(raw.shape[1])
                   if spec0.label_cols and spec0.value_cols and spec0.label_cols[0] < j < spec0.value_cols[0]
                   and j not in spec0.label_cols and int(raw.iloc[:, j].map(lambda v: table_mode.clean_label(v, False) != "").sum()) >= 3]
        if skipped:
            st.info(f"열 {', '.join(skipped)} 에도 글자가 있습니다. 항목 이름 열이면 위 '항목 이름이 있는 열'에 추가해 보세요.")
        blk = st.multiselect("그중 '블록(구분) 이름' 열 (선택)", [x for x in lab], default=[letters[i] for i in spec0.block_cols if letters[i] in lab],
                             key=f"tblk::{k}",
                             help="같은 항목이 블록마다 반복될 때 블록 이름(예: 일반병동/재활병동)이 적힌 열. 선(구분)이 되고, "
                                  "나머지 항목 이름 열은 합쳐서 항목 이름(차트 제목)이 됩니다. 비워 두면 맨 왼쪽 열이 항목입니다.")
        val = st.multiselect("값(기간)이 있는 열", letters, default=[letters[i] for i in spec0.value_cols if i < len(letters)],
                             key=f"tval::{k}")
        hdr_end = st.number_input("머리글 마지막 줄 번호 (0 = 없음)", min_value=0, max_value=500, value=int(spec0.header_row) + 1,
                                  step=1, key=f"thdr::{k}",
                                  help="기간(월 등)이 적힌 줄 중 데이터에 가장 가까운 줄입니다.")
        hdr_start = st.number_input("머리글 첫 줄 번호", min_value=0, max_value=500,
                                    value=int(spec0.header_start if spec0.header_start >= 0 else spec0.header_row) + 1,
                                    step=1, key=f"thdr0::{k}",
                                    help="머리글이 여러 줄이면(예: 연도 줄 + 월 줄) 가장 위 줄 번호를 적으세요. 한 줄이면 마지막 줄과 같게.")
        ffill_h = st.checkbox("머리글의 합쳐진 칸 채우기", value=True, key=f"tfh::{k}",
                              help="'2026년'이 여러 칸에 걸쳐 합쳐져 있으면 첫 칸에만 글자가 있습니다. 옆 칸에도 같은 글자로 채웁니다.")
        ffill = st.checkbox("항목 이름의 합쳐진 칸(병합 셀) 채우기", value=True, key=f"tff::{k}",
                            help="항목 이름이 여러 줄에 걸쳐 합쳐져 있으면 첫 줄에만 값이 있습니다. 아래 줄에도 같은 항목으로 채웁니다.")
        ffill_s = st.checkbox("세부 구분 열도 합쳐진 칸 채우기", value=bool(spec0.ffill_sub), key=f"tfs::{k}",
                              help="둘째 항목 열(세부 구분)도 위 칸과 합쳐져 있을 때 켜세요. 빈 칸이 '없음'을 뜻하는 표라면 끄세요.")
        cont = st.checkbox("빈 줄을 건너서도 '위와 같음' 채우기 이어가기", value=not spec0.reset_on_blank, key=f"tcont::{k}",
                           help="항목 사이에 보기 좋게 빈 줄을 끼워 둔 표에서, 빈 줄 뒤의 줄들이 항목 이름을 잃을 때 켜세요.")
        sect = st.checkbox("값 없는 제목 줄을 블록 이름(구분)으로 사용", value=bool(spec0.use_sections), key=f"tsec::{k}",
                           help="같은 항목이 블록마다 반복되고, 각 블록 위에 '[일반]' 같은 제목 줄(값이 없는 줄)이 있을 때 켜세요.")
        rev = st.checkbox("항목 열 순서 바꾸기 (왼쪽 열 = 세부 구분)", value=bool(spec0.reverse_labels), key=f"trev::{k}",
                          help="항목 이름 열이 둘 이상일 때, 왼쪽 열이 '블록 이름'이고 오른쪽 열이 '항목'이면 켜세요.")
        ratio = st.checkbox("이름에 '율'이 있고 값이 0~1이면 %로 표시", value=True, key=f"tratio::{k}",
                            help="병상가동율 0.96 → 96%. 원본이 이미 %(예: 96)로 적혀 있으면 영향이 없습니다.")
        tidy = st.checkbox("글자 사이 띄어쓰기 정리 (예: '총 진 료 비' → '총진료비')", value=True, key=f"tt::{k}")
        dsum = st.checkbox("합계·평균 열은 기간에서 제외", value=True, key=f"td::{k}")

    with st.expander("원본 표 앞부분 보기 (이 PC 화면에서만 보입니다)", expanded=False):
        st.dataframe(raw.head(15), hide_index=True)

    h_end = int(hdr_end) - 1 if int(hdr_end) > 0 else -1
    h_start = min(int(hdr_start) - 1, h_end) if (int(hdr_start) > 0 and h_end >= 0) else h_end
    spec = TableSpec(header_row=h_end, header_start=h_start, label_cols=sorted(letter_index(x) for x in lab),
                     value_cols=sorted(letter_index(x) for x in val), ffill=ffill, ffill_sub=ffill_s, reset_on_blank=not cont, ffill_header=ffill_h,
                     block_cols=sorted(letter_index(x) for x in blk if x in lab), use_sections=sect, reverse_labels=rev, ratio_to_pct=ratio, clean_labels=tidy, drop_summary_cols=dsum)
    try:
        parsed = table_mode.parse(raw, spec)
    except Exception as e:                       # 설정이 잘못돼도 화면이 멈추지 않게
        st.error(f"표를 읽지 못했습니다: {type(e).__name__}: {e}")
        return None
    st.caption(f"읽은 결과: 항목 {len(parsed.items):,}개 · 기간 {len(parsed.periods):,}개 · 값 {len(parsed.long):,}개")
    if parsed.duplicates:
        st.warning(f"같은 항목이 겹치는 값 {parsed.duplicates:,}개가 있습니다. 블록 이름이 있는 열/제목 줄을 위 설정에서 지정해 보세요.")
    if parsed.columns:
        with st.expander("머리글을 이렇게 읽었어요 (열마다 기간 / 구분)", expanded=False):
            st.caption("열마다 '기간'과 '구분'이 맞게 나뉘었는지 확인하세요. 틀리면 위의 머리글 줄 번호를 바꿔 보세요. (이 PC 화면에서만 보입니다)")
            view = pd.DataFrame(parsed.columns, columns=["열", "기간", "구분", "제외"])
            view["제외"] = view["제외"].map({True: "합계/평균 → 제외", False: ""})
            st.dataframe(view.head(60), hide_index=True)
    return TableLoaded(parsed=parsed, name=name, sig=sig, sheet=sheet)
