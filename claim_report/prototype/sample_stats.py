# -*- coding: utf-8 -*-
"""
프로토타입 전용: 가상 데이터를 보고 '가정해서' 만든 통계 4개.
병원이 실제로 내는 통계(재활 통계 코드별, 산소 통계, 지급일자별 등)를 알게 되면 stats_config.py 에 새로 정의하고,
이 파일은 prototype/ 폴더와 함께 삭제합니다.
"""
import config
from core.stats import Chart, Stat

STATS = [
    # ---- 월별 -------------------------------------------------------------
    Stat(
        id="monthly",
        title="월별",
        group_by="청구월",
        metrics={
            "청구건수": ("청구번호", "count"),
            "청구총액": ("청구금액", "sum"),
            "조정삭감총액": ("조정삭감금액", "sum"),
        },
        formulas={"조정삭감률(%)": "조정삭감총액 / 청구총액 * 100"},
        sort_by="청구월",
        chart=Chart(
            kind="combo",
            title="월별 청구건수와 조정·삭감률",
            subtitle="막대는 청구건수, 선은 조정·삭감률입니다. 점선은 경고 기준입니다.",
            value="청구건수", line="조정삭감률(%)", height=340,
        ),
    ),
    # ---- 심사결과별 ---------------------------------------------------------
    Stat(
        id="result",
        title="심사결과별",
        group_by="심사결과",
        metrics={"건수": ("청구번호", "count")},
        percent_of_total={"비율(%)": "건수"},
        order=config.RESULT_ORDER,
        chart=Chart(
            kind="donut",
            title="심사결과 분포",
            subtitle="승인·조정·삭감·반려 건수 비율",
            value="건수", center_key="승인", center_caption="승인률", height=340,
        ),
    ),
    # ---- 진료과별 ----------------------------------------------------------
    Stat(
        id="dept",
        title="진료과별",
        group_by="진료과",
        metrics={
            "청구건수": ("청구번호", "count"),
            "청구총액": ("청구금액", "sum"),
            "조정삭감총액": ("조정삭감금액", "sum"),
        },
        formulas={"조정삭감률(%)": "조정삭감총액 / 청구총액 * 100"},
        sort_by="청구총액", descending=True,
        chart=Chart(
            kind="hbar",
            title="진료과별 청구금액",
            subtitle="청구금액이 큰 진료과 순서",
            value="청구총액", value_format="won", height=300,
        ),
    ),
    # ---- 조정·삭감 사유별 ---------------------------------------------------
    Stat(
        id="reason",
        title="조정·삭감 사유별",
        group_by="조정삭감사유",
        metrics={"건수": ("청구번호", "count"), "금액": ("조정삭감금액", "sum")},
        where="조정삭감사유 != ''",
        sort_by="건수", descending=True,
        chart=Chart(
            kind="hbar",
            title="조정·삭감 사유별 건수",
            subtitle="사유 코드별 발생 건수",
            value="건수", value_format="count", color="BAD", height=300,
        ),
    )
]
