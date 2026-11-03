# -*- coding: utf-8 -*-
"""
결과 검증 — 병원이 손으로 만든 통계표와, 프로그램이 계산한 통계표를 같은 항목끼리 비교합니다.
"""
import pandas as pd

from core import loader


def compare(ours: pd.DataFrame, our_key: str, ref: pd.DataFrame, ref_key: str,
            pairs: list, tolerance: float = 0.01, key_is_month: bool = False):
    """
    pairs: [(프로그램 열, 병원 열), ...]
    반환: (상세 표 DataFrame, 요약 dict)
    """
    def keyed(df, col):
        k = df[col].map(loader.norm_month) if key_is_month else df[col].astype(str).str.strip()
        return k

    o = pd.DataFrame({"__k": keyed(ours, our_key).values})
    r = pd.DataFrame({"__k": keyed(ref, ref_key).values})
    for oc, rc in pairs:
        o[f"o::{oc}"] = pd.to_numeric(ours[oc].values, errors="coerce")
        r[f"r::{rc}"], _ = loader.to_number(pd.Series(ref[rc].values))
    r = r[r["__k"].notna() & (r["__k"] != "") & (r["__k"] != "nan")]
    o = o.drop_duplicates("__k")
    r = r.drop_duplicates("__k")
    m = o.merge(r, on="__k", how="outer", indicator=True)

    rows = []
    for _, row in m.iterrows():
        for oc, rc in pairs:
            ov, rv = row.get(f"o::{oc}"), row.get(f"r::{rc}")
            if row["_merge"] == "left_only":
                status, diff = "병원 표에 없음", None
            elif row["_merge"] == "right_only":
                status, diff = "프로그램 결과에 없음", None
            elif pd.isna(ov) or pd.isna(rv):
                status, diff = "값 없음", None
            else:
                diff = float(ov) - float(rv)
                status = "일치" if abs(diff) <= tolerance else "불일치"
            rows.append({"구분": row["__k"], "항목": oc,
                         "프로그램 값": None if pd.isna(ov) else ov,
                         "병원 값": None if pd.isna(rv) else rv,
                         "차이": diff, "결과": status})
    detail = pd.DataFrame(rows, columns=["구분", "항목", "프로그램 값", "병원 값", "차이", "결과"])
    total = len(detail)
    ok = int((detail["결과"] == "일치").sum()) if total else 0
    summary = {
        "전체": total, "일치": ok,
        "불일치": int((detail["결과"] == "불일치").sum()) if total else 0,
        "한쪽에만 있음": int(detail["결과"].isin(["병원 표에 없음", "프로그램 결과에 없음"]).sum()) if total else 0,
        "일치율(%)": round(ok / total * 100, 1) if total else 0.0,
    }
    return detail, summary
