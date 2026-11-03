# -*- coding: utf-8 -*-
"""통계표 모드 점검용 가상 표 (header=None 으로 읽은 모양). 모두 가짜 이름/숫자입니다."""
import datetime as dt

import numpy as np
import pandas as pd

NAN = np.nan


def _df(rows):
    w = max(len(r) for r in rows)
    return pd.DataFrame([list(r) + [NAN] * (w - len(r)) for r in rows], dtype=object)


MONTHS = [f"2026-{m:02d}" for m in range(1, 7)]


def layout_simple():
    """A) 가장 단순: 첫 줄에 기간, 첫 열에 항목, 맨 끝에 합계 열"""
    rows = [["구분"] + MONTHS + ["합계"]]
    for i in range(5):
        vals = [100 * (i + 1) + j for j in range(6)]
        rows.append([f"항목{i + 1}"] + vals + [sum(vals)])
    exp = dict(items=5, series=5, periods=MONTHS, spot=[("항목2", "", "2026-03", 202.0), ("항목5", "", "2026-06", 505.0)],
               label_cols=[0], header_row=0)
    return _df(rows), exp


def layout_hospital_like():
    """B) 병원 통계표처럼: 위에 제목 줄, 왼쪽 여백 열, 항목 이름은 병합 셀(첫 줄에만 값), 세부 구분 열, 블록 사이 빈 줄,
       글자 사이를 띄어 쓴 이름, 맨 끝 합계 열"""
    names = ["총 진 료 비", "본 인 부 담 금", "가 상 항 목", "병상가동률(가상)", "입원 환자수(가상)", "평 균 진 료 비",
             "의약품(가상)", "인건비 (퇴직금, 복리후생비 제외)", "재원환자 비율", "관리비", "식자재(가상)", "간 병"]
    rows = [[NAN, "가상 병원 월별 통계표 (예시)"], [NAN, "※ 단위: 건, 원, %"], [],
            [NAN, "구분", "세부"] + [f"{m}월" for m in range(1, 7)] + ["합계"]]
    spot = []
    for i, nm in enumerate(names):
        for k, sub in enumerate(["입원", "외래", "합계"]):
            vals = [1000 * (i + 1) + 100 * k + j for j in range(6)]
            rows.append([NAN, nm if k == 0 else NAN, sub] + vals + [sum(vals)])
            if i in (0, 3) and k == 1:
                spot.append((nm.replace(" ", "") if i == 0 else nm, sub, "3월", float(vals[2])))
        rows.append([])                                   # 블록 사이 빈 줄
    exp = dict(items=12, series=36, periods=[f"{m}월" for m in range(1, 7)], spot=spot, label_cols=[1, 2], header_row=3,
               cleaned={"총진료비", "본인부담금", "가상항목", "평균진료비", "간병"})
    return _df(rows), exp


def layout_formats():
    """C) 숫자 표기가 제각각: 쉼표 글자, %, 괄호 음수, △, '-', 엑셀 날짜 머리글"""
    hdr = ["구분"] + [dt.datetime(2026, m, 1) for m in range(1, 5)]
    rows = [hdr,
            ["금액(가상)", "1,234,000", "1,500,000", "(200,000)", "2,000,000"],
            ["비율(가상)", "87.5%", "88%", "-", "90.25%"],
            ["증감(가상)", "△50", "△20", 10, 30],
            ["건수(가상)", 10, 20, 30, 40]]
    exp = dict(items=4, series=4, periods=["2026-01", "2026-02", "2026-03", "2026-04"],
               spot=[("금액(가상)", "", "2026-03", -200000.0), ("금액(가상)", "", "2026-01", 1234000.0),
                     ("비율(가상)", "", "2026-02", 88.0), ("증감(가상)", "", "2026-01", -50.0)],
               missing=[("비율(가상)", "", "2026-03")], pct={("비율(가상)", "")}, label_cols=[0], header_row=0)
    return _df(rows), exp


def layout_transposed():
    """D) 가로세로가 반대: 위쪽 줄에 항목, 왼쪽 열에 월 (화면에서 '가로세로 바꾸기'를 켜면 읽혀야 함)"""
    names = ["항목A", "항목B", "항목C"]
    rows = [["월"] + names]
    for j in range(6):
        rows.append([f"2026-{j + 1:02d}"] + [10 * (i + 1) + j for i in range(3)])
    exp = dict(items=3, series=3, periods=MONTHS, spot=[("항목B", "", "2026-04", 23.0)], label_cols=[0], header_row=0)
    return _df(rows), exp


def _merged(first_blank, spans):
    """합쳐진 머리글 한 줄: 합쳐진 칸은 첫 칸에만 글자가 있고 나머지는 빈 칸(NaN)으로 읽힌다"""
    row = [NAN] * first_blank
    for text, w in spans:
        row += [text] + [NAN] * (w - 1)
    return row


_M6 = [f"{m}월" for m in range(1, 7)]


def _data_rows(n_items, n_cols, label_extra=0):
    return [[f"항목{i + 1}"] + [NAN] * label_extra + [100 * (i + 1) + j for j in range(n_cols)] for i in range(n_items)]


def layout_year_row():
    """E) 머리글 2줄: 윗줄 '2026년'(6칸에 걸쳐 합쳐짐) + 아랫줄 1월~6월"""
    rows = [_merged(1, [("2026년", 6)]), [NAN] + _M6] + _data_rows(4, 6)
    rows[0][0] = "구분"
    exp = dict(items=4, series=4, periods=[f"2026-{m:02d}" for m in range(1, 7)], label_cols=[0], header_row=1, header_start=0,
               spot=[("항목3", "", "2026-04", 303.0)])
    return _df(rows), exp


def layout_category_row():
    """F) 머리글 2줄: 윗줄 '입원'/'외래'(각 6칸 합쳐짐) + 아랫줄 월. 같은 월이 두 번 나옴"""
    rows = [_merged(1, [("입원", 6), ("외래", 6)]), [NAN] + _M6 * 2] + _data_rows(3, 12)
    rows[0][0] = "구분"
    exp = dict(items=3, series=6, periods=_M6, label_cols=[0], header_row=1, header_start=0,
               spot=[("항목2", "외래", "3월", 208.0), ("항목2", "입원", "3月".replace("月", "월"), 202.0)])
    return _df(rows), exp


def layout_month_over_category():
    """G) 머리글 2줄(반대 순서): 윗줄 월(각 2칸 합쳐짐) + 아랫줄 '입원','외래'"""
    rows = [_merged(1, [(m, 2) for m in _M6]), [NAN] + ["입원", "외래"] * 6] + _data_rows(3, 12)
    rows[0][0] = "구분"
    exp = dict(items=3, series=6, periods=_M6, label_cols=[0], header_row=1, header_start=0,
               spot=[("항목1", "외래", "2월", 103.0), ("항목3", "입원", "6월", 310.0)])
    return _df(rows), exp


def layout_three_levels():
    """H) 머리글 3줄: 연도 / 입원·외래 / 월  (왼쪽 여백 열 + 제목 줄 포함)"""
    rows = [[NAN, "가상 통계표 (예시)"], _merged(1, [("2026년", 12)]), _merged(1, [("입원", 6), ("외래", 6)]), [NAN] + _M6 * 2]
    rows += [[NAN] * 0 + [f"항목{i + 1}"] + [100 * (i + 1) + j for j in range(12)] for i in range(3)]
    rows[1][0] = rows[2][0] = rows[3][0] = "구분"
    exp = dict(items=3, series=6, periods=[f"2026-{m:02d}" for m in range(1, 7)], label_cols=[0], header_row=3, header_start=1,
               spot=[("항목2", "외래", "2026-05", 210.0), ("항목1", "입원", "2026-01", 100.0)])
    return _df(rows), exp


def layout_total_group():
    """I) 합계 묶음: 윗줄 '입원','외래','합계'(각 3칸) → '합계' 묶음 열은 기간에서 제외"""
    rows = [_merged(1, [("입원", 3), ("외래", 3), ("합계", 3)]), [NAN] + ["1월", "2월", "3월"] * 3] + _data_rows(2, 9)
    rows[0][0] = "구분"
    exp = dict(items=2, series=4, periods=["1월", "2월", "3월"], label_cols=[0], header_row=1, header_start=0,
               spot=[("항목2", "외래", "2월", 204.0)], absent_sub="합계")
    return _df(rows), exp


def layout_blocks_with_titles():
    """J) 같은 항목이 블록마다 반복되고, 블록 위에 값 없는 제목 줄('[일반]' …)이 있는 표"""
    rows = [["구분"] + MONTHS]
    for b, title in enumerate(["[일반]", "[한방]", "[요양]"]):
        rows.append([title])
        for i, nm in enumerate(["환자수", "입원 환자수"]):
            rows.append([nm] + [1000 * (b + 1) + 100 * i + j for j in range(6)])
        rows.append([])
    exp = dict(items=2, series=6, periods=MONTHS, label_cols=[0], header_row=0, no_dup=True,
               spot=[("환자수", "[한방]", "2026-03", 2002.0), ("입원 환자수", "[요양]", "2026-06", 3105.0)])
    return _df(rows), exp


def layout_group_left():
    """K) 왼쪽 열에 블록 이름(병합), 오른쪽 열에 항목 이름 — '항목 열 순서 바꾸기'를 켜면 항목 = 오른쪽 열"""
    rows = [["구분", "항목"] + MONTHS]
    for b, g in enumerate(["일반", "한방"]):
        for i, nm in enumerate(["환자수", "입원 환자수"]):
            rows.append([g if i == 0 else NAN, nm] + [1000 * (b + 1) + 100 * i + j for j in range(6)])
    exp = dict(items=2, series=4, periods=MONTHS, label_cols=[0, 1], header_row=0, no_dup=True,
               overrides={"reverse_labels": True}, spot=[("환자수", "한방", "2026-02", 2001.0), ("입원 환자수", "일반", "2026-06", 1105.0)])
    return _df(rows), exp


def layout_ratio():
    """L) 0~1 사이 비율 항목(이름에 '율')은 %로 바꿔 보여야 함. 값이 큰 '율' 이름 항목과 일반 항목은 그대로"""
    rows = [["구분"] + MONTHS,
            ["병상가동율"] + [0.90 + 0.01 * j for j in range(6)],
            ["재원환자 비율"] + [0.30 + 0.02 * j for j in range(6)],
            ["환자수"] + [120 + j for j in range(6)],
            ["평균 율동수"] + [5 + j for j in range(6)]]
    exp = dict(items=4, series=4, periods=MONTHS, label_cols=[0], header_row=0,
               pct={("병상가동율", ""), ("재원환자 비율", "")},
               spot=[("병상가동율", "", "2026-02", 91.0), ("환자수", "", "2026-02", 121.0), ("평균 율동수", "", "2026-02", 6.0)])
    return _df(rows), exp


def layout_nested_merge():
    """M) 항목 · 그룹 · 세부 3열이 모두 합쳐진 칸: 그룹 칸은 '입원'이 두 줄에 걸쳐 합쳐져 있고, 다음 항목(항목B)의 빈 그룹 칸은
       이전 항목의 '입원'을 물려받으면 안 됨 ('세부 구분 열도 합쳐진 칸 채우기'를 켠 경우)"""
    rows = [["구분", "그룹", "세부"] + MONTHS,
            ["항목A", "입원", "남"] + [100 + j for j in range(6)],
            [NAN, NAN, "여"] + [200 + j for j in range(6)],
            ["항목B", NAN, "합계"] + [300 + j for j in range(6)]]
    exp = dict(items=2, series=3, periods=MONTHS, label_cols=[0, 1, 2], header_row=0, no_dup=True,
               overrides={"ffill_sub": True}, absent_sub="입원 / 합계",
               spot=[("항목A", "입원 / 여", "2026-03", 202.0), ("항목B", "합계", "2026-03", 302.0)])
    return _df(rows), exp


def layout_group_left_many():
    """N) 왼쪽 열에 블록 이름(A1~A3 병합), 오른쪽 열에 항목 6개가 블록마다 반복. 자동으로 '항목 = 오른쪽 열'로 읽어야 함.
       '환자군 비율' 줄은 값이 전부 0 (경고가 나와야 함)"""
    items = ["환자군 수", "환자군 비율", "본인부담금", "의료용산소", "총진료비", "의료소모품"]
    rows = [["구분", "항목"] + MONTHS]
    for g, grp in enumerate(["A1", "A2", "A3"]):
        for k, nm in enumerate(items):
            vals = [0] * 6 if nm == "환자군 비율" else [1000 * (k + 1) + 100 * g + j for j in range(6)]
            rows.append([grp if k == 0 else NAN, nm] + vals)
    exp = dict(items=6, series=18, periods=MONTHS, label_cols=[0, 1], header_row=0, no_dup=True, warn_zero=3,
               spot=[("본인부담금", "A2", "2026-03", 3102.0), ("환자군 수", "A3", "2026-01", 1200.0)])
    return _df(rows), exp


def layout_hospital_not_reversed():
    """O) 항목(병합) 12개 × 세부 3개(입원/외래/합계): 세부 종류가 적으므로 뒤집으면 안 됨 (자동 판단이 과하게 작동하지 않는지)"""
    raw, exp = layout_hospital_like()
    exp = dict(exp)
    exp["no_reverse"] = True
    return raw, exp


def layout_group_with_total():
    """P) 사용자 파일과 같은 모양: 왼쪽 열 블록 8개(A1~A7 + '합계', 병합) × 오른쪽 열 항목 6개. 블록 수가 항목 수보다 많아도
       '합계'가 들어 있는 열이 블록(구분)이므로 항목 = 오른쪽 열로 읽어야 함"""
    items = ["환자군 수", "환자군 비율", "본인부담금", "의료용산소", "총진료비", "의료소모품"]
    groups = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "합계"]
    rows = [["구분", "항목"] + MONTHS]
    for g, grp in enumerate(groups):
        for k, nm in enumerate(items):
            rows.append([grp if k == 0 else NAN, nm] + [1000 * (k + 1) + 100 * g + j for j in range(6)])
    exp = dict(items=6, series=48, periods=MONTHS, label_cols=[0, 1], header_row=0, no_dup=True,
               spot=[("본인부담금", "합계", "2026-03", 3702.0), ("환자군 수", "A1", "2026-01", 1000.0)])
    return _df(rows), exp


def layout_ambiguous():
    """Q) 단서가 없는 모호한 표(블록 2개 × 항목 2개, '합계' 없음): 임의로 뒤집으면 안 됨 — 사용자가 설정에서 직접 고르게 둔다"""
    raw, exp = layout_group_left()
    exp = dict(exp)
    exp.pop("overrides", None)
    exp.update(no_reverse=True, spot=[("한방", "입원 환자수", "2026-06", 2105.0), ("일반", "환자수", "2026-01", 1000.0)])
    return raw, exp


def layout_block_in_extra_col():
    """S) 글자 열이 4개: 앞의 3열(대분류·분류·항목)은 블록마다 똑같고 4번째 열에만 블록 이름(일반/한방/요양). 항목 열은 3개까지만
       자동으로 잡히므로 겹침이 생김 → 겹침을 없애는 열을 자동으로 찾아 추가해야 함"""
    rows = [["구분", "분류", "항목", "블록"] + MONTHS]
    for b, blk in enumerate(["일반", "한방", "요양"]):
        for k, nm in enumerate(["환자수", "금액"]):
            rows.append(["G", "K", nm, blk] + [1000 * (b + 1) + 100 * k + j for j in range(6)])
    exp = dict(items=2, series=6, periods=MONTHS, label_cols=[0, 1, 2, 3], header_row=0, no_dup=True,
               spot=[("G / K / 금액", "한방", "2026-02", 2101.0), ("G / K / 환자수", "요양", "2026-06", 3005.0)])
    return _df(rows), exp


def layout_block_in_extra_col_merged():
    """T) S 와 같지만 4번째 열(블록 이름)이 합쳐진 칸: 블록의 첫 줄에만 이름이 있고 아래는 빈 칸 → 빈 칸 채우기까지 자동으로 켜야 함"""
    rows = [["구분", "분류", "항목", "블록"] + MONTHS]
    for b, blk in enumerate(["일반", "한방", "요양"]):
        for k, nm in enumerate(["환자수", "금액"]):
            rows.append(["G", "K", nm, blk if k == 0 else NAN] + [1000 * (b + 1) + 100 * k + j for j in range(6)])
    exp = dict(items=2, series=6, periods=MONTHS, label_cols=[0, 1, 2, 3], header_row=0, no_dup=True,
               spot=[("G / K / 금액", "한방", "2026-02", 2101.0), ("G / K / 환자수", "요양", "2026-06", 3005.0)])
    return _df(rows), exp


def layout_unresolvable_dup():
    """U) 같은 항목이 두 번 나오는데 어디에도 구분 단서가 없음 → 겹침이 남고, 겹치는 엑셀 줄 번호를 안내해야 함"""
    rows = [["구분"] + MONTHS,
            ["환자수"] + [100 + j for j in range(6)], ["금액"] + [200 + j for j in range(6)],
            ["환자수"] + [300 + j for j in range(6)], ["금액"] + [400 + j for j in range(6)]]
    exp = dict(items=2, series=4, periods=MONTHS, label_cols=[0], header_row=0, expect_dup=True, dup_rows_hint=[4, 5], no_note=True)
    return _df(rows), exp


def layout_dropped_rows():
    """W) 맨 위 두 줄은 항목 이름이 처음부터 없음(채울 위 값이 없음): 제외되고, 엑셀 줄 번호와 '글자가 있는 열'을 안내해야 함"""
    rows = [["구분", "세부"] + MONTHS,
            [NAN, "a"] + [100 + j for j in range(6)],
            [NAN, "b"] + [200 + j for j in range(6)],
            ["X", "c"] + [300 + j for j in range(6)],
            [NAN, "d"] + [400 + j for j in range(6)]]
    exp = dict(items=1, series=2, periods=MONTHS, label_cols=[0, 1], header_row=0, dropped_rows_hint=[2, 3], dropped_cols_hint="B", no_note=True)
    return _df(rows), exp


def layout_same_as_above():
    """X) 사용자 파일 모양: 구분(A)은 블록 첫 줄에만, 항목(B)은 항목 첫 줄에만, 세부(C)는 줄마다(입원/외래). 아래 칸은 '위와 같음'으로 비어 있고(병합 아님)
       항목 사이에 빈 줄이 있음 → '세부 구분 열도 채우기'와 '빈 줄에서도 채우기 이어가기'를 자동으로 켜야 하고, 값을 잃거나 겹치면 안 됨"""
    rows = [["구분", "항목", "세부"] + MONTHS]
    for g, grp in enumerate(["A1", "A2"]):
        for ii, it in enumerate(["환자군 수", "본인부담금"]):
            for k, sub in enumerate(["입원", "외래"]):
                rows.append([grp if (ii == 0 and k == 0) else NAN, it if k == 0 else NAN, sub] + [1000 * (g + 1) + 100 * ii + 10 * k + j for j in range(6)])
            rows.append([])
    exp = dict(items=4, series=8, periods=MONTHS, label_cols=[0, 1, 2], header_row=0, no_dup=True, no_drop=True,
               spot=[("본인부담금 / 외래", "A2", "2026-03", 2112.0), ("환자군 수 / 입원", "A1", "2026-01", 1000.0)])
    return _df(rows), exp


def layout_partial_titles():
    """Y) 블록 제목 줄이 일부 블록에만 있음: 제목 줄 방식을 켜면 겹침이 '줄기는' 하지만(24 → 12) 0 이 되지는 않음.
       원칙: 겹침이 0 이 되지 않는 변형은 채택하지 않고 처음 해석을 유지 + 줄 번호 안내"""
    rows = [["구분"] + MONTHS]
    for b in range(3):
        if b < 2:
            rows.append(["[일반]" if b == 0 else "[한방]"])
        for i, nm in enumerate(["환자수", "입원 환자수"]):
            rows.append([nm] + [1000 * (b + 1) + 100 * i + j for j in range(6)])
        rows.append([])
    exp = dict(items=2, series=6, periods=MONTHS, label_cols=[0], header_row=0, expect_dup=True, dup_rows_hint=[7, 8, 10, 11], no_note=True)
    return _df(rows), exp


HIER = {"일부만 구분되는 겹침(채택하지 않음)": layout_partial_titles, "위와 같음(병합 아님)+빈 줄 구분": layout_same_as_above, "항목 이름 없는 줄(줄 번호·열 안내)": layout_dropped_rows, "블록 이름이 4번째 글자 열(자동 추가)": layout_block_in_extra_col, "4번째 열이 합쳐진 칸(자동 추가)": layout_block_in_extra_col_merged,
        "단서 없는 겹침(줄 번호 안내)": layout_unresolvable_dup, "모호하면 뒤집지 않음": layout_ambiguous, "블록 8개(합계 포함) × 항목 6개": layout_group_with_total, "그룹 왼쪽 열 + 항목 다수(자동 판단)": layout_group_left_many, "항목 많고 세부 적음(뒤집지 않음)": layout_hospital_not_reversed, "안쪽 합쳐진 칸 채우기": layout_nested_merge, "반복 블록(제목 줄)": layout_blocks_with_titles, "왼쪽 열 블록 이름(순서 바꾸기)": layout_group_left, "0~1 비율 → %": layout_ratio}

MULTI = {"머리글2줄(연도+월)": layout_year_row, "머리글2줄(구분+월)": layout_category_row,
         "머리글2줄(월+구분)": layout_month_over_category, "머리글3줄(연도+구분+월)": layout_three_levels,
         "합계 묶음 제외": layout_total_group}

ALL = {"단순": layout_simple, "병원식(병합·띄어쓰기·합계)": layout_hospital_like, "숫자 표기 제각각": layout_formats}


def hostile_table():
    """항목 이름에 태그/수식/특수문자가 들어 있는 표"""
    rows = [["구분"] + MONTHS]
    bad = ['<img src=x onerror="alert(1)">', "내과 & 외과 <b>굵게</b>", '=HYPERLINK("http://evil.example","x")', "+SUM(1+1)", "A&B <para>"]
    for i, b in enumerate(bad):
        rows.append([b] + [10 * (i + 1) + j for j in range(6)])
    return _df(rows)


def big_table(n_items=3000, n_periods=36):
    rng = np.random.default_rng(3)
    rows = [["구분"] + [f"2024-{(m % 12) + 1:02d}" if m < 12 else f"{2025 + (m - 12) // 12}-{(m % 12) + 1:02d}" for m in range(n_periods)]]
    vals = rng.integers(0, 100000, (n_items, n_periods))
    for i in range(n_items):
        rows.append([f"항목{i:05d}"] + list(vals[i]))
    return _df(rows)
