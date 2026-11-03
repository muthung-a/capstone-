# -*- coding: utf-8 -*-
"""
구조 복제본 — 병원 엑셀의 '이름'과 '값'은 전부 가짜로 바꾸고, '구조'만 똑같이 남긴 새 엑셀 파일을 만듭니다.
(streamlit 을 가져오지 않는 순수 계산 모듈)

남기는 것 (구조)   시트 수/크기, 병합 셀, 빈 칸 위치, 숫자 칸/글자 칸 위치, 머리글 줄 수, 같은 항목이 반복되는 모양,
                   글자 사이 띄어쓰기('본 인 부 담 금'), 숫자 표기(1,234 / 87.5% / (123) / △50), 0 인 칸, 0~1 비율 모양,
                   기간 이름(2026-07, 7월, 2026년), '합계/평균' 같은 말, 프로그램이 아는 컬럼 이름, 승인/조정/삭감/반려
바꾸는 것 (정보)   항목·블록 이름 → '항목_001' 같은 가짜 이름 (같은 이름은 같은 가짜 이름),
                   숫자 → 자릿수만 같은 무작위 값, 날짜 → 그 달 1일, 긴 글(제목·메모) → '(긴 글)'
버리는 것         시트 이름, 문서 속성(만든 이·회사), 메모, 이름 정의, 머리글/바닥글, 숨은 정보, 그림 — 새 파일에 아예 옮기지 않음

안전장치: 원본에 있던 글자가 복제본에 그대로 남으면(허용 목록 제외) 파일을 만들지 않습니다.
주의: 값 사이의 관계(합계 = 구분의 합, 비율 = 분자/분모)와 추세는 보존하지 않습니다. 구조 문제를 고치는 용도이며,
      숫자가 맞는지 확인하는 일은 원본 파일로 이 PC 에서 '결과 검증' 탭으로 하세요.
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime

import numpy as np
import openpyxl
import pandas as pd
from openpyxl import Workbook

import config
from core import loader, table_mode
from core.table_mode import clean_label

KEEP_WORDS = {"합계", "총계", "소계", "누계", "평균", "전체", "계", "total", "sum", "avg", "average"}
MAX_CELLS = 3_000_000


def _vocab() -> set:
    """프로그램이 아는 말(컬럼 별칭, 심사결과 값): 병원 정보가 아니므로 그대로 둔다"""
    return set(loader._alias_map().keys()) | {loader._norm(x) for x in config.RESULT_ORDER}


# ---------------------------------------------------------------------------
# 숫자 / 숫자처럼 보이는 글자
# ---------------------------------------------------------------------------
def _decimals(a: float) -> int:
    r = repr(float(a))
    return min(len(r.split(".")[1]), 6) if ("." in r and "e" not in r) else 0


def _rand_number(v, rng):
    if v == 0:
        return 0 if isinstance(v, (int, np.integer)) else 0.0
    neg, a = v < 0, abs(float(v))
    is_int = isinstance(v, (int, np.integer)) or a == int(a)
    if a <= 1.5 and not (isinstance(v, (int, np.integer))):              # 0~1 비율 모양은 비율 모양으로
        d = max(_decimals(a), 2)
        x = round(float(rng.uniform(0.05, 0.99 if a <= 1 else 1.5)), d)
    elif is_int:
        digits = len(str(int(a)))
        lo = 10 ** (digits - 1) if digits > 1 else 1
        x = int(rng.integers(lo, 10 ** digits))
        x = float(x) if isinstance(v, (float, np.floating)) else x
    else:
        digits = len(str(int(a)))
        d = _decimals(a)
        lo = 10 ** (digits - 1) if digits > 1 else 1
        x = round(float(rng.uniform(lo, 10 ** digits - 1)), d)
    return -x if neg else x


def _rand_numtext(s: str, rng) -> str:
    """'1,234,000' '87.5%' '(123)' '△50' 의 표기는 그대로 두고 숫자만 무작위로 (0 만 있는 글자는 그대로)"""
    if not re.search(r"[1-9]", s):
        return s
    first = True
    out = []
    for ch in s:
        if ch.isdigit():
            lo = 1 if (first and ch != "0") else 0
            out.append(str(int(rng.integers(lo, 10))))
            first = False
        else:
            out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------------------
# 글자
# ---------------------------------------------------------------------------
class _State:
    def __init__(self, rng):
        self.rng = rng
        self.vocab = _vocab()
        self.labels = {}                    # 정리한 이름 → 번호
        self.original_keys = set()          # 원본에서 가짜 이름으로 바꾼 글자들 (누출 검사용)
        self.kept = 0

    def token(self, key: str, s: str) -> str:
        idx = self.labels.setdefault(key, len(self.labels) + 1)
        self.original_keys.add(key)
        if len(key) > 40:
            base = "(긴 글)"
        elif key.startswith("[") and key.endswith("]"):
            base = f"[구분_{idx:03d}]"
        else:
            base = f"항목_{idx:03d}"
            if key.endswith("비율"):
                base += "비율"
            elif key.endswith("율"):
                base += "율"
        spaced = clean_label(s, True) != clean_label(s, False)         # '본 인 부 담 금' 처럼 띄어 쓴 이름은 띄어 쓴 가짜 이름으로
        return " ".join(base) if (spaced and base != "(긴 글)") else base


def classify_text(s: str, vocab: set) -> str:
    """글자 칸 하나의 종류: blank(빈 글자) / keep(그대로 둠: 기간 이름·합계·프로그램이 아는 말·'-') / numtext(숫자처럼 보임) / label(이름 → 가짜로 바꿈)"""
    t = clean_label(s, False)
    if t == "":
        return "blank"
    if t.lower() in table_mode._BLANK_TOKENS:
        return "keep"
    pl = table_mode.period_label(s, "")
    if re.fullmatch(r"\d{4}-\d{2}", pl) or re.fullmatch(r"\d{1,2}월", pl) or re.fullmatch(r"\d{4}\s*년?", pl):
        return "keep"                                                     # 기간 이름
    x, _ = table_mode.to_num(s)
    if not np.isnan(x):
        return "numtext"
    key = clean_label(s, True)
    if key.lower() in KEEP_WORDS or loader._norm(key) in vocab:
        return "keep"                                                     # 합계/평균/프로그램이 아는 컬럼 이름
    return "label"


def _convert_text(s: str, st: _State):
    kind = classify_text(s, st.vocab)
    if kind == "blank":
        return None
    if kind == "keep":
        st.kept += 1
        return s
    if kind == "numtext":
        return _rand_numtext(s, st.rng)
    return st.token(clean_label(s, True), s)


def _convert(v, st: _State, keep_numbers: bool):
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, float, np.integer, np.floating)):
        if isinstance(v, float) and np.isnan(v):
            return None
        return v if keep_numbers else _rand_number(v, st.rng)
    if isinstance(v, (datetime, date)):
        return datetime(v.year, v.month, 1)
    if isinstance(v, str):
        return _convert_text(v, st)
    return None


def _safe_format(fmt: str) -> str:
    """숫자 서식은 한글이 들어 있지 않을 때만 옮김 (서식 안의 글자에 이름이 숨어 있을 수 있음)"""
    return "General" if (not fmt or re.search(r"[가-힣]", fmt)) else fmt


# ---------------------------------------------------------------------------
# 복제본 만들기
# ---------------------------------------------------------------------------
def _to_workbook_bytes(name: str, data: bytes) -> bytes:
    """CSV 는 엑셀 모양으로 바꿔서 같은 방식으로 처리"""
    if not loader.is_csv(name):
        return data
    df = loader.read_table(name, data, "", None)
    wb = Workbook()
    ws = wb.active
    for r in df.itertuples(index=False):
        ws.append([None if (isinstance(x, float) and np.isnan(x)) else x for x in r])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _top_sheets(raw_by_sheet: dict, k: int = 3) -> list:
    cnt = {}
    for sh, df in raw_by_sheet.items():
        num, _ = table_mode._numeric(df.head(400))
        cnt[sh] = int((~np.isnan(num)).sum())
    return [s for s, c in sorted(cnt.items(), key=lambda x: -x[1]) if c > 0][:k]


def _signature(df: pd.DataFrame) -> tuple:
    """읽기 결과의 '모양'만 비교하기 위한 값 (이름·숫자는 들어 있지 않음)"""
    spec = table_mode.detect(df)
    if len(spec.value_cols) >= 3 and spec.label_cols:
        p = table_mode.read(df)
        s = p.spec
        return ("table", len(p.items), len(p.series), tuple(p.periods), tuple(s.label_cols), tuple(s.value_cols),
                s.header_start, s.header_row, s.use_sections, s.reverse_labels, p.duplicates, len(p.pct_series),
                len(p.excluded_periods), len(p.long))
    lay = loader.auto_map(list(df.iloc[0]) if len(df) else [])
    return ("rows", df.shape, tuple(k for k, v in lay.items() if v is not None))


def make_replica(name: str, data: bytes, seed=None):
    """반환: (복제본 xlsx 바이트 또는 b'', 보고 줄 목록, 성공 여부)"""
    rng = np.random.default_rng(seed)
    try:
        src = openpyxl.load_workbook(io.BytesIO(_to_workbook_bytes(name, data)), data_only=True)
    except Exception as e:  # noqa: BLE001
        return b"", [f"파일을 읽지 못했습니다 ({type(e).__name__}). .xls 는 .xlsx 로 저장한 뒤 다시 시도하세요."], False
    st = _State(rng)
    out = Workbook()
    out.remove(out.active)
    total_cells, merged_n = 0, 0
    for i, ws in enumerate(src.worksheets, 1):
        if ws.max_row * max(ws.max_column, 1) > MAX_CELLS:
            return b"", [f"시트 {i} 가 너무 큽니다 ({ws.max_row:,}행 × {ws.max_column}열)."], False
        nws = out.create_sheet(f"시트{i}")
        for row in ws.iter_rows():
            nums = [float(c.value) for c in row if isinstance(c.value, (int, float)) and not isinstance(c.value, bool)
                    and not (isinstance(c.value, float) and np.isnan(c.value))]
            keep_numbers = len(nums) >= 2 and table_mode._header_like(np.array(nums))      # 연도/월 번호 머리글 줄은 그대로
            for c in row:
                if c.value is None:
                    continue
                nv = _convert(c.value, st, keep_numbers)
                if nv is None:
                    continue
                nc = nws.cell(row=c.row, column=c.column, value=nv)
                fmt = _safe_format(c.number_format)
                if fmt != "General":
                    nc.number_format = fmt
                total_cells += 1
        for rng_ in ws.merged_cells.ranges:
            nws.merge_cells(str(rng_))
            merged_n += 1
    out.properties.creator = ""
    out.properties.lastModifiedBy = ""
    buf = io.BytesIO()
    out.save(buf)
    rep = buf.getvalue()

    # --- 누출 검사: 원본의 이름 글자를 (변환 과정과 무관하게) 직접 모아서, 복제본에 그대로 남아 있으면 만들지 않음 ---
    leaks = _leaks(rep, _original_label_keys(src, st.vocab))
    report = [f"시트 {len(src.worksheets)}개 · 값이 있는 칸 {total_cells:,}개 · 병합 셀 {merged_n}개 · 가짜 이름으로 바꾼 서로 다른 글자 {len(st.labels):,}개",
              f"원본 글자가 복제본에 그대로 남은 것: {leaks}개"]
    if leaks:
        return b"", report + ["→ 안전하지 않아 복제본을 만들지 않았습니다."], False

    # --- 구조 동일성 검사 (이름·숫자 없이 모양만 비교) ---
    try:
        a = loader.read_raw_grids("x.xlsx", _to_workbook_bytes(name, data))          # 원본과 복제본을 같은 방식(병합 범위 채움)으로 읽어 비교
        b = loader.read_raw_grids("x.xlsx", rep)
        keys_a = list(a.keys())
        for j, sh in enumerate(_top_sheets(a), 1):
            same = _signature(a[sh]) == _signature(b[f"시트{keys_a.index(sh) + 1}"])
            kind = _signature(a[sh])[0]
            report.append(f"읽기 결과 비교 {j}: {'통계표(항목 × 기간)' if kind == 'table' else '청구 내역(행 단위)'} 모양 — "
                          + ("원본과 동일 ✓" if same else "원본과 다릅니다 ✗ (복제본이 구조를 완전히 재현하지 못했습니다)"))
    except Exception as e:  # noqa: BLE001
        report.append(f"읽기 결과 비교를 건너뛰었습니다 ({type(e).__name__})")
    return rep, report, True


def _original_label_keys(src_wb, vocab: set) -> set:
    """원본의 모든 글자 칸 중 '이름'(가짜로 바꿔야 하는 글자)을 직접 수집 — 변환 코드가 제대로 동작했는지와 무관하게"""
    keys = set()
    for ws in src_wb.worksheets:
        keys.add(clean_label(ws.title, True))                           # 시트 이름도 이름이다
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and classify_text(c.value, vocab) == "label":
                    keys.add(clean_label(c.value, True))
    keys.discard("")
    return keys


def _xml_strings(blob: bytes) -> list:
    """XML 의 글자 내용과 속성 '값'만 모은다 (태그/속성 '이름'은 제외: showSheetTabs 같은 기본 이름이 오탐을 만들기 때문).
    XML 해석기가 &#...; 문자 참조를 알아서 풀어 준다."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(blob)
    except ET.ParseError:
        return [blob.decode("utf-8", errors="ignore")]
    out = []
    for el in root.iter():
        if el.text and el.text.strip():
            out.append(el.text)
        out.extend(v for v in el.attrib.values() if v)
    return out


def _leaks(replica: bytes, original_keys: set) -> int:
    """복제본에 원본의 이름이 남아 있는 곳의 수: (1) 글자 칸이 원본 이름과 같음 (2) 시트 구조/문서 속성 파일 안에 원본 이름(3글자 이상)이 들어 있음.
    ※ openpyxl 은 한글을 &#...; 문자 참조로 저장하므로, 파일 안을 글자로 검사할 때는 XML 해석기로 풀어서 봐야 한다."""
    import zipfile
    n = 0
    wb = openpyxl.load_workbook(io.BytesIO(replica), data_only=True)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and clean_label(c.value, True) in original_keys:
                    n += 1
    long_keys = [k for k in original_keys if len(k) >= 3]
    with zipfile.ZipFile(io.BytesIO(replica)) as z:
        for part in z.namelist():
            if part.startswith("xl/worksheets/"):
                continue                                                  # 시트 내용은 위에서 칸 단위로 검사함
            for text in _xml_strings(z.read(part)):
                n += sum(1 for k in long_keys if k in text)
    return n
