# -*- coding: utf-8 -*-
"""프로토타입 전용 점검: 샘플 파일의 '정답 숫자'에 의존하는 항목들 (prototype/ 폴더와 함께 삭제됨)"""
import os

import pandas as pd

import config
import prototype
import stats_config
from core import loader, structure, verify


def _load(path):
    name, data = os.path.basename(path), open(path, "rb").read()
    lay = loader.guess_layout(name, data)
    sh = loader.best_sheet(lay)
    raw = loader.read_table(name, data, sh, lay[sh][1])
    df, _ = loader.prepare(raw, loader.auto_map(list(raw.columns)))
    return df, sh, lay[sh][1]


def c_sample():
    df, _, _ = _load(prototype.SAMPLE_PATH)
    if len(df) != 1342 or len(df.columns) != 10:
        raise ValueError(f"샘플이 예상과 다릅니다: {len(df)}행, {len(df.columns)}열")
    return f"샘플 {len(df):,}행, 컬럼 {len(df.columns)}개"


def c_numbers():
    df, _, _ = _load(prototype.SAMPLE_PATH)
    stat = stats_config.STATS_BY_ID.get("monthly")
    if stat is None:
        return "monthly 통계가 없어 건너뜀 (가정 통계를 교체하셨다면 정상)"
    last = stat.compute(df).sort_values("청구월").iloc[-1]
    if (last["청구월"], int(last["청구건수"])) != ("2026-06", 235) or abs(last["조정삭감률(%)"] - 4.39) > 0.01:
        raise ValueError("샘플 2026-06 의 청구건수 235건 / 조정·삭감률 4.39% 와 다릅니다 (통계 정의를 바꾸셨다면 정상일 수 있어요)")
    return "샘플 2026-06: 235건, 조정·삭감률 4.39%"


def c_practice():
    df, sh, hdr = _load(prototype.PRACTICE_PATH)
    if sh != "9월 청구내역" or hdr != 3 or len(df) != 400:
        raise ValueError(f"연습용 파일 읽기 결과가 예상과 다릅니다: 시트 {sh}, {hdr + 1}번째 줄, {len(df)}행")
    return f"시트 '{sh}', {hdr + 1}번째 줄이 컬럼 이름, {len(df)}행"


def c_verify_practice():
    stat = stats_config.STATS_BY_ID.get("dept")
    if stat is None:
        return "dept 통계가 없어 건너뜀"
    df, _, _ = _load(prototype.SAMPLE_PATH)
    ref = pd.read_excel(prototype.VERIFY_PRACTICE_PATH, sheet_name="진료과별")
    _, s = verify.compare(stat.compute(df), "진료과", ref, "진료과",
                          [("청구건수", "청구 건수"), ("청구총액", "청구금액"), ("조정삭감총액", "삭감액")], tolerance=0.01)
    if (s["일치"], s["불일치"], s["한쪽에만 있음"]) != (10, 2, 6):
        raise ValueError(f"검증 연습 결과가 예상(일치10/불일치2/한쪽6)과 다릅니다: {s}")
    return "일부러 틀리게 만든 병원 표에서 불일치 2, 빠진/추가된 항목 6을 정확히 찾음"


def c_structure_sample_values():
    text = "\n".join(structure.summarize(os.path.basename(prototype.SAMPLE_PATH), open(prototype.SAMPLE_PATH, "rb").read()))
    for v in ("재활의학과", "내과", "A02(입원일수 초과)", "CLM-000001", "승인"):
        if v in text:
            raise ValueError(f"샘플 파일의 값 '{v}' 이(가) 구조 요약에 출력되었습니다")
    return "샘플의 실제 값이 구조 요약에 나오지 않음"


def c_table_sample():
    import pandas as pd
    from core import table_mode
    raw = pd.read_excel(prototype.SAMPLE_TABLE_PATH, sheet_name="월별통계", header=None)
    p = table_mode.read(raw)
    want = ["환자수", "병상가동률", "매출총액", "평균재원일수", "직원 수", "재료비", "관리비", "간병"]
    if p.items != want or len(p.periods) != 6 or p.spec.header_row != 3 or p.spec.label_cols != [1, 2]:
        raise ValueError(f"통계표 샘플 읽기 결과가 예상과 다릅니다: 항목 {p.items}, 기간 {p.periods}, 줄 {p.spec.header_row}, 열 {p.spec.label_cols}")
    if ("병상가동률", "입원") not in p.pct_series:
        raise ValueError("% 로 적힌 항목을 인식하지 못했습니다")
    return f"통계표 샘플: 항목 {len(p.items)}개, 기간 {len(p.periods)}개 (병합 셀·띄어쓰기·% 포함)"


def c_replica_claims_sample():
    import io
    import openpyxl
    from core import anonymize
    data = open(prototype.SAMPLE_PATH, "rb").read()
    rep, report, ok = anonymize.make_replica(os.path.basename(prototype.SAMPLE_PATH), data, seed=4)
    if not ok or not rep:
        raise ValueError(f"청구 내역 샘플의 복제본을 만들지 못했습니다: {report}")
    if not any("동일" in l for l in report) or any("다릅니다" in l for l in report):
        raise ValueError(f"청구 내역 복제본의 읽기 결과가 원본과 다릅니다: {report}")
    wb = openpyxl.load_workbook(io.BytesIO(rep))
    texts = {c.value for ws in wb.worksheets for row in ws.iter_rows() for c in row if isinstance(c.value, str)}
    for v in ("재활의학과", "내과", "CLM-000001", "A02(입원일수 초과)"):
        if v in texts:
            raise ValueError(f"복제본에 샘플의 실제 값 '{v}' 이 남아 있습니다")
    return "청구 내역 샘플(1,342행)의 복제본: 값 누출 없음, 컬럼 이름 인식·읽기 결과 동일"


CHECKS = [("샘플 데이터 읽기", c_sample), ("샘플 숫자 확인(235건 등)", c_numbers), ("컬럼 이름이 다른 연습용 파일", c_practice),
          ("결과 검증 연습(틀린 값 찾기)", c_verify_practice), ("구조 요약에 샘플 값이 안 나옴", c_structure_sample_values),
          ("통계표 샘플 읽기(병합 셀·띄어쓰기·%)", c_table_sample),
          ("구조 복제본: 청구 내역 샘플", c_replica_claims_sample)]
