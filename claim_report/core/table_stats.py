# -*- coding: utf-8 -*-
"""통계표 모드의 계산: 항목×기간 표 만들기, 항목별 증감 요약, 자동 요약 문장, 숫자 표기 (streamlit 을 가져오지 않음)"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.table_mode import ITEM, PERIOD, SUB, VALUE

SUMMARY_COLS = [ITEM, SUB, "최근기간", "직전기간", "최근값", "직전값", "증감", "증감률(%)", "평균", "최대", "최소", "값개수"]


def fmt_num(v, pct: bool = False) -> str:
    """숫자를 읽기 좋게: 천 단위 쉼표, 정수는 소수점 없이, 소수는 최대 2자리. 값이 없으면 '-'"""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    v = float(v)
    s = f"{int(round(v)):,}" if abs(v - round(v)) < 1e-9 else f"{v:,.2f}".rstrip("0").rstrip(".")
    return s + ("%" if pct else "")


def matrix(long: pd.DataFrame, series: list, periods: list) -> pd.DataFrame:
    """행 = (항목, 하위구분) 표에 나온 순서, 열 = 기간. 값이 없는 칸은 NaN"""
    if long.empty:
        return pd.DataFrame(columns=periods, index=pd.MultiIndex.from_tuples([], names=[ITEM, SUB]))
    m = long.set_index([ITEM, SUB, PERIOD])[VALUE].unstack(PERIOD)
    m = m.reindex(columns=periods)
    idx = pd.MultiIndex.from_tuples([k for k in series if k in m.index], names=[ITEM, SUB])
    return m.reindex(idx)


def summary(mat: pd.DataFrame) -> pd.DataFrame:
    """(항목, 하위구분)마다 최근값, 직전값, 증감, 증감률, 평균, 최대, 최소"""
    rows = []
    cols = list(mat.columns)
    for (item, sub), s in mat.iterrows():
        v = s.to_numpy(dtype=float)
        ok = np.nonzero(~np.isnan(v))[0]
        if len(ok) == 0:
            continue
        last = ok[-1]
        prev = ok[-2] if len(ok) >= 2 else None
        d = (v[last] - v[prev]) if prev is not None else np.nan
        rate = (d / abs(v[prev]) * 100) if (prev is not None and v[prev] != 0) else np.nan
        vv = v[ok]
        rows.append([item, sub, cols[last], "" if prev is None else cols[prev], v[last], np.nan if prev is None else v[prev], d, rate,
                     float(vv.mean()), float(vv.max()), float(vv.min()), len(ok)])
    return pd.DataFrame(rows, columns=SUMMARY_COLS)


def label_of(item: str, sub: str) -> str:
    return f"{item} · {sub}" if sub else item


def sentences(summ: pd.DataFrame, periods: list) -> list:
    """보고서에 쓸 법한 한 줄 코멘트 (화면에 넣을 때는 반드시 이스케이프)"""
    if summ.empty or not periods:
        return ["요약할 수 있는 항목이 아직 없습니다. 항목과 기간을 선택해 주세요."]
    n_items = summ[ITEM].nunique()
    count = f"{n_items:,}개" + (f"(구분까지 {len(summ):,}줄)" if len(summ) > n_items else "")
    out = [f"선택한 항목 {count}의 기간은 {periods[0]} ~ {periods[-1]} 입니다."]
    cmp = summ[summ["증감률(%)"].notna() & (summ["값개수"] >= 2)]
    if not cmp.empty:
        up, down = cmp.loc[cmp["증감률(%)"].idxmax()], cmp.loc[cmp["증감률(%)"].idxmin()]
        if up["증감률(%)"] > 0:
            out.append(f"직전 값 대비 가장 크게 늘어난 항목은 '{label_of(up[ITEM], up[SUB])}'으로 "
                       f"{fmt_num(up['직전값'])} → {fmt_num(up['최근값'])} ({up['증감률(%)']:+.1f}%) 입니다.")
        if down["증감률(%)"] < 0:
            out.append(f"직전 값 대비 가장 크게 줄어든 항목은 '{label_of(down[ITEM], down[SUB])}'으로 "
                       f"{fmt_num(down['직전값'])} → {fmt_num(down['최근값'])} ({down['증감률(%)']:+.1f}%) 입니다.")
    stale = summ[summ["최근기간"] != periods[-1]]
    if len(stale):
        out.append(f"마지막 기간({periods[-1]})의 값이 없는 항목이 {len(stale):,}개 있습니다. (가장 최근 값을 대신 보여줍니다)")
    return out
