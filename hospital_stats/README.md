# 병원 통계 대시보드

## 실행
`실행.bat` 더블클릭 (또는 `pip install -r requirements.txt` → `streamlit run app.py`)

## 구조
```
app.py                  엔트리: 화면 조립만
config/settings.py      ★ 지표·KPI·그룹·색상 설정 (대부분의 수정은 여기서)
core/                   엑셀 → DataFrame (데이터 읽기)
  main_loader.py        Sample data 시트
  drug_loader.py        약품 시트(6~11)
  nursing_loader.py     간호등급 시트
  utils.py              포맷/계산 공통 함수
services/analytics.py   통계 계산 (KPI, 자동요약, 변동 TOP, 사용자 지표)
ui/                     화면
  theme.py              CSS / 차트 테마
  components.py         KPI 카드, 카드, 차트, 표
  sidebar.py            업로드·메뉴·조회조건·다운로드
  pages/                overview / group / drugs / nursing / custom
export/                 excel.py, pdf.py
.streamlit/config.toml  기본 테마
```

## 자주 하는 수정
- KPI 카드 추가: `config/settings.py` → `KPIS`에 한 줄 추가
- 새 페이지: `ui/pages/새파일.py`에 `render()` 작성 → `ui/sidebar.py` MENU, `app.py` 분기에 추가
