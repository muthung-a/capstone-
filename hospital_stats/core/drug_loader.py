"""숫자 이름 시트(6~11 = 월) 약품 처방 데이터"""
import pandas as pd


def load_drugs(file) -> pd.DataFrame:
    xl = pd.ExcelFile(file)
    out = []
    for s in xl.sheet_names:
        if not s.strip().isdigit():
            continue
        d = xl.parse(s, header=None)
        hdr = [str(x).strip() for x in d.iloc[0]]
        if "총금액" not in hdr:
            continue
        d = d.iloc[1:]
        amt = hdr.index("총금액")
        dept = hdr[amt + 1:-1]
        half = len(dept) // 2
        base = pd.DataFrame({
            "월": int(s), "청구코드": d[1].astype(str), "약품명": d[2], "제약회사": d[3],
            "처방횟수": pd.to_numeric(d[8], errors="coerce"),
            "총금액": pd.to_numeric(d[11], errors="coerce"),
        })
        base = base[base["약품명"].notna()]
        for k in range(half):                       # 뒤쪽 블록 = 진료과별 금액
            base[f"금액_{dept[half + k]}_{k}"] = pd.to_numeric(d.loc[base.index, amt + 1 + half + k],
                                                             errors="coerce").fillna(0)
        out.append(base)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def drug_by_dept(drugs: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in drugs.columns if c.startswith("금액_")]
    g = drugs.groupby("월")[cols].sum()
    g.columns = [c.split("_")[1] for c in cols]
    g = g.T.groupby(level=0).sum().T
    return g.drop(columns=[c for c in g.columns if c == "nan" or g[c].sum() == 0])
