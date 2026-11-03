"""구조 복제본 점검용 가상 파일. 비밀처럼 보이는 이름/숫자/메타정보가 곳곳에 숨겨져 있음 (모두 가짜)"""
import io
import datetime as dt
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.styles import Font

SECRETS = ["홍길동", "김철수", "비밀", "010-1234", "987654321", "123456789", "424242424", "98765"]


def build_hostile_xlsx():
    wb = Workbook(); ws = wb.active; ws.title = "홍길동병원"
    wb.properties.creator = "김철수"; wb.properties.title = "비밀제목"; wb.properties.subject = "비밀주제"; wb.properties.keywords = "비밀키워드"
    wb.defined_names["비밀이름"] = DefinedName("비밀이름", attr_text="'홍길동병원'!$A$1")
    ws.oddHeader.center.text = "비밀머리글"; ws.oddFooter.center.text = "비밀바닥글"
    ws["A1"] = "홍길동병원 2026년 월별 통계표 (비밀 제목입니다. 아주 긴 제목 글자입니다. 아주 긴 제목 글자입니다.)"; ws.merge_cells("A1:J1")
    ws.cell(row=3, column=1, value="구분"); ws.cell(row=3, column=2, value="세부")
    months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
    for j, m in enumerate(months): ws.cell(row=3, column=3 + j, value=m)
    ws.cell(row=3, column=9, value="합계")
    rows = [("[비밀병동]", None, None), ("홍길동 환자수", "입원", "int"), (None, "외래", "int"), ("비 밀 항 목", "입원", "money"),
            ("병상가동율", None, "ratio"), ("비밀 비율", None, "pct"), ("영 값", None, "zero")]
    r = 4
    for name, sub, kind in rows:
        if name: ws.cell(row=r, column=1, value=name)
        if sub: ws.cell(row=r, column=2, value=sub)
        if kind:
            for j in range(6):
                if kind == "int": v = 987654321 + j
                elif kind == "money": v = f"1,{234567 + j * 1111:03d},000"
                elif kind == "ratio": v = 0.8765 + j * 0.001
                elif kind == "pct": v = f"{87.5 + j}%"
                else: v = 0
                c = ws.cell(row=r, column=3 + j, value=v)
                if kind == "ratio": c.number_format = "0.0%"
                if kind == "int": c.number_format = "#,##0"
            ws.cell(row=r, column=9, value=123456789.123 if kind == "int" else "-")
        r += 1
    ws.cell(row=r, column=3, value="(123,456)"); ws.cell(row=r, column=4, value="△98765"); ws.cell(row=r, column=5, value=dt.datetime(2026, 3, 17, 9, 30))
    ws.cell(row=r, column=6, value=555).number_format = '"비밀단위"0'
    ws["A5"].comment = Comment("비밀메모 010-1234-5678", "작성자홍")
    ws.merge_cells("A5:A6")
    ws2 = wb.create_sheet("비밀시트"); ws2["A1"] = "김철수"; ws2["B1"] = 424242424
    ws2.sheet_state = "hidden"
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()

def build_merged_xlsx():
    """병합된 머리글(연도/입원·외래/월)과 병합된 항목 이름, 합계 열, 제목 줄이 있는 실제 엑셀 모양"""
    wb = Workbook()
    ws = wb.active
    ws.title = "통계"
    ws["B1"] = "가상 통계표 (시험용)"
    ws.merge_cells("A1:P1")
    ws["B3"], ws["C3"] = "구분", "세부"
    ws["D3"] = "2026년"
    ws.merge_cells("D3:O3")
    ws["D4"] = "입원"
    ws.merge_cells("D4:I4")
    ws["J4"] = "외래"
    ws.merge_cells("J4:O4")
    for g in range(2):
        for m in range(6):
            ws.cell(row=5, column=4 + g * 6 + m, value=f"{m + 1}월")
    ws["P3"] = "합계"
    ws.merge_cells("P3:P5")
    r = 6
    for i, nm in enumerate(["가 상 지 표 A", "총 매 출", "병상가동율", "직 원 수"]):
        start = r
        for k, sub in enumerate(["전체", "남", "여"]):
            ws.cell(row=r, column=3, value=sub)
            for c in range(12):
                ws.cell(row=r, column=4 + c, value=(0.5 + 0.01 * c) if "율" in nm else 100 * (i + 1) + 10 * k + c)
            ws.cell(row=r, column=16, value=999)
            r += 1
        ws.cell(row=start, column=2, value=nm)
        ws.merge_cells(start_row=start, start_column=2, end_row=r - 1, end_column=2)
        r += 1
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
