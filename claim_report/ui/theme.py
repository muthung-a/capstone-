# -*- coding: utf-8 -*-
"""화면 디자인(CSS). 색은 config.py 의 THEME 에서 가져옵니다. 모양을 더 바꾸고 싶을 때만 이 파일을 고치세요."""
import streamlit as st

import config

FONT_STACK = ("'Pretendard Variable','Pretendard','Malgun Gothic','Apple SD Gothic Neo',"
              "'Noto Sans KR','NanumGothic',sans-serif")

_WEB_FONT = ('@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/'
             'pretendardvariable-dynamic-subset.min.css");')

_CSS = """
__WEBFONT__
:root { color-scheme: light; }
.stApp { background: __BG__; color: __TEXT__; font-family: __FONT__; }
.stApp p, .stApp label, .stApp li, .stApp input, .stApp button, .stApp textarea { font-family: __FONT__; }
/* 기본 상단 메뉴/배포 버튼/푸터 숨기기.  ※ stToolbar 는 통째로 숨기면 안 됩니다: '사이드바 펼치기' 버튼이 그 안에 있습니다 */
#MainMenu, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"], [data-testid="stToolbarActions"] { display: none !important; }
[data-testid="stHeader"] { background: transparent; }
/* 사이드바를 접었을 때 다시 여는 버튼: 남색 상단 바 위에서도 잘 보이게 흰색으로 */
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] button {
    color: #fff !important; background: rgba(255,255,255,.18) !important; border-radius: 8px !important; }
[data-testid="stExpandSidebarButton"] span, [data-testid="stSidebarCollapsedControl"] span,
[data-testid="stExpandSidebarButton"] svg, [data-testid="stSidebarCollapsedControl"] svg { color: #fff !important; fill: #fff !important; }
[data-testid="stExpandSidebarButton"]:hover, [data-testid="stSidebarCollapsedControl"] button:hover { background: rgba(255,255,255,.3) !important; }
/* 사이드바가 접혀 있어서 펼치기 버튼이 보일 때는, 상단 바의 제목이 버튼에 가리지 않게 오른쪽으로 비킵니다 */
.stApp:has([data-testid="stExpandSidebarButton"]) .gnb, .stApp:has([data-testid="stSidebarCollapsedControl"]) .gnb { padding-left: 4.6rem; }
[data-testid="stMainBlockContainer"], .block-container { padding: 0 2rem 3rem 2rem !important; max-width: 100% !important; }

.gnb { background: __NAVY__; margin: 0 -2rem 1.2rem -2rem; padding: 1rem 2rem; display: flex; align-items: center;
       justify-content: space-between; gap: 1rem; flex-wrap: wrap; }
.gnb-title { color: #fff; font-size: 1.2rem; font-weight: 700; letter-spacing: -0.01em; }
.gnb-sub { color: #A9B8D3; font-size: .85rem; font-weight: 400; margin-left: .9rem; }
.gnb-right { display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }
.chip { display: inline-block; padding: .22rem .7rem; border-radius: 999px; font-size: .76rem; font-weight: 600; }
.chip-demo { background: #FFF1CC; color: #7A5600; }
.chip-data { background: rgba(255,255,255,.13); color: #E6EDF8; }

[data-testid="stSidebar"] { background: #fff; border-right: 1px solid __LINE__; }
.side-title { font-size: .8rem; font-weight: 700; color: __MUTED__; margin: 1.1rem 0 .45rem 0; }
.col-chip { display: inline-block; background: #EEF2F8; color: #33445F; border-radius: 6px; padding: .16rem .5rem;
            margin: .12rem .1rem; font-size: .76rem; }
.col-chip.miss { background: #FDECEC; color: #B83A37; }
[data-testid="stFileUploaderDropzone"] { background: #F7F9FC; border: 1.5px dashed #C5CFDF; border-radius: 8px; }

[class*="st-key-card-"] { background: __CARD__; border: 1px solid __LINE__; border-radius: 10px; padding: 1.1rem 1.25rem 1rem 1.25rem; }
.card-title { font-size: 1.02rem; font-weight: 700; color: __TEXT__; margin: 0; }
.card-sub { font-size: .8rem; color: __MUTED__; margin: .15rem 0 .2rem 0; }

.kpi-caption { font-size: .85rem; color: __MUTED__; margin: .2rem 0 .1rem 0; font-weight: 600; }
.kpi { background: #fff; border: 1px solid __LINE__; border-radius: 10px; padding: 1rem 1.15rem .9rem 1.15rem; height: 100%; }
.kpi.over { border-left: 4px solid __BAD__; }
.kpi-label { font-size: .85rem; color: __MUTED__; font-weight: 600; }
.kpi-value { font-size: 1.9rem; font-weight: 700; margin: .3rem 0 .4rem 0; line-height: 1.15;
             font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
.kpi-value.over { color: __BAD__; }
.kpi-unit { font-size: .95rem; font-weight: 600; color: __MUTED__; margin-left: .22rem; letter-spacing: 0; }
.kpi-delta { display: inline-block; font-size: .78rem; font-weight: 600; padding: .13rem .5rem; border-radius: 6px; }
.kpi-vs { font-size: .78rem; color: __MUTED__; margin-left: .4rem; }
.tone-neutral { background: __BLUE_SOFT__; color: __BLUE_DARK__; }
.tone-bad { background: #FDECEC; color: #B83A37; }
.tone-good { background: #E4F5EC; color: #1E7A50; }
.tone-flat { background: #EEF1F5; color: __MUTED__; }
.kpi-foot { margin-top: .75rem; padding-top: .6rem; border-top: 1px solid __LINE__; font-size: .8rem; color: __MUTED__; }
.kpi-foot b { color: __TEXT__; font-weight: 600; }
.kpi-gap { height: .3rem; }

.alert { background: #FFF6E0; border: 1px solid #F1DDA6; border-left: 4px solid __WARN__; border-radius: 8px;
         padding: .75rem 1rem; font-size: .9rem; color: #5C4300; margin: .2rem 0 .4rem 0; }
.note { background: #EEF4FC; border: 1px solid #D5E3F7; border-radius: 8px; padding: .65rem .9rem; font-size: .86rem; color: #26457A; margin: .3rem 0; }
.warn-line { font-size: .84rem; color: #7A5600; margin: .15rem 0; }

.insights { list-style: none; margin: .5rem 0 0 0; padding: 0; }
.insights li { position: relative; padding: .38rem 0 .38rem 1.1rem; font-size: .92rem; line-height: 1.55; }
.insights li::before { content: ""; position: absolute; left: 0; top: .95rem; width: 6px; height: 6px; border-radius: 50%; background: __BLUE__; }

.empty { background: #fff; border: 1px dashed #C5CFDF; border-radius: 12px; padding: 2.4rem 2rem 2rem 2rem; text-align: center;
         max-width: 660px; margin: 2.2rem auto 1rem auto; }
.empty h3 { font-size: 1.25rem; font-weight: 700; margin: .9rem 0 .45rem 0; }
.empty p { color: __MUTED__; font-size: .92rem; line-height: 1.65; margin: 0 0 1rem 0; }

.sum-row { display: flex; gap: .6rem; flex-wrap: wrap; margin: .5rem 0 .6rem 0; }
.sum-box { background: #F7F9FC; border: 1px solid __LINE__; border-radius: 8px; padding: .55rem .9rem; min-width: 110px; }
.sum-box .n { font-size: 1.35rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.sum-box .l { font-size: .78rem; color: __MUTED__; }
.sum-box.ok .n { color: __OK__; } .sum-box.bad .n { color: __BAD__; } .sum-box.warn .n { color: #B47B00; }

[data-baseweb="tag"] { background: __BLUE_SOFT__ !important; border-radius: 6px !important; }
[data-baseweb="tag"], [data-baseweb="tag"] span { color: __BLUE_DARK__ !important; }
[data-baseweb="select"] > div { border-radius: 8px; }
.stTabs [data-baseweb="tab-list"] { gap: .2rem; border-bottom: 1px solid __LINE__; }
.stTabs [data-baseweb="tab"] { padding: .5rem .95rem; font-weight: 600; color: __MUTED__; }
.stTabs [aria-selected="true"] { color: __BLUE__; }
.stTabs [data-baseweb="tab-highlight"] { background-color: __BLUE__; }
[data-testid="stBaseButton-pills"], [data-testid="stBaseButton-pillsActive"] { border-radius: 999px; font-size: .85rem; padding: .2rem .8rem; }
[data-testid="stBaseButton-pillsActive"] { background: __BLUE_SOFT__ !important; border-color: __BLUE__ !important; color: __BLUE_DARK__ !important; font-weight: 600; }

[data-testid="stButton"], [data-testid="stDownloadButton"] { width: 100%; }
.stButton button, .stDownloadButton button { width: 100%; border-radius: 8px; font-weight: 600; padding: .55rem 1rem;
    border: 1px solid __LINE__; background: #fff; color: __TEXT__; }
.stButton button:hover, .stDownloadButton button:hover { border-color: __BLUE__; color: __BLUE__; }
[data-testid="stBaseButton-primary"] { background: __BLUE__ !important; border-color: __BLUE__ !important; color: #fff !important; }
[data-testid="stBaseButton-primary"]:hover { background: __BLUE_DARK__ !important; color: #fff !important; }
.foot-note { color: __MUTED__; font-size: .78rem; margin-top: 1.2rem; }
"""


def apply():
    css = _CSS.replace("__WEBFONT__", _WEB_FONT if config.USE_WEB_FONT else "")
    for k, v in {**config.THEME, "FONT": FONT_STACK}.items():
        css = css.replace(f"__{k}__", v)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
