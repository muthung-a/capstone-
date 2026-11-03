# -*- coding: utf-8 -*-
"""점검용 테스트 데이터 생성기 — config.COLUMNS(데이터 계약)만 보고 가짜 데이터를 만듭니다.
샘플 파일이 없어도(실사용 모드) 점검이 돌아가게 하려는 것입니다."""
import numpy as np
import pandas as pd

import config


def make_df(n: int = 600, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    months = [f"2026-{m:02d}" for m in range(1, 7)]
    data = {}
    for col, spec in config.COLUMNS.items():
        kind = spec.get("type", "text")
        if kind == "month":
            data[col] = rng.choice(months, n)
        elif kind == "number":
            data[col] = rng.integers(0, 2_000_000, n)
        elif col == "청구번호":
            data[col] = np.array([f"ID{i:07d}" for i in range(n)])
        elif col == "심사결과" and config.RESULT_ORDER:
            data[col] = rng.choice(config.RESULT_ORDER, n, p=_probs(len(config.RESULT_ORDER)))
        elif col == "조정삭감사유":
            data[col] = rng.choice(["", "", "R1", "R2", "R3"], n)           # 빈 값도 섞어 where 조건을 시험
        else:
            data[col] = rng.choice([f"{col}{i}" for i in range(1, 5)], n)
    return pd.DataFrame(data)


def _probs(k):
    p = np.arange(k, 0, -1, dtype=float)
    return p / p.sum()
