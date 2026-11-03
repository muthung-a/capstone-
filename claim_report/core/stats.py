# -*- coding: utf-8 -*-
"""
통계 엔진 — stats_config.py 에 적힌 '통계 정의(Stat)'를 읽어서 계산합니다.

보통은 이 파일을 고칠 필요가 없습니다. 새 통계는 stats_config.py 에 추가하세요.
이 파일은 '정의를 어떻게 계산하는가'만 담당합니다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

AGG_FUNCS = ("sum", "count", "mean", "nunique", "max", "min", "median")


@dataclass
class Chart:
    """통계 하나를 어떤 차트로 그릴지"""
    kind: str                    # "combo"(막대+선) / "donut"(도넛) / "hbar"(가로막대)
    title: str = ""
    subtitle: str = ""
    value: str = ""              # 막대/도넛에 쓸 값 열
    line: str = ""               # combo 에서 선으로 그릴 열
    value_format: str = "count"  # count / won / percent  (값 표시 방식)
    line_format: str = "percent"
    top_n: int = 0               # hbar 에서 위에서 N개만 (0 = 전부)
    center_key: str = ""         # donut 가운데에 강조할 항목 (예: "승인")
    center_caption: str = ""     # donut 가운데 글자 (예: "승인률")
    color: str = ""              # 막대 색. config.THEME 의 이름(예: "BAD") 또는 #RRGGBB. 비우면 파랑
    height: int = 320


@dataclass
class Stat:
    id: str                                  # 이 통계의 이름표 (config.py 에서 이 이름으로 부릅니다)
    title: str                               # 표/엑셀 시트/PDF 에 쓰일 제목
    group_by: str                            # 무엇별로 묶을지 (컬럼 이름)
    metrics: dict                            # {"결과열 이름": ("원본 컬럼", "sum"|"count"|"mean"|...)}
    formulas: dict = field(default_factory=dict)          # {"새 열": "수식"} 예: "삭감액 / 청구액 * 100"
    percent_of_total: dict = field(default_factory=dict)  # {"비율(%)": "건수"} → 전체 합 대비 %
    where: str = ""                          # 조건 (예: "조정삭감사유 != ''") — 해당 행만 계산
    sort_by: str = ""                        # 정렬 기준 열 (기본: 정렬 안 함)
    descending: bool = False
    order: Optional[list] = None             # 묶음 값의 표시 순서 (예: 승인, 조정, 삭감, 반려). 없는 값은 0건으로 표시
    decimals: int = 2
    chart: Optional[Chart] = None
    in_table: bool = True                    # 상세 통계표/엑셀/PDF 에 포함할지

    # -- 필요한 컬럼 --------------------------------------------------------
    def needs(self, known_columns) -> set:
        cols = {self.group_by}
        cols |= {src for src, _ in self.metrics.values()}
        cols |= {c for c in known_columns if c in (self.where or "")}
        return cols

    def missing(self, df_columns, known_columns) -> list:
        return sorted(self.needs(known_columns) - set(df_columns))

    # -- 계산 ---------------------------------------------------------------
    def _filter(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.where:
            return df.query(self.where, engine="python")
        return df

    def _tidy(self, g: pd.DataFrame, skip: str) -> pd.DataFrame:
        for c in g.columns:
            if c == skip or not pd.api.types.is_numeric_dtype(g[c]):
                continue
            s = g[c].replace([np.inf, -np.inf], np.nan).fillna(0)
            if (s == s.round(0)).all():
                g[c] = s.astype("int64")
            else:
                g[c] = s.round(self.decimals)
        return g

    def _build(self, d: pd.DataFrame, group_col: str) -> pd.DataFrame:
        for out, (src, fn) in self.metrics.items():
            if fn not in AGG_FUNCS:
                raise ValueError(f"[{self.id}] '{out}' 의 집계 방식 '{fn}' 은 지원하지 않습니다. 사용 가능: {AGG_FUNCS}")
        named = {out: pd.NamedAgg(column=src, aggfunc=fn) for out, (src, fn) in self.metrics.items()}
        g = d.groupby(group_col, sort=False).agg(**named).reset_index()

        if self.order and group_col == self.group_by:
            extras = [x for x in g[group_col] if x not in self.order]
            g = g.set_index(group_col).reindex(list(self.order) + extras).fillna(0).reset_index()
            g = g.rename(columns={g.columns[0]: group_col})

        for name, expr in self.formulas.items():
            g[name] = g.eval(expr)
        for name, src in self.percent_of_total.items():
            tot = g[src].sum()
            g[name] = (g[src] / tot * 100) if tot else 0.0
        return self._tidy(g, skip=group_col)

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """묶음별 결과 표"""
        d = self._filter(df)
        if d.empty:
            return pd.DataFrame(columns=[self.group_by] + list(self.metrics) + list(self.formulas)
                                + list(self.percent_of_total))
        g = self._build(d, self.group_by)
        if self.sort_by and self.sort_by in g.columns:
            g = g.sort_values(self.sort_by, ascending=not self.descending, kind="stable")
        return g.reset_index(drop=True)

    def total(self, df: pd.DataFrame) -> pd.Series:
        """전체를 한 덩어리로 계산한 값 (KPI '기간 합계' 등에 사용)"""
        d = self._filter(df).copy()
        if d.empty:
            return pd.Series(dtype=float)
        d["__all__"] = "전체"
        g = self._build(d, "__all__")
        return g.iloc[0].drop("__all__")
