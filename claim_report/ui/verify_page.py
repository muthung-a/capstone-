# -*- coding: utf-8 -*-
"""
'결과 검증' 탭 — 병원이 손으로 만든 통계표(엑셀)를 올리면, 프로그램이 계산한 같은 통계와 항목별로 비교합니다.
(같은 원 데이터에서 같은 숫자가 나오는지 확인하는 용도)
"""
import io
from difflib import SequenceMatcher

import pandas as pd
import streamlit as st

import config
import hooks
from core import loader, verify
from ui.components import card_header, show_table, wide_button


@st.cache_data(show_spinner=False)
def _sheets(name, data):
    return loader.sheet_names(name, data)


@st.cache_data(show_spinner=False)
def _read(name, data, sheet, header_row):
    return loader.read_table(name, data, sheet, header_row)


def _norm(x):
    x = str(x).replace(" ", "").replace("(원)", "").replace("(%)", "")
    for a, b in (("총액", "금액"), ("조정삭감", "삭감"), ("건수", "건")):
        x = x.replace(a, b)
    return x


def _guess(item, cols, used):
    """프로그램 항목과 이름이 가장 비슷한 병원 컬럼 추천 (너무 다르면 None)"""
    best, score = None, 0.0
    for c in cols:
        if c in used:
            continue
        r = SequenceMatcher(None, _norm(item), _norm(c)).ratio()
        if r > score:
            best, score = c, r
    return best if score >= 0.5 else None


def _num(v):
    if v is None or pd.isna(v):
        return "-"
    return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}"


def _color(v):
    return {"일치": "background-color:#E4F5EC;color:#1E7A50",
            "불일치": "background-color:#FDECEC;color:#B83A37"}.get(v, "background-color:#FFF6E0;color:#7A5600")


def render(stats, tables):
    usable = [s for s in stats if s.in_table and not tables[s.id].empty]
    with st.container(key="card-verify"):
        card_header("결과 검증", "병원이 만든 통계표와 프로그램 계산 결과를 같은 항목끼리 비교합니다.")
        st.markdown('<div class="note">비교 범위는 위쪽 <b>조회 조건</b>과 같습니다. 병원 표가 특정 기간(예: 9월)만 담고 있다면 '
                    '조회 조건의 청구월도 같은 기간으로 맞춰 주세요. 병원 파일은 이 PC 안에서만 읽습니다.</div>',
                    unsafe_allow_html=True)
        if not usable:
            st.warning("비교할 수 있는 통계가 없습니다.")
            return

        c1, c2 = st.columns(2)
        with c1:
            stat = st.selectbox("비교할 통계", usable, format_func=lambda s: s.title, key="vf_stat")
        with c2:
            up = st.file_uploader("병원이 만든 통계표 (엑셀/CSV)", type=["xlsx", "csv"], key="vf_file")
        if up is None:
            st.caption("파일을 올리면 항목을 연결해서 비교합니다. " + hooks.verify_hint())
            return

        name, data = up.name, up.getvalue()
        sheets = _sheets(name, data)
        c3, c4 = st.columns(2)
        with c3:
            sheet = st.selectbox("시트", sheets, key=f"vf_sheet::{name}") if len(sheets) > 1 else sheets[0]
        with c4:
            hdr = st.number_input("컬럼 이름이 적힌 줄 번호", min_value=1, value=1, step=1, key=f"vf_hdr::{name}")
        try:
            ref = _read(name, data, sheet, int(hdr) - 1)
        except Exception as e:
            st.error(f"병원 표를 읽지 못했습니다: {e}")
            return
        ref = ref.dropna(how="all")
        ref_cols = [str(c) for c in ref.columns]
        ref.columns = ref_cols
        with st.expander("병원 표 미리보기", expanded=False):
            st.dataframe(ref.head(10), hide_index=True)

        ours = tables[stat.id]
        metric_cols = [c for c in ours.columns if c != stat.group_by and pd.api.types.is_numeric_dtype(ours[c])]
        k1, k2 = st.columns(2)
        with k1:
            kidx = ref_cols.index(stat.group_by) if stat.group_by in ref_cols else 0
            ref_key = st.selectbox(f"병원 표에서 '{stat.group_by}' 에 해당하는 컬럼", ref_cols, index=kidx,
                                   key=f"vf_key::{name}::{stat.id}")
        with k2:
            tol = st.number_input("허용 오차 (이 값 이하의 차이는 일치로 봄)", min_value=0.0, value=0.01, step=0.01,
                                  format="%.2f", key="vf_tol",
                                  help="병원 표가 반올림한 값이면 오차를 조금 키워 보세요. 건수·금액은 0이 정확합니다.")
        chosen = st.multiselect("비교할 항목", metric_cols, default=metric_cols, key=f"vf_items::{stat.id}")
        pairs = []
        if chosen:
            st.caption("각 항목에 해당하는 병원 표의 컬럼을 고르세요. 이름이 비슷한 컬럼을 미리 골라 두었고, "
                       "병원 표에 없는 항목은 '비교 안 함'으로 두면 됩니다.")
            skip = "(비교 안 함)"
            options = [skip] + [c for c in ref_cols if c != ref_key]
            grid = st.columns(min(len(chosen), 3))
            used = set()
            for i, item in enumerate(chosen):
                guess = _guess(item, options[1:], used)
                if guess:
                    used.add(guess)
                with grid[i % len(grid)]:
                    pick = st.selectbox(f"{item}", options, index=options.index(guess) if guess else 0,
                                        key=f"vf_pair::{name}::{stat.id}::{item}")
                if pick != skip:
                    pairs.append((item, pick))
        if not pairs:
            st.info("비교할 항목을 하나 이상 연결하세요.")
            return

        is_month = config.COLUMNS.get(stat.group_by, {}).get("type") == "month"
        detail, summ = verify.compare(ours, stat.group_by, ref, ref_key, pairs, tolerance=tol, key_is_month=is_month)
        if detail.empty:
            st.warning("비교할 행이 없습니다. 구분 컬럼을 확인해 주세요.")
            return

        st.markdown(
            '<div class="sum-row">'
            f'<div class="sum-box"><div class="n">{summ["전체"]}</div><div class="l">비교한 항목</div></div>'
            f'<div class="sum-box ok"><div class="n">{summ["일치"]}</div><div class="l">일치 ({summ["일치율(%)"]}%)</div></div>'
            f'<div class="sum-box bad"><div class="n">{summ["불일치"]}</div><div class="l">불일치</div></div>'
            f'<div class="sum-box warn"><div class="n">{summ["한쪽에만 있음"]}</div><div class="l">한쪽에만 있음</div></div>'
            '</div>', unsafe_allow_html=True)
        if summ["전체"] and summ["일치"] == summ["전체"]:
            st.success("모든 항목이 병원 표와 일치합니다.")

        only_diff = st.checkbox("차이가 있는 항목만 보기", value=True, key="vf_only")
        view = detail[detail["결과"] != "일치"] if only_diff else detail
        if view.empty:
            st.caption("표시할 항목이 없습니다.")
        else:
            fmt = {c: _num for c in ["프로그램 값", "병원 값", "차이"]}
            styler = view.style.format(fmt, na_rep="-")
            styler = styler.map(_color, subset=["결과"]) if hasattr(styler, "map") else styler.applymap(_color, subset=["결과"])
            st.dataframe(styler, hide_index=True)

        buf = io.BytesIO()
        detail.to_excel(buf, index=False, sheet_name="검증결과")
        wide_button(st.download_button, "검증 결과 내려받기 (Excel)", data=buf.getvalue(),
                    file_name="검증결과.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="vf_dl")
