"""'간호등급 (YYYYQ)' 시트 → 월별 직종별 재직 인원"""
import re
import pandas as pd


def load_nursing(file) -> pd.DataFrame:
    xl = pd.ExcelFile(file)
    rows = []
    for s in xl.sheet_names:
        m = re.match(r"간호등급\s*\((\d{4})(\d)\)", s)
        if not m:
            continue
        d = xl.parse(s, header=None)
        hdr = [str(x).strip() for x in d.iloc[0]]
        body = d.iloc[1:]
        jcol = next((c for c in range(min(4, body.shape[1]))
                     if body[c].astype(str).str.contains("간호").mean() > 0.3), None)
        for ci, h in enumerate(hdr):
            if not re.match(r"^\d{1,2}/\d{1,2}$", h):
                continue
            on = pd.to_numeric(body[ci], errors="coerce") == 1
            rec = {"연도": int(m.group(1)), "분기": int(m.group(2)),
                   "월": int(h.split("/")[0]), "재직인원": int(on.sum())}
            if jcol is not None:
                rec.update({str(k).strip(): int(v) for k, v in body[on].groupby(body[jcol]).size().items()})
            rows.append(rec)
    if not rows:
        return pd.DataFrame()
    r = pd.DataFrame(rows).fillna(0)
    r["기준"] = r["연도"].astype(str) + "-" + r["월"].astype(str).str.zfill(2)
    return r.sort_values(["연도", "월"]).reset_index(drop=True)
