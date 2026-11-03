# -*- coding: utf-8 -*-
"""
통계표 모드 — '항목 × 기간' 모양의 표(예: 병원이 매달 만드는 통계표)를 읽어서
긴 형태(항목, 하위구분, 기간, 값)로 바꿉니다.  (streamlit 을 가져오지 않는 순수 계산 모듈)

자동으로 처리하는 것
  · 항목 이름이 있는 열 / 값(기간)이 있는 열 / 기간 이름이 적힌 줄 찾기
  · 합쳐진 칸(병합 셀)로 비어 보이는 항목 이름 채우기 (완전히 빈 줄을 만나면 끊음)
  · 글자 사이를 띄어 쓴 이름 정리: '본 인 부 담 금' → '본인부담금'
  · '1,234'  '87.5%'  '(123)'  '△123' 같은 숫자 표기 읽기, '-' 는 빈 값으로
  · 기간 이름 통일: 2026-07 / 2026.07 / 2026년 7월 / 202607 / 엑셀 날짜 → 2026-07,  '7월' 은 그대로
  · 합계·평균 열은 기간에서 제외 (선택)
자동으로 못 맞추면 화면에서 열/줄을 직접 고르거나 표를 가로세로 바꿀 수 있습니다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date, datetime

import numpy as np
import pandas as pd

SUMMARY_WORDS = re.compile(r"합\s*계|총\s*계|소\s*계|누\s*계|평\s*균|^계$|전\s*체|^total$|^sum$|^avg$|^average$", re.I)
_BLANK_TOKENS = {"", "-", "–", "—", "n/a", "na", "nan", "none", "null"}
ITEM, SUB, PERIOD, VALUE = "항목", "하위구분", "기간", "값"


# ---------------------------------------------------------------------------
# 작은 도구
# ---------------------------------------------------------------------------
def col_letter(i: int) -> str:
    """0 → A, 25 → Z, 26 → AA"""
    s, i = "", i + 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def letter_index(s: str) -> int:
    n = 0
    for ch in str(s).upper():
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def to_num(v):
    """셀 하나를 (숫자, %표시여부) 로. 숫자가 아니면 (nan, False)"""
    if v is None or isinstance(v, (bool, np.bool_)):
        return np.nan, False
    if isinstance(v, (int, float, np.integer, np.floating)):
        x = float(v)
        return (x, False) if not np.isnan(x) else (np.nan, False)
    if isinstance(v, (datetime, date, pd.Timestamp)):
        return np.nan, False
    s = str(v).strip()
    if s.lower() in _BLANK_TOKENS:
        return np.nan, False
    pct = s.endswith("%")
    s = s.rstrip("%").strip()
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    if s[:1] in ("△", "▽"):                       # △ 는 감소(음수)로 쓰는 표가 많음
        neg, s = True, s[1:]
    s = re.sub(r"[,\s]", "", s)
    try:
        x = float(s)
    except ValueError:
        return np.nan, False
    return (-x if neg else x), pct


def clean_label(v, tidy: bool = True) -> str:
    """항목 이름 정리. tidy=True 면 글자 사이를 띄어 쓴 이름('본 인 부 담 금')을 붙인다."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    s = re.sub(r"[\u00a0\u3000\t\r\n]+", " ", str(v)).strip()
    s = re.sub(r" {2,}", " ", s)
    if not tidy or not s:
        return s
    toks = s.split(" ")
    hangul = lambda t: len(t) == 1 and "가" <= t <= "힣"  # noqa: E731
    if (len(toks) == 2 and all(hangul(t) for t in toks)) or (len(toks) >= 3 and all(len(t) == 1 for t in toks)):
        return "".join(toks)
    return s


def period_label(cell, fallback: str) -> str:
    """기간(열 머리글) 이름 통일"""
    if cell is None or (isinstance(cell, float) and np.isnan(cell)):
        return fallback
    if isinstance(cell, (pd.Timestamp, datetime, date)):
        return f"{cell.year:04d}-{cell.month:02d}"
    if isinstance(cell, (int, np.integer)) or (isinstance(cell, (float, np.floating)) and float(cell).is_integer()):
        s = str(int(cell))
    else:
        s = clean_label(cell)
    if not s:
        return fallback
    m = re.match(r"^(\d{4})\s*[-./년]\s*(\d{1,2})", s) or re.match(r"^(\d{4})(\d{2})$", s)
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.match(r"^(\d{1,2})\s*월", s)
    if m and 1 <= int(m.group(1)) <= 12:
        return f"{int(m.group(1))}월"
    return s


def order_periods(labels: list) -> list:
    """연-월이면 시간순, 'N월' 이면 월 순서, 그 외는 표에 적힌 순서"""
    if labels and all(re.fullmatch(r"\d{4}-\d{2}", x) for x in labels):
        return sorted(labels)
    if labels and all(re.fullmatch(r"\d{1,2}월", x) for x in labels):
        return sorted(labels, key=lambda x: int(x[:-1]))
    return list(labels)


def _numeric(raw: pd.DataFrame):
    vals = raw.to_numpy(dtype=object)
    num = np.full(vals.shape, np.nan)
    pct = np.zeros(vals.shape, dtype=bool)
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            num[i, j], pct[i, j] = to_num(vals[i, j])
    return num, pct


def _empty_mask(raw: pd.DataFrame) -> np.ndarray:
    vals = raw.to_numpy(dtype=object)
    out = np.ones(vals.shape, dtype=bool)
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            out[i, j] = clean_label(vals[i, j], tidy=False) == ""
    return out


def _header_like(nums: np.ndarray) -> bool:
    """연도(2026, 2027…)나 월 번호(1,2,3…)처럼 '머리글로 쓴 숫자' 줄인지"""
    if len(nums) < 2 or not np.all(nums == np.round(nums)):
        return False
    if np.all((nums >= 1900) & (nums <= 2100)):
        return True
    return len(nums) >= 3 and nums[0] == 1 and bool(np.all(np.diff(nums) == 1))      # 1,2,3… 으로 시작할 때만 (월/일 번호)


# ---------------------------------------------------------------------------
# 구조 자동 탐지
# ---------------------------------------------------------------------------
@dataclass
class TableSpec:
    header_row: int = -1                                   # 머리글의 마지막 줄 (데이터 바로 위, 0부터). 없으면 -1
    header_start: int = -1                                 # 머리글의 첫 줄 (여러 줄 머리글이면 header_row 보다 위). -1 이면 한 줄
    label_cols: list = field(default_factory=list)         # 항목 이름 열 (0부터, 왼쪽부터 항목/하위구분 순서)
    value_cols: list = field(default_factory=list)         # 값(기간) 열
    ffill: bool = True                                     # 항목 이름의 합쳐진 칸 채우기
    ffill_sub: bool = False                                # 세부 구분 열의 합쳐진 칸도 채우기
    ffill_header: bool = True                              # 머리글의 합쳐진 칸 채우기
    use_sections: bool = False                             # 값 없는 제목 줄(블록 이름)을 구분으로 사용
    block_cols: list = field(default_factory=list)         # 항목 이름 열 중 '블록(구분) 이름' 열 (선이 되는 쪽). 나머지 열은 합쳐서 항목 이름이 됨
    reverse_labels: bool = False                           # 항목 열 순서 바꾸기 (왼쪽 열 = 세부 구분, 맨 오른쪽 열 = 항목)
    ratio_to_pct: bool = True                              # 이름에 '율'이 있고 값이 0~1 사이면 %로 바꿔 표시
    reset_on_blank: bool = True                            # 완전히 빈 줄에서 '위와 같음' 채우기를 끊음 (꺼지면 빈 줄을 건너 계속 채움)
    auto_note: str = ""                                     # 자동으로 한 일 안내 (예: 겹침을 없애려고 열 D 를 항목 이름 열에 추가)
    clean_labels: bool = True                              # 글자 사이 띄어쓰기 정리
    drop_summary_cols: bool = True                         # 합계/평균 열 제외


def detect(raw: pd.DataFrame) -> TableSpec:
    """header=None 으로 읽은 표에서 항목 열 / 값 열 / 머리글 줄(여러 줄 포함)을 추정"""
    n_r, n_c = raw.shape
    if n_r == 0 or n_c == 0:
        return TableSpec()
    num, _ = _numeric(raw)
    isnum = ~np.isnan(num)
    empt = _empty_mask(raw)
    cnt = isnum.sum(axis=1)
    data_rows = [i for i in range(n_r) if cnt[i] >= 2 and not _header_like(num[i][isnum[i]])]
    if not data_rows:
        return TableSpec(label_cols=[0], value_cols=list(range(1, n_c)))

    region = np.array(data_rows)
    nonempty_cnt = (~empt[region]).sum(axis=0)
    isnum_cnt = isnum[region].sum(axis=0)
    ratio = isnum_cnt / np.maximum(nonempty_cnt, 1)

    label_cols, j = [], 0
    while j < n_c and len(label_cols) < 3:
        if nonempty_cnt[j] == 0:                      # 빈 열(여백)은 건너뜀
            j += 1
            continue
        if ratio[j] < 0.3:
            label_cols.append(j)
            j += 1
        else:
            break
    start = (label_cols[-1] + 1) if label_cols else 0
    value_cols = [k for k in range(start, n_c) if isnum_cnt[k] >= 2 and ratio[k] >= 0.25]
    if not label_cols and value_cols and value_cols[0] > 0:
        label_cols = [value_cols[0] - 1]

    first = data_rows[0]
    best, best_cnt = -1, 0
    for i in range(first - 1, max(-1, first - 6), -1):          # 첫 데이터 줄 바로 위쪽에서 머리글의 마지막 줄 찾기
        c = sum(1 for k in value_cols if not empt[i, k])
        if c > best_cnt:
            best, best_cnt = i, c
    header_row = best if best_cnt >= max(2, len(value_cols) // 3) else -1
    header_start = header_row
    if header_row >= 0:                                          # 그 위로 이어지는 머리글 줄(합쳐진 연도/구분 줄 등)
        i = header_row - 1
        while i >= 0 and header_row - i < 4:
            labs = [period_label(raw.iat[i, k], "") for k in value_cols if not empt[i, k]]
            if not labs:
                break
            if len(labs) == 1 and not (_YEAR_RE.match(labs[0]) or _MONTH_RE.match(labs[0])):
                break                                   # 한 칸짜리 일반 글자 = 표 제목/단위 줄. 머리글이 아님
            header_start = i
            i -= 1
    return TableSpec(header_row=header_row, header_start=header_start, label_cols=label_cols, value_cols=value_cols)


# ---------------------------------------------------------------------------
# 머리글 해석 (여러 줄 · 합쳐진 칸)
# ---------------------------------------------------------------------------
_MONTH_RE = re.compile(r"^(\d{4}-\d{2}|\d{1,2}월)$")
_YEAR_RE = re.compile(r"^(\d{4})\s*년?$")


def _header_grid(raw: pd.DataFrame, spec: TableSpec) -> list:
    """값 열마다 머리글 글자 목록(위 줄 → 아래 줄). 합쳐진 칸은 왼쪽 칸의 글자로 채움. 머리글이 없으면 빈 목록"""
    if spec.header_row < 0:
        return [[] for _ in spec.value_cols]
    start = spec.header_start if 0 <= spec.header_start <= spec.header_row else spec.header_row
    rows = []
    for r in range(start, spec.header_row + 1):
        cells = [period_label(raw.iat[r, j], "") for j in spec.value_cols]
        filled = sum(1 for c in cells if c)
        if spec.ffill_header and 0 < filled < 0.7 * len(cells):    # 일부 칸만 채워진 줄 = 합쳐진 칸으로 판단
            carry = ""
            for k, c in enumerate(cells):
                carry = c or carry
                cells[k] = carry
        rows.append(cells)
    return [[rows[ri][k] for ri in range(len(rows))] for k in range(len(spec.value_cols))]


def _row_types(cols: list) -> list:
    """머리글 줄마다 역할: year(연도) / month(월) / other(구분) / period(월 줄이 없을 때 마지막 줄) / blank"""
    n = len(cols[0]) if cols else 0
    types = []
    for ri in range(n):
        labs = [c[ri] for c in cols if c[ri]]
        if not labs:
            types.append("blank")
            continue
        month = sum(1 for x in labs if _MONTH_RE.match(x)) / len(labs)
        year = sum(1 for x in labs if _YEAR_RE.match(x)) / len(labs)
        kind = "month" if month >= 0.7 else ("year" if year >= 0.7 else "other")
        if kind == "other" and len(set(labs)) == 1 and len(labs) >= 2:
            kind = "ignore"                                   # 모든 열에 같은 글자(표 제목·단위 등)는 열 구분에 쓰지 않음
        types.append(kind)
    if "month" not in types:                                        # 월 줄이 없으면 마지막 줄을 기간으로 (예: 병동 이름, 연도)
        last = max((i for i, t in enumerate(types) if t not in ("blank", "ignore")), default=None)
        if last is not None:
            types[last] = "period"
    return types


def _column_header(labels: list, types: list, fallback: str):
    """한 열의 머리글 → (기간 이름, 열 구분 목록, 요약열 여부)"""
    period, year, cats = "", "", []
    for lab, t in zip(labels, types):
        if not lab:
            continue
        if t in ("month", "period"):
            period = lab
        elif t == "year":
            year = lab
        else:
            cats.append(lab)
    ym = _YEAR_RE.match(year)
    mm = re.match(r"^(\d{1,2})월$", period)
    if ym and mm:
        period = f"{ym.group(1)}-{int(mm.group(1)):02d}"
    elif year and period and not _MONTH_RE.match(period):
        period = f"{year} {period}"
    elif year and not period:
        period = year
    is_sum = any(SUMMARY_WORDS.search(x) for x in labels if x)
    return (period or fallback), cats, is_sum


# ---------------------------------------------------------------------------
# 읽기: 가로 표 → 긴 표
# ---------------------------------------------------------------------------
@dataclass
class Parsed:
    long: pd.DataFrame                                    # 항목, 하위구분, 기간, 값
    series: list                                          # [(항목, 하위구분), ...] 표에 나온 순서
    items: list                                           # 항목 목록 (표에 나온 순서)
    periods: list                                         # 기간 목록 (정렬됨)
    pct_series: set = field(default_factory=set)          # '%' 로 적혀 있던(또는 0~1 비율을 %로 바꾼) (항목, 하위구분)
    warnings: list = field(default_factory=list)
    excluded_periods: list = field(default_factory=list)  # 제외한 합계/평균 열 이름
    columns: list = field(default_factory=list)           # 머리글 해석 결과 [(열 문자, 기간, 열 구분, 제외 여부)]
    duplicates: int = 0                                   # 같은 항목·구분·기간이 겹쳐서 번호(#2 …)를 붙인 값의 개수
    dropped: int = 0                                      # 항목 이름이 없어서 제외한 줄의 수
    dup_rows: list = field(default_factory=list)          # 겹침이 생긴 엑셀 줄 번호(1부터)
    spec: TableSpec = field(default_factory=TableSpec)


def parse(raw: pd.DataFrame, spec: TableSpec) -> Parsed:
    raw = raw.reset_index(drop=True)
    warns = []
    empty = Parsed(long=pd.DataFrame(columns=[ITEM, SUB, PERIOD, VALUE]), series=[], items=[], periods=[], spec=spec)
    if raw.empty or not spec.value_cols or not spec.label_cols:
        empty.warnings = ["항목 이름 열이나 값 열이 정해지지 않았습니다. '표 읽기 설정'에서 열을 골라 주세요."]
        return empty

    # 머리글 → 값 열마다 (기간, 열 구분)
    grid = _header_grid(raw, spec)
    types = _row_types(grid)
    labels, cats, cols, col_info, excluded, seen = [], [], [], [], [], {}
    for j, hl in zip(spec.value_cols, grid):
        period, cat, is_sum = _column_header(hl, types, f"열{col_letter(j)}")
        cat_s = " / ".join(cat)
        if spec.drop_summary_cols and is_sum:
            excluded.append(" / ".join([x for x in hl if x]) or period)
            col_info.append((col_letter(j), period, cat_s, True))
            continue
        key = (cat_s, period)
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            period = f"{period} ({seen[key]})"
        labels.append(period)
        cats.append(cat_s)
        cols.append(j)
        col_info.append((col_letter(j), period, cat_s, False))

    start = spec.header_row + 1 if spec.header_row >= 0 else 0
    body = raw.iloc[start:].reset_index(drop=True)
    vals = body.to_numpy(dtype=object)
    n = len(body)
    num = np.full((n, len(cols)), np.nan)
    pct = np.zeros((n, len(cols)), dtype=bool)
    for i in range(n):
        for k, j in enumerate(cols):
            num[i, k], pct[i, k] = to_num(vals[i, j])
    has_val = ~np.isnan(num)
    L = [[clean_label(vals[i, c], spec.clean_labels) for i in range(n)] for c in spec.label_cols]
    nL = len(L)
    order = list(range(nL))[::-1] if spec.reverse_labels else list(range(nL))     # order[0] = 항목 열
    bset = set(spec.block_cols)
    blk_idx = [k for k, c in enumerate(spec.label_cols) if c in bset]              # 블록(구분) 이름 열
    item_idx = [k for k, c in enumerate(spec.label_cols) if c not in bset]         # 항목 이름 열 (여럿이면 ' / ' 로 합쳐 하나의 항목 이름)
    use_blocks = bool(blk_idx) and bool(item_idx)

    value_rows = [i for i in range(n) if has_val[i].any()]
    merged_like = [any(L[k][i] == "" for i in value_rows) for k in range(nL)]       # 빈 칸이 있는 열 = 합쳐진 칸처럼 생긴 열
    items, subs, keep = [], [], []
    last, section, dropped_no_item, n_sections, dropped_idx = [""] * nL, "", 0, 0, []
    for i in range(n):
        row_has = bool(has_val[i].any())
        if spec.reset_on_blank and not row_has and all(L[k][i] == "" for k in range(nL)):
            last = [""] * nL                                # 완전히 빈 줄: '위와 같음' 채우기를 끊는다 (끄면 빈 줄을 건너 계속 채움)
        filled = [""] * nL
        for k in range(nL):                                 # 왼쪽(바깥) 칸부터: 값이 있으면 기억, 비면 (켜져 있을 때) 위 칸 값으로 채움
            v = L[k][i]
            if v:
                if v != last[k] and merged_like[k]:
                    for kk in range(k + 1, nL):
                        last[kk] = ""                       # 합쳐진 칸처럼 생긴 바깥 열의 값이 '바뀔 때' 안쪽 칸 채우기도 새로 시작
                last[k] = v
            filled[k] = v or (last[k] if (spec.ffill if k == 0 else spec.ffill_sub) else "")
        if not row_has:
            if L[0][i] and spec.use_sections:
                section = L[0][i]                           # 값 없는 제목 줄 = 블록 이름
                n_sections += 1
            continue
        if use_blocks:
            item = " / ".join(filled[k] for k in item_idx if filled[k])
            parts = [filled[k] for k in blk_idx if filled[k]]
        else:
            item = filled[order[0]]
            parts = [filled[k] for k in order[1:] if filled[k]]
        if not item:
            dropped_no_item += 1
            dropped_idx.append(i)
            continue
        if spec.use_sections and section and section != item:
            parts = [section] + parts
        keep.append(i)
        items.append(item)
        subs.append(" / ".join(parts))
    if dropped_no_item:
        rows = [start + i + 1 for i in dropped_idx]                                  # 엑셀 줄 번호(1부터)
        sample = dropped_idx[:200]
        text_cols = [col_letter(j) for j in range(raw.shape[1]) if j not in set(cols)
                     and any(clean_label(vals[i, j], False) != "" and np.isnan(to_num(vals[i, j])[0]) for i in sample)]
        warns.append(f"항목 이름이 없는 줄 {dropped_no_item}개는 제외했습니다 (엑셀 줄 번호 예: {', '.join(map(str, rows[:6]))}). "
                     + (f"이 줄들에서 글자가 있는 열: 열 {', '.join(text_cols[:6])}. 그 열에 항목 이름이 있다면 '항목 이름이 있는 열'에 추가하세요. "
                        if text_cols else "")
                     + "(합쳐진 칸 채우기가 꺼져 있거나, 항목 이름 열이 맞지 않을 수 있어요)")
    if excluded:
        warns.append(f"합계/평균 열 {len(excluded)}개는 기간에서 제외했습니다: {', '.join(dict.fromkeys(excluded))}")
    if not keep:
        empty.warnings = warns + ["숫자가 있는 줄을 찾지 못했습니다. 값 열/항목 열/머리글 줄을 확인해 주세요."]
        empty.columns = col_info
        return empty

    keep_a = np.array(keep)
    block = num[keep_a]
    r_idx, c_idx = np.nonzero(~np.isnan(block))
    sub_arr = np.array(subs, dtype=object)[r_idx]
    cat_arr = np.array(cats, dtype=object)[c_idx]
    sub_final = np.where(cat_arr == "", sub_arr, np.where(sub_arr == "", cat_arr, sub_arr + " / " + cat_arr))
    long = pd.DataFrame({
        ITEM: np.array(items, dtype=object)[r_idx],
        SUB: sub_final,
        PERIOD: np.array(labels, dtype=object)[c_idx],
        VALUE: block[r_idx, c_idx],
    })
    long["_pct"] = pct[keep_a][r_idx, c_idx]
    occ = long.groupby([ITEM, SUB, PERIOD]).cumcount()
    dup = int((occ > 0).sum())
    dup_rows = sorted(set((keep_a[r_idx[(occ > 0).to_numpy()]] + start + 1).tolist())) if dup else []
    if dup:
        warns.append(f"같은 항목·구분·기간이 여러 번 나오는 값 {dup}개가 있어 구분 뒤에 번호(#2 …)를 붙였습니다 "
                     f"(엑셀 줄 번호 예: {', '.join(map(str, dup_rows[:6]))}). "
                     "같은 항목이 블록마다 반복되는 표라면, 블록 이름이 어느 열/줄에 있는지 위 줄들 근처에서 찾아 '표 읽기 설정'에서 지정하세요. "
                     "(항목 이름 열에 열 추가 / 블록 위 제목 줄 사용 / 항목 열 순서 바꾸기)")
        long[SUB] = np.where(occ > 0, long[SUB] + " #" + (occ + 1).astype(str), long[SUB])

    if spec.ratio_to_pct:                                    # 이름에 '율'이 있고 값이 모두 0~1.5 사이면 비율로 보고 %로 바꿈
        g = long.groupby([ITEM, SUB], sort=False)[VALUE]
        lo, hi = g.min(), g.max()
        keys = [k for k in lo.index if "율" in k[0] and lo[k] >= -1e-9 and hi[k] <= 1.5 and hi[k] > 0]
        if keys:
            mask = pd.MultiIndex.from_frame(long[[ITEM, SUB]]).isin(keys)
            long.loc[mask, VALUE] = long.loc[mask, VALUE] * 100
            long.loc[mask, "_pct"] = True
            warns.append(f"이름에 '율'이 들어 있고 값이 0~1 사이인 {len(set(k[0] for k in keys))}개 항목은 비율로 보고 %로 바꿔 표시했습니다. "
                         "(원본이 이미 %라면 '표 읽기 설정'에서 끄세요)")

    gz = long.groupby([ITEM, SUB], sort=False)[VALUE]
    n_zero = int(((gz.max() == 0) & (gz.min() == 0)).sum())
    if n_zero:
        warns.append(f"값이 모두 0인 줄이 {n_zero}개 있습니다. 엑셀에서도 실제로 0인지(수식 결과가 비어 있거나 '-' 표시는 아닌지) 확인해 보세요.")

    series = list(dict.fromkeys(zip(long[ITEM], long[SUB])))
    pct_series = {k for k, gg in long.groupby([ITEM, SUB], sort=False)["_pct"] if gg.mean() >= 0.5}
    used = list(dict.fromkeys(p for p in labels if p in set(long[PERIOD])))
    return Parsed(long=long.drop(columns="_pct").reset_index(drop=True), series=series,
                  items=list(dict.fromkeys(long[ITEM])), periods=order_periods(used), pct_series=pct_series,
                  warnings=warns, excluded_periods=excluded, columns=col_info, duplicates=dup, dup_rows=dup_rows, dropped=dropped_no_item, spec=spec)


def _prefers_reverse(p: "Parsed") -> bool:
    """왼쪽 열이 '블록 이름'이고 오른쪽 열이 '항목'인 모양인지: 세부 구분 이름이 여러 블록에 반복되고, 종류가 항목(블록)보다 훨씬 많음"""
    if len(p.items) < 2 or any(c[2] for c in p.columns if not c[3]):          # 머리글에 열 구분이 있으면 판단하지 않음
        return False
    subs = {sb for _, sb in p.series}
    if "" in subs or len(subs) < 2 or len(p.series) / len(subs) < 2:             # 세부 이름이 여러 블록에 반복되어야 함
        return False
    total = {"합계", "전체", "계", "총계", "소계", "total", "Total", "TOTAL"}
    outer_total = any(it in total for it in p.items)
    inner_total = any(sb in total for sb in subs)
    if outer_total != inner_total:                                                 # '합계' 행이 들어 있는 쪽이 구분(블록) 단계
        return outer_total
    return len(subs) >= 2 * len(p.items)                                           # 단서가 없으면 종류가 '2배 이상' 많은 쪽이 항목 (애매하면 뒤집지 않음)


def _extra_text_cols(raw: pd.DataFrame, spec: TableSpec) -> list:
    """항목 이름 열도 값 열도 아닌데 글자가 있는 열 (겹침을 구분하는 블록 이름이 들어 있을 수 있는 열), 글자가 많은 순서로 최대 6개"""
    start = spec.header_row + 1 if spec.header_row >= 0 else 0
    body = raw.iloc[start:]
    used = set(spec.label_cols) | set(spec.value_cols)
    found = []
    for j in range(raw.shape[1]):
        if j in used:
            continue
        n_text = sum(1 for v in body.iloc[:, j] if clean_label(v, False) != "" and np.isnan(to_num(v)[0]))
        if n_text >= 3:
            found.append((n_text, j))
    found.sort(key=lambda x: (-x[0], x[1]))
    return [j for _, j in found[:6]]


def _add_label_cols(raw: pd.DataFrame, spec: TableSpec, base: "Parsed", budget_sec: float = 6.0):
    """겹침을 없애는 글자 열(1개 → 2개 조합)을 항목 이름 열에 추가해 본다. 합쳐진 칸 채우기는 끈 것부터, 그다음 켠 것을 시도.
    값을 하나도 잃지 않고 겹침이 0이 되는 첫 조합을 채택. 못 찾으면 None."""
    from itertools import combinations
    import time
    t0 = time.monotonic()
    cands = _extra_text_cols(raw, spec)
    for r in (1, 2):
        for combo in combinations(cands[:5], r):
            for fill_sub in (False, True):
                if time.monotonic() - t0 > budget_sec:
                    return None
                cols = sorted(set(spec.label_cols) | set(combo))
                cand = replace(spec, label_cols=cols, block_cols=list(combo), ffill_sub=fill_sub or spec.ffill_sub)
                q = parse(raw, cand)
                if not q.long.empty and q.duplicates == 0 and len(q.long) == len(base.long):
                    added = ", ".join(col_letter(c) for c in combo)
                    return replace(cand, auto_note=f"같은 항목이 겹쳐서, 겹침을 없애는 열 {added} 을(를) 블록(구분) 이름 열로 추가했습니다."
                                                    f"{' (합쳐진 칸 채우기 포함)' if fill_sub else ''} 맞지 않으면 '항목 이름이 있는 열'에서 빼세요.")
    return None


def _note(spec: TableSpec, text: str) -> TableSpec:
    return replace(spec, auto_note=(spec.auto_note + " " if spec.auto_note else "") + text)


def _orient(raw: pd.DataFrame, spec: TableSpec, p: "Parsed") -> TableSpec:
    """겹침 없이 읽힌 결과에서, 왼쪽 열이 '블록 이름'이고 나머지 열이 '항목'인 모양이면 방향을 바로잡는다 (값을 잃지 않을 때만)"""
    if len(spec.label_cols) >= 2 and not spec.block_cols and not spec.reverse_labels and _prefers_reverse(p):
        cand = replace(spec, block_cols=[spec.label_cols[0]])
        q = parse(raw, cand)
        if not q.long.empty and q.duplicates == 0 and len(q.long) == len(p.long):
            return _note(cand, "왼쪽 열을 블록(구분)으로, 나머지 열을 항목 이름으로 읽었습니다. (반대라면 '그중 블록(구분) 이름 열'을 비우세요)")
    return spec


def suggest(raw: pd.DataFrame) -> TableSpec:
    """자동 탐지 + 문제가 있으면 고쳐 읽는 방식을 찾는다. 원칙: 값은 하나도 잃지 않고, 문제(버린 줄/겹침)가 **완전히 없어지는** 경우에만 채택한다.
    (조금 나아지기만 해도 채택하면 엉뚱한 해석을 고르게 됨) 못 찾으면 처음 탐지한 해석을 그대로 두고, 경고에 줄 번호를 안내한다."""
    spec = detect(raw)
    p = parse(raw, spec)
    if p.long.empty:
        return spec

    # 1) 항목 이름이 없어서 버린 줄 → 빈 줄에서도 '위와 같음' 채우기를 이어가면 살아나는지
    if p.dropped:
        cand = replace(spec, reset_on_blank=False)
        q = parse(raw, cand)
        if not q.long.empty and q.dropped == 0 and len(q.long) > len(p.long):
            spec, p = _note(cand, "빈 줄에서 '위와 같음' 채우기가 끊겨 항목 이름이 없어지던 줄들이 있어, 빈 줄을 건너서도 채우도록 했습니다."), q

    # 2) 겹치지 않으면 방향만 바로잡음
    if p.duplicates == 0:
        return _orient(raw, spec, p)

    # 3) 겹침 → 겹침이 0이 되는 읽기 방식만 채택 (간단한 것부터). 채택한 뒤에도 방향을 바로잡는다
    flag_sets = [{"ffill_sub": True}, {"use_sections": True}, {"ffill_sub": True, "use_sections": True}]
    if len(spec.label_cols) >= 2:
        first = spec.label_cols[0]
        flag_sets += [{"block_cols": [first]}, {"block_cols": [first], "ffill_sub": True}, {"block_cols": [first], "use_sections": True},
                      {"block_cols": [first], "ffill_sub": True, "use_sections": True}]
    labels = {"ffill_sub": "세부 구분 열의 빈 칸 채우기", "use_sections": "블록 위 제목 줄 사용", "block_cols": "맨 왼쪽 열을 블록(구분)으로"}
    for flags in flag_sets:
        cand = replace(spec, **flags)
        q = parse(raw, cand)
        if not q.long.empty and q.duplicates == 0 and q.dropped <= p.dropped and len(q.long) == len(p.long):
            return _orient(raw, _note(cand, "같은 항목이 겹쳐서 다음을 켰습니다: " + ", ".join(labels[k] for k in flags) + "."), q)
    found = _add_label_cols(raw, spec, p)                    # 블록 이름이 항목 이름 열 밖(예: 4번째 글자 열)에 있는 경우
    return found if found is not None else spec


def read(raw: pd.DataFrame, **overrides) -> Parsed:
    """자동 탐지(suggest) + 읽기 (overrides 로 일부 설정을 덮어쓸 수 있음)"""
    spec = suggest(raw) if not overrides else replace(suggest(raw), **overrides)
    return parse(raw, spec)
