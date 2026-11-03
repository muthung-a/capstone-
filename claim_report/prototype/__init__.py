# -*- coding: utf-8 -*-
"""
★ 프로토타입 전용 기능 모음 ★

실제로 쓰기 시작할 때는 이 폴더를 통째로 지우거나 config.py 의 PROTOTYPE_MODE = False 로 바꾸면 됩니다.
(본 프로그램은 hooks.py 를 통해서만 이 폴더를 부르고, 폴더가 없어도 정상 동작합니다)

여기에 들어 있는 것
  · 가상 데이터 엑셀 3개 (data/)                        샘플 시작 / 컬럼 연결 연습 / 결과 검증 연습
  · '샘플 데이터로 시작' 버튼, '샘플 끄기' 버튼 (ui.py)
  · 상단 '프로토타입' 배지, 하단 안내 문구 (아래 BADGE_TEXT, FOOT_NOTE)
  · 가상 데이터를 보고 '가정해서' 만든 통계 4개 (sample_stats.py)   → 병원 실제 통계로 교체 대상
  · 샘플 숫자에 의존하는 점검 항목 (checks.py)
"""
import os

DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(DIR, "data")

SAMPLE_PATH = os.path.join(DATA_DIR, "심사청구_더미데이터_2026상반기.xlsx")
SAMPLE_TABLE_PATH = os.path.join(DATA_DIR, "샘플_통계표(항목x월).xlsx")          # 항목 × 기간 모양의 통계표 샘플
PRACTICE_PATH = os.path.join(DATA_DIR, "연습용_컬럼명다른파일.xlsx")
VERIFY_PRACTICE_PATH = os.path.join(DATA_DIR, "검증_연습용_병원결과표.xlsx")

BADGE_TEXT = "프로토타입"        # 상단의 노란 배지
FOOT_NOTE = "가상 데이터로 만든 프로토타입입니다. 실제 병원 양식과 통계 항목이 확정되면 맞춰 수정합니다."
VERIFY_HINT = ("연습해 보려면 prototype/data/검증_연습용_병원결과표.xlsx 를 올려보세요 "
               "(진료과별 통계, 일부러 틀린 값이 들어 있습니다).")


def sample_source(kind="claims"):
    """샘플 파일을 (이름, 바이트)로. kind: "claims"(청구 내역) / "table"(통계표). 파일이 없으면 None"""
    path = SAMPLE_TABLE_PATH if kind == "table" else SAMPLE_PATH
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return os.path.basename(path), f.read()
