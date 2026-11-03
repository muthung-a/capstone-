"""'Sample data' 시트(지표 × 월) 파서"""
import pandas as pd
from config.settings import MAIN_SHEET, GROUP_MAP
from core.utils import clean


def _group_of(top: str) -> str:
    for g, keys in GROUP_MAP.items():
        if any(top.startswith(k) for k in keys):
            return g
    return "기타"


def load_main(file):
    raw = pd.read_excel(file, sheet_name=MAIN_SHEET, header=None)
    header = raw.iloc[0]
    month_cols = [c for c in raw.columns[5:] if hasattr(header[c], "year")]
    months = [pd.Timestamp(header[c]) for c in month_cols]

    rows, lv = [], [""] * 5
    for i in range(2, len(raw)):
        r = raw.iloc[i]
        cells = [clean(r[j]) for j in range(5)]
        first = next((j for j in range(5) if cells[j]), None)
        if first is not None:            # 병합셀 펼치기: 상위 레벨 바뀌면 하위 초기화
            for k in range(first, 5):
                lv[k] = cells[k]
        vals = pd.to_numeric(r[month_cols], errors="coerce").values
        if first is None and pd.isna(vals).all():
            continue
        top, detail = lv[0], " > ".join(x for x in lv[1:] if x)
        rows.append({"행": i + 1, "그룹": _group_of(top), "지표": top, "세부": detail,
                     "라벨": f"{top} | {detail}" if detail else top,
                     **dict(zip(months, vals))})
    df = pd.DataFrame(rows)

    key = df[(df["지표"] == "총진료비") & (df["세부"] == "합계 > 소계")]
    if len(key):
        valid = [m for m in months if pd.notna(key.iloc[0][m]) and key.iloc[0][m] != 0]
    else:
        valid = [m for m in months if df[m].notna().sum() > len(df) * 0.3]
    return df, valid
