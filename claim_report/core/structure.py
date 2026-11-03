# -*- coding: utf-8 -*-
"""
엑셀 '구조 요약' — 파일에 어떤 시트/컬럼이 있는지만 알려주고, **셀 값은 절대 출력하지 않습니다.**
(병원 데이터를 AI 등 외부에 보여주지 않고도, 프로그램을 맞추는 데 필요한 구조 정보만 공유하기 위한 도구)

안전장치
  · 값(셀 내용)·값의 종류 목록·최소/최대값은 출력하지 않습니다. (값의 '개수'만 출력)
  · 컬럼 이름이 개인정보/값처럼 보이면(주민번호·전화번호·긴 숫자·날짜·40자 초과) '값처럼 보여 숨김'으로 바꿉니다.
  · 파일 이름도 출력하지 않습니다.
"""
import re

import pandas as pd

import config
import stats_config
from core import loader, table_mode

_VALUE_LIKE = [re.compile(r"\d{6}-?\d{7}"), re.compile(r"01[016789]-?\d{3,4}-?\d{4}"),
               re.compile(r"^\d{6,}$"), re.compile(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}")]
HIDDEN = "(값처럼 보여 숨김)"


def safe_name(name) -> str:
    s = str(name).strip()
    if not s or s.lower().startswith("unnamed"):
        return "(이름 없음)"
    if len(s) > 40 or any(p.search(s) for p in _VALUE_LIKE):
        return HIDDEN
    return s


def _kind(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "날짜"
    if pd.api.types.is_numeric_dtype(series):
        return "숫자"
    sample = series.dropna().astype(str).head(2000)
    if len(sample):
        _, bad = loader.to_number(sample.reset_index(drop=True))
        if bad <= len(sample) * 0.05:
            return "숫자(글자로 저장됨)"
    return "글자"


def _table_section(name: str, data: bytes, sheet: str) -> list:
    """항목 × 기간 모양의 통계표로 보이면, 항목 '이름'은 빼고 모양(열 문자, 개수, 기간 형식)만 설명"""
    try:
        raw = loader.read_raw_grid(name, data, sheet)
        spec = table_mode.suggest(raw)
        if len(spec.value_cols) < 3 or not spec.label_cols:
            return []
        p = table_mode.parse(raw, spec)
    except Exception:  # noqa: BLE001
        return []
    if p.long.empty:
        return []
    L = [table_mode.col_letter(c) for c in spec.label_cols]
    V = [table_mode.col_letter(c) for c in spec.value_cols]
    per = p.periods
    if per and all(re.fullmatch(r"\d{4}-\d{2}", x) for x in per):
        kind = "연-월 형식(예: 2026-01)"
    elif per and all(re.fullmatch(r"\d{1,2}월", x) for x in per):
        kind = "'N월' 형식"
    else:
        kind = "글자(월이 아닌 이름일 수 있음)"
    return ["", "  ▶ 이 시트는 '통계표(항목 × 기간)' 모양으로 보입니다. (항목·기간 이름은 적지 않았습니다)",
            f"    - 항목 이름 열: {', '.join(L)}   /   값(기간) 열: {V[0]} ~ {V[-1]} ({len(V)}개)",
            f"    - 머리글 줄: {'없음' if spec.header_row < 0 else (str(spec.header_start + 1) + '~' + str(spec.header_row + 1) + '번째 줄 (' + str(spec.header_row - spec.header_start + 1) + '줄)' if spec.header_start >= 0 and spec.header_start != spec.header_row else str(spec.header_row + 1) + '번째 줄')}"
            f"   /   기간 {len(per)}개, 형식: {kind}",
            f"    - 열 구분(예: 입원/외래처럼 열을 나누는 머리글): {len({c[2] for c in p.columns if c[2]})}종류",
            f"    - 항목 {len(p.items)}개, 세부 구분까지 {len(p.series)}줄, 읽은 값 {len(p.long):,}개",
            f"    - 합계/평균 열 {len(p.excluded_periods)}개, '%' 로 적힌(또는 0~1 비율) 줄 {len(p.pct_series)}개",
            f"    - 같은 항목이 블록마다 반복되는 표인지: {'예' if (spec.use_sections or spec.reverse_labels) else '아니오'}"
            f" (블록 제목 줄 사용 {'예' if spec.use_sections else '아니오'} / 항목 열 순서 바꿈 {'예' if spec.reverse_labels else '아니오'})"
            f", 겹치는 값 {p.duplicates:,}개"]


def summarize(name: str, data: bytes) -> list:
    lines = ["# 엑셀 구조 요약  (셀 값은 포함하지 않았습니다)", ""]
    layout = loader.guess_layout(name, data)
    sheets = list(layout)[:15]
    lines.append(f"시트 {len(layout)}개")
    best = loader.best_sheet(layout)
    for sh in sheets:
        score, hdr = layout[sh]
        try:
            raw = loader.read_table(name, data, sh, hdr)
        except Exception as e:  # noqa: BLE001
            lines += ["", f"## 시트 {sheets.index(sh) + 1}: 읽지 못함 ({type(e).__name__})"]
            continue
        lines += ["", f"## 시트 {sheets.index(sh) + 1}" + ("  ← 컬럼 이름이 가장 많이 맞는 시트" if sh == best and score else ""),
                  f"- 데이터 {len(raw):,}행 × {len(raw.columns)}열",
                  f"- 컬럼 이름이 있는 줄: {hdr + 1}번째 줄 (프로그램 컬럼과 맞은 개수: {score})"]
        if score == 0:
            lines.append("- ⚠ 컬럼 이름 줄을 찾지 못했습니다. 첫 줄이 데이터 값일 수 있어 이름은 숨겼습니다.")
        lines += ["", "  번호 | 이름 | 자료형 | 빈 칸(%) | 서로 다른 값 개수"]
        for i, col in enumerate(raw.columns, 1):
            s = raw[col]
            blank = float((s.isna() | (s.astype(str).str.strip() == "")).mean() * 100) if len(s) else 0.0
            shown = safe_name(col) if score > 0 else "(숨김)"      # 컬럼 이름 줄을 못 찾았으면 이름 대신 숨김
            lines.append(f"  {i} | {shown} | {_kind(s)} | {blank:.0f} | {s.nunique(dropna=True):,}")

        lines += _table_section(name, data, sh)
        mapping = loader.auto_map(list(raw.columns))
        ok = {k: v for k, v in mapping.items() if v is not None}
        lines += ["", "  프로그램 컬럼과의 자동 연결:"]
        for k in config.COLUMNS:
            lines.append(f"  - {k}: " + (f"← {safe_name(ok[k])}" if k in ok else "연결 안 됨"))
        usable = [s.title for s in stats_config.STATS if not s.missing(list(ok), config.COLUMNS)]
        lines.append(f"  → 이 시트로 바로 계산 가능한 통계: {', '.join(usable) if usable else '없음'}")
    lines += ["", "※ 공유하기 전에 위 내용을 직접 읽어 보고, 공유해도 되는지 교수님/병원에 확인하세요."]
    return lines
