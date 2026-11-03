# -*- coding: utf-8 -*-
"""
★ 통계 정의 파일 ★  — 새 통계를 추가하려면 여기에 블록 하나를 추가하세요.

추가하면 자동으로 반영되는 곳
  · 화면의 '상세 통계표' 탭
  · 엑셀/PDF 보고서
  · '결과 검증' 화면 (병원 표와 비교)
  · 차트(chart= 를 적은 경우, 그리고 config.py 의 DASHBOARD_LAYOUT 에 넣은 경우)

각 칸의 뜻
  id        : 이 통계의 이름표 (영문/숫자 추천, 중복 금지)
  title     : 화면/엑셀 시트/PDF 에 보일 제목
  group_by  : 무엇별로 묶을지 (config.py 의 COLUMNS 에 있는 컬럼 이름)
  metrics   : {"결과 열 이름": ("원본 컬럼", 집계방식)}
              집계방식 = sum(합계) / count(건수) / mean(평균) / nunique(종류 수) / max / min / median
  formulas  : {"새 열": "수식"}  이미 만든 열끼리 계산. 예) "조정삭감총액 / 청구총액 * 100"
              (열 이름에 괄호 등이 들어 있으면 `백틱`으로 감싸세요)
  percent_of_total : {"비율(%)": "건수"}  전체 합계 대비 %
  where     : 조건. 예) "조정삭감사유 != ''"  (이 조건에 맞는 행만 계산)
  sort_by / descending : 정렬
  order     : 표시 순서를 고정하고 싶을 때 (예: 승인, 조정, 삭감, 반려)

필요한 컬럼이 파일에 없으면 그 통계만 자동으로 빠지고 나머지는 정상 동작합니다.
"""
import hooks
from core.stats import Chart, Stat  # noqa: F401  (아래 예시를 풀어 쓸 때 필요)

STATS = [
    # 여기에 병원 실제 통계를 정의하세요. 아래 '새 통계 추가 예시'를 복사해서 쓰면 됩니다.
    # =======================================================================
    # ▼ 새 통계 추가 예시 (맨 앞의 # 을 지우고 컬럼 이름만 실제에 맞게 바꾸세요)
    #   먼저 config.py 의 COLUMNS 에 '재활통계코드' 컬럼을 한 줄 추가해야 합니다.
    # =======================================================================
    # Stat(
    #     id="rehab_code",
    #     title="재활 통계 코드별",
    #     group_by="재활통계코드",
    #     metrics={"건수": ("청구번호", "count"), "청구총액": ("청구금액", "sum")},
    #     percent_of_total={"비중(%)": "청구총액"},
    #     sort_by="청구총액", descending=True,
    #     chart=Chart(kind="hbar", title="재활 통계 코드별 청구금액", value="청구총액", value_format="won"),
    # ),
]

# 프로토타입 모드일 때만, 가상 데이터로 '가정한' 통계 4개(prototype/sample_stats.py)를 함께 불러옵니다.
# 실제 사용 시에는 PROTOTYPE_MODE=False 이거나 prototype/ 폴더가 없으면 아무것도 추가되지 않습니다.
STATS += hooks.sample_stats()

STATS_BY_ID = {s.id: s for s in STATS}
