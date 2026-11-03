# -*- coding: utf-8 -*-
"""
심사청구 통계보고서 자동화 — 실행 진입점 (이 파일은 '조립'만 합니다. 내용은 아래 파일들에 나눠져 있어요)

  config.py          ★ 화면 문구·컬럼 이름·필터·KPI·배치·색
  stats_config.py    ★ 통계 정의 (새 통계는 여기에 추가)
  core/              읽기(loader) · 통계 계산(stats) · 요약 문장(insights) · 검증(verify)
  reports/           Excel / PDF 보고서 양식
  ui/                화면 부품 (차트, 대시보드, 검증 화면 ...)

실행: 실행.bat 더블클릭  (또는  streamlit run app.py)
"""
import streamlit as st

import config
import hooks
from core.format import esc

st.set_page_config(page_title=config.APP_TITLE, page_icon="📊", layout="wide")

import stats_config                              # noqa: E402
from core import insights as insight_mod         # noqa: E402
from ui import components, data_panel, filters, theme, dashboard, table_dashboard, verify_page  # noqa: E402

theme.apply()
loaded, threshold = data_panel.render_sidebar()


def render_empty():
    components.top_bar()
    chips = "".join(f'<span class="col-chip">{c}</span>' for c in config.COLUMNS)
    st.markdown(
        '<div class="empty">'
        '<svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#2563B8" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4"/><path d="M7 9l5-5 5 5"/>'
        '<path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/></svg>'
        '<h3>데이터 파일을 불러오세요</h3>'
        '<p>왼쪽 사이드바에 엑셀(xlsx) 또는 CSV 파일을 올리면<br>'
        '통계와 요약 문장, 보고서(Excel/PDF)가 자동으로 만들어집니다.<br>'
        '청구 내역(한 줄 = 청구 1건)과 통계표(항목 × 기간) 모두 읽을 수 있고,<br>'
        '컬럼 이름이 달라도 자동으로 연결하며 안 맞으면 직접 고칠 수 있어요.</p>'
        f'<div>{chips}</div></div>', unsafe_allow_html=True)
    hooks.render_empty_actions()            # 프로토타입 모드에서만 보이는 시작 버튼 (실사용 모드에서는 아무것도 안 함)
    if not stats_config.STATS:
        st.markdown('<div class="note">아직 정의된 통계가 없습니다. <b>stats_config.py</b> 에 병원 통계를 정의하면 '
                    '화면·엑셀·PDF 에 자동으로 나타납니다. (예시가 파일 안에 있어요)</div>', unsafe_allow_html=True)


if loaded is None:
    render_empty()
    st.stop()

if getattr(loaded, "kind", "claims") == "table":       # 항목 × 기간 표(통계표 모드)
    table_dashboard.render(loaded)
    st.stop()

df_all = loaded.df
# --- 사용할 수 있는 통계만 (필요한 컬럼이 없으면 건너뜀) ---
avail, skipped = [], []
for s in stats_config.STATS:
    miss = s.missing(df_all.columns, config.COLUMNS)
    (skipped if miss else avail).append((s, miss))
avail = [s for s, _ in avail]

period = ""
if "청구월" in df_all.columns and (df_all["청구월"] != "").any():
    ms = df_all.loc[df_all["청구월"] != "", "청구월"]
    period = f"{ms.min()} ~ {ms.max()}"
components.top_bar(
    components.chip(loaded.name)
    + (components.chip(period) if period else "")
    + components.chip(f"{len(df_all):,}건"))

for level, text in loaded.issues:
    if level == "error":
        st.error(text)
for w in dict.fromkeys(loaded.warnings + [t for lv, t in loaded.issues if lv == "warn"]):      # 같은 경고는 한 번만
    components.warn_line(w)
if df_all.empty:
    st.stop()
if skipped:
    st.markdown('<div class="note">필요한 컬럼이 연결되지 않아 건너뛴 통계: ' +
                ", ".join(f"<b>{esc(s.title)}</b>({esc(', '.join(m))} 없음)" for s, m in skipped) +
                ' — 왼쪽 <b>컬럼 연결</b>에서 연결하면 나타납니다.</div>', unsafe_allow_html=True)
if not stats_config.STATS:
    st.warning("정의된 통계가 없습니다. stats_config.py 에 병원 통계를 정의해 주세요.")
    st.stop()
if not avail:
    st.error("계산할 수 있는 통계가 없습니다. 왼쪽 '컬럼 연결'에서 컬럼을 연결해 주세요.")
    st.stop()

df = filters.render(df_all, loaded.sig)
if df.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다. 조회 조건을 넓혀 보세요.")
    st.stop()

tables, totals = {}, {}
for s in list(avail):
    try:
        tables[s.id] = s.compute(df)
        totals[s.id] = s.total(df)
    except Exception as e:                       # 통계 정의에 오타가 있어도 나머지는 계속 보이게
        st.warning(f"'{s.title}' 통계를 계산하지 못했습니다: {e}")
        avail.remove(s)
avail = [s for s in avail if s.id in tables]
if not avail:
    st.stop()

ctx = dict(df=df, stats=avail, tables=tables, totals=totals, threshold=threshold, period=period,
           insights=insight_mod.generate(tables))

if config.SHOW_VERIFY_TAB:
    tab_dash, tab_verify = st.tabs(["대시보드", "결과 검증"])
else:
    tab_dash, tab_verify = st.container(), None
with tab_dash:
    dashboard.render(ctx)       # 영역별 오류 격리는 dashboard.py 안에서 처리
if tab_verify is not None:
    with tab_verify:
        with components.guard("결과 검증"):
            verify_page.render(avail, tables)

if hooks.foot_note():
    st.markdown(f'<div class="foot-note">{esc(hooks.foot_note())}</div>', unsafe_allow_html=True)
