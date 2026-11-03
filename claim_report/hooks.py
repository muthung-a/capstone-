# -*- coding: utf-8 -*-
"""
프로토타입 전용 기능과 본 프로그램을 잇는 **유일한 연결 지점**입니다.

  · prototype/ 폴더가 있고 config.PROTOTYPE_MODE = True 이면 프로토타입 기능이 켜집니다.
  · 폴더를 지우거나 PROTOTYPE_MODE = False 이면 아래 함수들이 전부 '아무것도 안 함'으로 바뀝니다.
본 프로그램의 다른 파일은 prototype 을 직접 가져오지 않습니다. (점검.bat 이 이 규칙을 확인합니다)
"""
import config

_p = None
if getattr(config, "PROTOTYPE_MODE", False):
    try:
        import prototype as _p          # noqa: F401
    except ImportError:                 # prototype/ 폴더가 없으면 실사용 모드
        _p = None


def enabled() -> bool:
    return _p is not None


def badge_text() -> str:                # 상단 '프로토타입' 배지
    return _p.BADGE_TEXT if _p else ""


def foot_note() -> str:                 # 화면 맨 아래 안내 문구
    return _p.FOOT_NOTE if _p else ""


def verify_hint() -> str:               # 결과 검증 탭의 연습 안내
    return _p.VERIFY_HINT if _p else ""


def sample_stats() -> list:             # 가상 데이터로 '가정한' 통계들
    if not _p:
        return []
    from prototype import sample_stats as m
    return list(m.STATS)


def sample_source_if_active():          # 샘플 보기가 켜져 있으면 (이름, 바이트)
    if not _p:
        return None
    from prototype import screens
    kind = screens.active_kind()
    return _p.sample_source(kind) if kind else None


def render_empty_actions():             # 안내 화면의 '샘플 데이터로 시작' 버튼
    if _p:
        from prototype import screens
        screens.render_empty_actions()


def render_sidebar_actions():           # 사이드바의 '샘플 끄기'
    if _p:
        from prototype import screens
        screens.render_sidebar_actions()


def check_list() -> list:               # 샘플 숫자에 의존하는 점검 항목들 [(이름, 함수)]
    if not _p:
        return []
    from prototype import checks
    return list(checks.CHECKS)
