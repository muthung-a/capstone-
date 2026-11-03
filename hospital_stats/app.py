"""엔트리 포인트 — 화면 조립만 담당
실행: streamlit run app.py
"""
import io
import streamlit as st

st.set_page_config(page_title="병원 통계 대시보드", page_icon="🏥", layout="wide")

from config.settings import GROUP_MAP
from core.main_loader import load_main
from core.drug_loader import load_drugs
from core.nursing_loader import load_nursing
from services.analytics import make_context
from export.excel import build_excel
from export.pdf import build_pdf
from ui import theme, sidebar, components as C
from ui.pages import overview, group, drugs, nursing, custom

theme.apply()


@st.cache_data(show_spinner="엑셀 분석 중...")
def load_all(b: bytes):
    return load_main(io.BytesIO(b)), load_drugs(io.BytesIO(b)), load_nursing(io.BytesIO(b))


@st.cache_data(show_spinner=False)
def reports(b: bytes, base, span):
    (df, months), _, _ = load_all(b)
    ctx = make_context(df, months, base, span)
    return build_excel(ctx), build_pdf(ctx)


up = sidebar.upload()
if not up:
    C.page_header("병원 통계 대시보드", "엑셀 파일을 업로드하면 통계가 자동으로 집계됩니다.")
    with C.card("시작하기"):
        st.markdown("1. 왼쪽 사이드바에 **Sample data 시트가 포함된 엑셀**을 업로드하세요.\n"
                    "2. 메뉴에서 보고 싶은 통계를 선택하세요.\n3. 사이드바 하단에서 **엑셀/PDF**로 내려받을 수 있습니다.")
    st.stop()

data = up.getvalue()
try:
    (df, months), drug_df, nurse_df = load_all(data)
except Exception as e:
    st.error(f"엑셀을 읽지 못했습니다: {e}")
    st.stop()

page = sidebar.menu()
base, span = sidebar.filters(months)
ctx = make_context(df, months, base, span)
xlsx, pdf = reports(data, base, span)
sidebar.exports(xlsx, pdf, f"{base:%Y-%m}")

title = page.split(" ", 1)[1]
C.page_header(title, f"조회 기간 {ctx.period[0]:%Y-%m} ~ {ctx.base:%Y-%m}", f"기준월 {ctx.base:%Y-%m}")

if title == "개요":
    overview.render(ctx)
elif title in GROUP_MAP:
    group.render(ctx, title)
elif title == "약품 처방":
    drugs.render(drug_df)
elif title == "간호인력":
    nursing.render(nurse_df)
else:
    custom.render(ctx)
