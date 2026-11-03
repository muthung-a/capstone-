import re
import pandas as pd


def clean(x) -> str:
    return "" if pd.isna(x) else re.sub(r"\s+", "", str(x))


def pct(a, b):
    if a is None or b is None or pd.isna(a) or pd.isna(b) or b == 0:
        return None
    return (a - b) / abs(b) * 100


def fmt_month(m) -> str:
    return pd.Timestamp(m).strftime("%Y-%m")


def fmt_value(v, unit=""):
    if v is None or pd.isna(v):
        return "-"
    if unit == "%":
        return f"{v*100:.1f}%"
    if unit == "원":
        return f"{v/1e8:,.2f}억" if abs(v) >= 1e8 else f"{v/1e4:,.0f}만"
    return f"{v:,.0f}{unit}"
