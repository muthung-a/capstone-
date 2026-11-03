# -*- coding: utf-8 -*-
"""숫자를 사람이 읽기 좋은 글자로 바꾸는 도구 모음 (금액 억/만원, 증감 화살표 등)"""
import html
import re


def fmt_won(n):
    """금액 -> (값, 단위). 1억 이상은 억원, 1만 이상은 만원, 그 외는 원"""
    n = float(n)
    a = abs(n)
    if a >= 1e8:
        return f"{n / 1e8:,.2f}", "억원"
    if a >= 1e4:
        return f"{n / 1e4:,.0f}", "만원"
    return f"{n:,.0f}", "원"


def fmt_won_text(n):
    v, u = fmt_won(n)
    return f"{v}{u}"


def fmt_value(v, kind):
    """kind: count / won / percent / plain"""
    if kind == "won":
        return fmt_won_text(v)
    if kind == "count":
        return f"{float(v):,.0f}건"
    if kind == "percent":
        return f"{float(v):.1f}%"
    return f"{float(v):,.2f}".rstrip("0").rstrip(".")


def esc(x):
    """엑셀 값 등 외부에서 온 글자를 화면 HTML 에 넣기 전에 반드시 거치는 함수 (태그를 글자 그대로 보이게 함)"""
    return html.escape(str(x), quote=True)


def arrow(d):
    return "▲" if d > 0 else ("▼" if d < 0 else "–")


def strip_lead(line):
    """문장 앞의 이모지/기호 제거"""
    return re.sub(r"^[^\w가-힣]+", "", str(line)).strip()
