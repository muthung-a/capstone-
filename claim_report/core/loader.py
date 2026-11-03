# -*- coding: utf-8 -*-
"""
파일 읽기 도구 — 엑셀/CSV 를 읽고, 컬럼 이름을 프로그램 이름으로 연결하고, 숫자/날짜를 정리합니다.

실제 병원 엑셀은 이렇게 지저분한 경우가 많아서 아래를 자동으로 처리합니다.
  · 시트가 여러 개  → 컬럼 이름이 가장 많이 맞는 시트를 기본으로 선택
  · 맨 위에 제목/빈 줄이 있음 → 컬럼 이름이 있는 줄을 자동으로 찾음
  · 숫자가 '1,234,000' 처럼 글자로 들어 있음 → 숫자로 변환
  · 청구월이 202609 / 2026.09 / 2026-09-15 등 제각각 → 2026-09 로 통일
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime

import pandas as pd

import config


def _norm(x) -> str:
    """컬럼 이름 비교용: 공백/줄바꿈/밑줄 제거, 소문자"""
    return re.sub(r"[\s_]+", "", str(x)).lower()


# 별칭 사전 (정규화된 이름 -> 논리 컬럼)
def _alias_map() -> dict:
    m = {}
    for logical, spec in config.COLUMNS.items():
        for a in [logical] + list(spec.get("aliases", [])):
            m.setdefault(_norm(a), logical)
    return m


# ---------------------------------------------------------------------------
# 파일 읽기
# ---------------------------------------------------------------------------
def is_csv(name: str) -> bool:
    return name.lower().endswith(".csv")


def sheet_names(name: str, data: bytes) -> list:
    if is_csv(name):
        return ["(CSV 파일)"]
    return pd.ExcelFile(io.BytesIO(data)).sheet_names


def _read_csv(data: bytes, **kw) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(io.BytesIO(data), encoding=enc, **kw)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(io.BytesIO(data), encoding="latin1", **kw)


MAX_GRID_CELLS = 3_000_000


def read_raw_grid(name: str, data: bytes, sheet: str) -> pd.DataFrame:
    """header=None 으로 읽은 표(모든 칸 그대로). .xlsx 는 엑셀의 '진짜 병합 범위'를 읽어서, 합쳐진 칸의 값을 범위 전체에 채워 돌려준다
    (엑셀 화면에서 보이는 모양 그대로). 빈 칸을 보고 '합쳐졌겠지' 하고 추측하지 않는다. CSV/.xls 등은 pandas 로 읽은 그대로."""
    lower = name.lower()
    if is_csv(name) or not lower.endswith((".xlsx", ".xlsm")):
        return read_table(name, data, sheet, None)
    import io
    import numpy as np
    import openpyxl
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
        ws = wb[sheet]
        n_r, n_c = ws.max_row or 0, ws.max_column or 0
        if n_r * max(n_c, 1) > MAX_GRID_CELLS:
            return read_table(name, data, sheet, None)                  # 너무 크면 기존 방식
        grid = [[None] * n_c for _ in range(n_r)]
        for row in ws.iter_rows(min_row=1, max_row=n_r, min_col=1, max_col=n_c):
            for c in row:
                if c.value is not None:
                    grid[c.row - 1][c.column - 1] = c.value
        for rng in ws.merged_cells.ranges:
            if (rng.max_row - rng.min_row + 1) * (rng.max_col - rng.min_col + 1) > 200_000:
                continue
            v = grid[rng.min_row - 1][rng.min_col - 1]
            if v is None:
                continue
            for r in range(rng.min_row, rng.max_row + 1):
                for c in range(rng.min_col, rng.max_col + 1):
                    grid[r - 1][c - 1] = v
        df = pd.DataFrame(grid, dtype=object)
        return df.where(df.notna(), np.nan)
    except KeyError:
        return read_table(name, data, sheet, None)


def read_raw_grids(name: str, data: bytes) -> dict:
    """모든 시트를 read_raw_grid 방식으로 {시트 이름: 표}"""
    return {sh: read_raw_grid(name, data, sh) for sh in sheet_names(name, data)}


def read_table(name: str, data: bytes, sheet: str, header_row: int = 0) -> pd.DataFrame:
    """header_row: 컬럼 이름이 있는 줄 (0부터 시작)"""
    if is_csv(name):
        return _read_csv(data, header=header_row)
    return pd.read_excel(io.BytesIO(data), sheet_name=sheet, header=header_row)


def guess_layout(name: str, data: bytes, max_scan_rows: int = 30) -> dict:
    """시트별로 '컬럼 이름이 있을 법한 줄'을 찾는다.  반환: {시트: (맞은 개수, 줄 번호(0부터))}"""
    amap = _alias_map()
    result = {}
    for sh in sheet_names(name, data)[:15]:
        try:
            if is_csv(name):
                head = _read_csv(data, header=None, nrows=max_scan_rows)
            else:
                head = pd.read_excel(io.BytesIO(data), sheet_name=sh, header=None, nrows=max_scan_rows)
        except Exception:
            result[sh] = (0, 0)
            continue
        best = (0, 0)
        for i in range(len(head)):
            hits = len({amap[_norm(v)] for v in head.iloc[i].tolist() if pd.notna(v) and _norm(v) in amap})
            if hits > best[0]:
                best = (hits, i)
        result[sh] = best
    return result


def best_sheet(layout: dict) -> str:
    return max(layout, key=lambda s: layout[s][0])


# ---------------------------------------------------------------------------
# 컬럼 자동 연결
# ---------------------------------------------------------------------------
def auto_map(columns) -> dict:
    """{논리 컬럼: 실제 컬럼 이름 or None}"""
    amap = _alias_map()
    found = {}
    for col in columns:
        logical = amap.get(_norm(col))
        if logical and logical not in found:
            found[logical] = col
    return {logical: found.get(logical) for logical in config.COLUMNS}


# ---------------------------------------------------------------------------
# 자료형 정리
# ---------------------------------------------------------------------------
def norm_month(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT:
        return ""
    if isinstance(v, (pd.Timestamp, datetime, date)):
        return f"{v.year:04d}-{v.month:02d}"
    s = str(v).strip()
    m = re.match(r"^(\d{4})\s*[-./년]?\s*(\d{1,2})", s)
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    return s


def to_number(series: pd.Series):
    """글자로 된 숫자('1,234원')도 숫자로. 반환: (숫자 Series, 변환 실패 개수)"""
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float), 0
    s = series.astype(str).str.replace(r"[,\s원₩]", "", regex=True)
    s = s.replace({"": None, "nan": None, "None": None, "NaT": None, "-": None})
    num = pd.to_numeric(s, errors="coerce")
    raw_blank = series.isna() | series.astype(str).str.strip().isin(["", "-", "nan", "None"])
    bad = int((num.isna() & ~raw_blank).sum())
    return num, bad


def prepare(raw: pd.DataFrame, mapping: dict):
    """실제 컬럼 → 논리 컬럼 이름으로 바꾸고 자료형을 정리. 반환: (DataFrame, 경고 목록)"""
    warns = []
    out = pd.DataFrame(index=raw.index)
    for logical, actual in mapping.items():
        if not actual or actual not in raw.columns:
            continue
        s = raw[actual]
        kind = config.COLUMNS[logical].get("type", "text")
        if kind == "number":
            num, bad = to_number(s)
            blank = int(num.isna().sum()) - bad
            if bad:
                warns.append(f"'{actual}' 에서 숫자로 바꾸지 못한 값이 {bad}개 있어 0으로 처리했습니다.")
            if blank > 0:
                warns.append(f"'{actual}' 의 빈 칸 {blank}개는 0으로 처리했습니다. (해당 없음 값이면 정상입니다)")
            out[logical] = num.fillna(0)
        elif kind == "month":
            out[logical] = s.map(norm_month)
        else:
            out[logical] = s.fillna("").astype(str).str.strip().replace({"nan": "", "None": ""})
    # 완전히 빈 줄 제거 (엑셀 맨 아래 합계/빈 줄 방지)
    if len(out.columns):
        text_cols = [c for c in out.columns if config.COLUMNS[c].get("type") != "number"]
        if text_cols:
            keep = (out[text_cols] != "").any(axis=1)
            dropped = int((~keep).sum())
            if dropped:
                warns.append(f"내용이 없는 빈 줄 {dropped}개는 제외했습니다.")
            out = out[keep]
    return out.reset_index(drop=True), warns


def check(df: pd.DataFrame) -> list:
    """데이터 점검. 반환: [("error"|"warn", 문구)]"""
    msgs = []
    if len(df.columns) == 0:
        return [("error", "아직 연결된 컬럼이 없습니다. 왼쪽 '컬럼 연결'에서 엑셀의 컬럼을 연결해 주세요. "
                          "(컬럼 이름이 적힌 줄이 맞는지는 '읽기 설정'에서 확인할 수 있어요)")]
    if df.empty:
        return [("error", "읽은 데이터가 비어 있습니다. 시트와 컬럼 이름이 있는 줄(행 번호)을 확인해 주세요.")]
    for c, spec in config.COLUMNS.items():
        if c in df.columns and spec.get("type") == "number" and (df[c] < 0).any():
            msgs.append(("warn", f"'{c}' 에 음수 값이 {int((df[c] < 0).sum())}개 있습니다. (환수/취소 건이면 정상일 수 있어요)"))
    if "심사결과" in df.columns:
        extra = sorted(set(df["심사결과"]) - set(config.RESULT_ORDER) - {""})
        if len(extra) > 8:
            msgs.append(("warn", f"심사결과에 목록에 없는 값이 {len(extra)}종류 있습니다 (예: {', '.join(extra[:5])} 외). "
                                 "항목 이름처럼 보입니다. 항목이 세로, 기간이 가로인 표라면 왼쪽 '데이터 모양'에서 '통계표'를 선택해 보세요."))
        elif extra:
            msgs.append(("warn", f"심사결과에 목록에 없는 값이 있습니다: {', '.join(extra)} — 그대로 따로 표시합니다. "
                                 "자주 나오는 값이면 config.py 의 RESULT_ORDER 에 추가하세요."))
    if "청구월" in df.columns and (df["청구월"] == "").any():
        msgs.append(("warn", f"청구월이 비어 있는 행이 {int((df['청구월'] == '').sum())}개 있습니다."))
    return msgs
