# -*- coding: utf-8 -*-
"""
자동 요약 문장 만들기 — 통계 결과 표에서 보고서에 쓸 법한 한 줄 코멘트를 뽑습니다.
어떤 통계/컬럼을 쓸지는 config.py 의 INSIGHT 에서 정합니다. 필요한 값이 없으면 그 문장은 건너뜁니다.
"""
import pandas as pd

import config


def generate(tables: dict) -> list:
    cfg = config.INSIGHT
    out = []

    t = tables.get(cfg["time_stat"])
    if t is not None and not t.empty and cfg["time_col"] in t.columns:
        m = t.sort_values(cfg["time_col"]).reset_index(drop=True)
        tc, rc, cc = cfg["time_col"], cfg["rate"], cfg["count"]
        has_rate, has_count = rc in m.columns, cc in m.columns
        last = m.iloc[-1]
        prev = m.iloc[-2] if len(m) >= 2 else None

        if has_rate:
            if prev is not None:
                diff = last[rc] - prev[rc]
                word = "상승" if diff > 0 else ("하락" if diff < 0 else "동일")
                out.append(f"{last[tc]} {cfg['rate_label']}은 {last[rc]}%로, 전월({prev[rc]}%) 대비 "
                           f"{abs(diff):.2f}%p {word}했습니다.")
            else:
                out.append(f"{last[tc]} {cfg['rate_label']}은 {last[rc]}%입니다.")
        if has_count and prev is not None:
            d = int(last[cc] - prev[cc])
            word = "증가" if d > 0 else ("감소" if d < 0 else "동일")
            out.append(f"{last[tc]} {cfg['count_label']}는 {int(last[cc]):,}건으로, 전월 대비 {abs(d):,}건 {word}했습니다.")
        if has_rate and len(m) >= 2:
            hi, lo = m.loc[m[rc].idxmax()], m.loc[m[rc].idxmin()]
            out.append(f"조회 기간 중 {cfg['rate_label']}이 가장 높았던 달은 {hi[tc]}({hi[rc]}%), "
                       f"가장 낮았던 달은 {lo[tc]}({lo[rc]}%)입니다.")

    g = tables.get(cfg["group_stat"])
    if g is not None and not g.empty and cfg["rate"] in g.columns and cfg["group_col"] in g.columns:
        w = g.loc[g[cfg["rate"]].idxmax()]
        out.append(f"{cfg['group_label']} 중에서는 '{w[cfg['group_col']]}'의 {cfg['rate_label']}이 "
                   f"{w[cfg['rate']]}%로 가장 높아, 청구 시 유의가 필요합니다.")

    return out or ["요약할 수 있는 통계가 아직 없습니다. 컬럼 연결을 확인해 주세요."]
