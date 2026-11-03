"""통계 계산 로직 (UI와 분리)"""
from dataclasses import dataclass
import pandas as pd
from config.settings import KPIS, CHANGE_MIN_BASE, CHANGE_TOP_N
from core.utils import pct


@dataclass
class Context:
    df: pd.DataFrame
    months: list
    base: pd.Timestamp
    period: list
    prev: pd.Timestamp | None
    last12: list


def make_context(df, months, base, span) -> Context:
    i = months.index(base)
    return Context(df, months, base, months[max(0, i - span + 1): i + 1],
                   months[i - 1] if i > 0 else None, months[max(0, i - 11): i + 1])


def value(df, top, detail, m):
    if m is None:
        return None
    q = df[(df["지표"].str.startswith(top)) & (df["세부"] == detail)]
    return None if q.empty else q.iloc[0][m]


def series(df, label, months):
    q = df[df["라벨"] == label]
    return pd.Series(dtype=float) if q.empty else q.iloc[0][months].astype(float)


def kpi_summary(ctx: Context) -> list[dict]:
    out = []
    for name, top, det, unit, icon in KPIS:
        cur, pv = value(ctx.df, top, det, ctx.base), value(ctx.df, top, det, ctx.prev)
        trend = ctx.df[(ctx.df["지표"].str.startswith(top)) & (ctx.df["세부"] == det)]
        out.append({"지표": name, "단위": unit, "아이콘": icon, "기준월": cur, "전월": pv,
                    "증감률(%)": pct(cur, pv),
                    "추이": [] if trend.empty else trend.iloc[0][ctx.last12].astype(float).tolist()})
    return out


def top_changes(ctx: Context) -> pd.DataFrame:
    if ctx.prev is None:
        return pd.DataFrame()
    c = ctx.df[["라벨", "그룹"]].copy()
    c["전월"], c["당월"] = ctx.df[ctx.prev], ctx.df[ctx.base]
    c["증감률"] = (c["당월"] - c["전월"]) / c["전월"].abs() * 100
    c = c[(c["전월"].abs() >= CHANGE_MIN_BASE) & (c["당월"] != 0) & c["증감률"].notna()]
    return c.reindex(c["증감률"].abs().sort_values(ascending=False).index).head(CHANGE_TOP_N)


def summary_lines(ctx: Context) -> list[str]:
    lines = []
    tot, tp = value(ctx.df, "총진료비", "합계 > 소계", ctx.base), value(ctx.df, "총진료비", "합계 > 소계", ctx.prev)
    if tot and tp:
        lines.append(f"총진료비 {tot:,.0f}원, 전월 대비 {pct(tot, tp):+.1f}%")
    bed = value(ctx.df, "병상가동율", "%", ctx.base)
    if bed is not None and pd.notna(bed):
        avg = ctx.df.loc[ctx.df["지표"] == "병상가동율", ctx.last12].mean(axis=1).iloc[0]
        lines.append(f"병상가동률 {bed*100:.1f}% (최근 12개월 평균 {avg*100:.1f}%)")
    for _, r in top_changes(ctx).iterrows():
        lines.append(f"{'▲' if r['증감률'] > 0 else '▼'} {r['라벨']}: "
                     f"{r['전월']:,.0f} → {r['당월']:,.0f} ({r['증감률']:+.1f}%)")
    return lines


def group_table(ctx: Context, group: str, period=None) -> pd.DataFrame:
    period = period or ctx.period
    t = ctx.df[ctx.df["그룹"] == group][["지표", "세부"] + period].copy()
    t.columns = ["지표", "세부"] + [m.strftime("%Y-%m") for m in period]
    return t


def custom_metric(ctx: Context, a, op, b) -> pd.Series:
    sa, sb = series(ctx.df, a, ctx.period), series(ctx.df, b, ctx.period)
    res = {"÷": sa / sb.replace(0, float("nan")), "+": sa + sb, "−": sa - sb, "×": sa * sb}[op]
    res.index = [m.strftime("%Y-%m") for m in ctx.period]
    return res
