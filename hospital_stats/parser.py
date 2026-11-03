"""엑셀 파싱 모듈 - Sample data(월간 통계) / 약품(6~11) / 간호등급 시트"""
import re
import pandas as pd

MAIN_SHEET = "Sample data"

# 지표 그룹 (Sample data 의 첫 번째 열 기준)
GROUP_MAP = {
    "환자현황": ["입원 환자수", "퇴원 환자수", "월말 재원환자수", "총재원환자수", "평균재원환자수",
              "병상가동율", "재원환자 비율", "환자군 수", "환자군 비율"],
    "진료비·청구": ["총진료비", "평균진료비", "청구금액", "본인부담금", "인당진료비"],
    "재활·행위": ["재활치료", "재활치료실 직원", "고빈도흉벽진동요법", "방광스캐너", "의료용산소", "한의사별총진료비"],
    "운영·원가": ["식자재", "의약품", "위생소모품", "기저귀폐기물", "의료소모품", "간병", "인건비(퇴직금,", "관리비"],
    "인력현황": ["인력현황(초일기준)"],
}


def _clean(x):
    if pd.isna(x):
        return ""
    s = re.sub(r"\s+", "", str(x))
    return s


def _group_of(top):
    for g, keys in GROUP_MAP.items():
        for k in keys:
            if top.startswith(k.replace(" ", "")):
                return g
    return "기타"


def load_main(file) -> tuple[pd.DataFrame, list]:
    """Sample data 시트 → long 형태가 아닌 wide(지표 x 월) DataFrame 반환
    columns: 그룹, 지표, 세부, 라벨, <월...>
    """
    raw = pd.read_excel(file, sheet_name=MAIN_SHEET, header=None)
    header = raw.iloc[0]
    month_cols = [c for c in raw.columns[5:] if isinstance(header[c], pd.Timestamp) or hasattr(header[c], "year")]
    months = [pd.Timestamp(header[c]) for c in month_cols]

    rows = []
    lv = ["", "", "", "", ""]
    for i in range(2, len(raw)):
        r = raw.iloc[i]
        cells = [_clean(r[j]) for j in range(5)]
        # 상위 레벨이 바뀌면 하위 레벨 초기화
        for j in range(5):
            if cells[j]:
                lv[j] = cells[j]
                for k in range(j + 1, 5):
                    lv[k] = ""
                break
        for j in range(5):
            if cells[j]:
                lv[j] = cells[j]
        vals = pd.to_numeric(r[month_cols], errors="coerce").values
        if pd.isna(vals).all() and not any(cells):
            continue
        top = lv[0]
        detail = " > ".join([x for x in lv[1:] if x])
        rows.append({
            "행": i + 1,
            "그룹": _group_of(top),
            "지표": top,
            "세부": detail,
            "라벨": f"{top} | {detail}" if detail else top,
            **{m: v for m, v in zip(months, vals)},
        })
    df = pd.DataFrame(rows)
    # 데이터가 하나라도 있는 월만 사용
    # 핵심 지표(총진료비 합계 소계)에 값이 있는 월만 '확정 월'로 사용
    key = df[(df["지표"] == "총진료비") & (df["세부"] == "합계 > 소계")]
    if len(key):
        valid = [m for m in months if pd.notna(key.iloc[0][m]) and key.iloc[0][m] != 0]
    else:
        valid = [m for m in months if df[m].notna().sum() > len(df) * 0.3]
    return df, valid


def find(df, top, detail=None):
    """지표 이름(앞부분 일치)과 세부 라벨로 행 찾기"""
    q = df[df["지표"].str.startswith(top)]
    if detail is not None:
        q = q[q["세부"] == detail]
    return q.iloc[0] if len(q) else None


def load_drugs(file) -> pd.DataFrame:
    """숫자 이름의 시트(6~11 = 월) 약품 처방 데이터 통합"""
    xl = pd.ExcelFile(file)
    out = []
    for s in xl.sheet_names:
        if not s.strip().isdigit():
            continue
        d = pd.read_excel(file, sheet_name=s, header=None)
        hdr = [str(x).strip() for x in d.iloc[0]]
        d = d.iloc[1:].copy()
        d.columns = range(d.shape[1])
        # 총금액 이후 진료과 열: 앞쪽 블록=수량, 뒤쪽 블록=금액
        try:
            amt_idx = hdr.index("총금액")
        except ValueError:
            continue
        dept_cols = hdr[amt_idx + 1:-1]
        half = len(dept_cols) // 2
        base = pd.DataFrame({
            "월": int(s),
            "청구코드": d[1].astype(str),
            "약품명": d[2],
            "제약회사": d[3],
            "분류번호": d[5],
            "처방횟수": pd.to_numeric(d[8], errors="coerce"),
            "총금액": pd.to_numeric(d[11], errors="coerce"),
        })
        base = base[base["약품명"].notna()]
        for k in range(half):
            name = dept_cols[half + k]
            col = amt_idx + 1 + half + k
            base[f"금액_{name}_{k}"] = pd.to_numeric(d.loc[base.index, col], errors="coerce").fillna(0)
        out.append(base)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def drug_by_dept(drugs: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in drugs.columns if c.startswith("금액_")]
    g = drugs.groupby("월")[cols].sum()
    # 같은 이름(내과2 중복 등)은 합산
    g.columns = [c.split("_")[1] for c in cols]
    g = g.T.groupby(level=0).sum().T
    g = g.drop(columns=[c for c in g.columns if c == "nan" or g[c].sum() == 0])
    return g


def load_nursing(file) -> pd.DataFrame:
    """'간호등급 (YYYYQ)' 시트 → 분기/월별 재직 인원 수"""
    xl = pd.ExcelFile(file)
    rows = []
    for s in xl.sheet_names:
        m = re.match(r"간호등급\s*\((\d{4})(\d)\)", s)
        if not m:
            continue
        d = pd.read_excel(file, sheet_name=s, header=None)
        hdr = [str(x).strip() for x in d.iloc[0]]
        body = d.iloc[1:]
        jcol = None
        for ci in range(min(4, body.shape[1])):
            if body[ci].astype(str).str.contains("간호").mean() > 0.3:
                jcol = ci
                break
        for ci, h in enumerate(hdr):
            if re.match(r"^\d{1,2}/\d{1,2}$", h):
                col = pd.to_numeric(body[ci], errors="coerce")
                mon = int(h.split("/")[0])
                total = int((col == 1).sum())
                rec = {"연도": int(m.group(1)), "분기": int(m.group(2)), "월": mon, "재직인원": total}
                if jcol is not None:
                    for job, cnt in body[col == 1].groupby(body[jcol]).size().items():
                        rec[str(job).strip()] = int(cnt)
                rows.append(rec)
    if not rows:
        return pd.DataFrame()
    r = pd.DataFrame(rows).fillna(0)
    r["기준"] = r["연도"].astype(str) + "-" + r["월"].astype(str).str.zfill(2)
    return r.sort_values(["연도", "월"]).reset_index(drop=True)
