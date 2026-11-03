import io
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from config.settings import GROUP_MAP
from services import analytics as A

HEAD = PatternFill("solid", fgColor="4F46E5")


def build_excel(ctx) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        k = pd.DataFrame(A.kpi_summary(ctx))[["지표", "기준월", "전월", "증감률(%)"]]
        k.to_excel(w, sheet_name="요약", index=False, startrow=2)
        ws = w.sheets["요약"]
        ws["A1"] = f"월간 통계 보고서 — 기준월 {ctx.base:%Y-%m}"
        ws["A1"].font = Font(size=14, bold=True)
        r = len(k) + 5
        ws.cell(r, 1, "자동 요약").font = Font(bold=True)
        for i, l in enumerate(A.summary_lines(ctx), 1):
            ws.cell(r + i, 1, l)
        _style(ws, 3, 4, 18)
        for g in GROUP_MAP:
            name = g.replace("·", "_")
            A.group_table(ctx, g).to_excel(w, sheet_name=name, index=False)
            _style(w.sheets[name], 1, 2 + len(ctx.period), 15, num="#,##0.00" if g == "환자현황" else "#,##0")
    return buf.getvalue()


def _style(ws, head_row, ncol, width, num="#,##0"):
    for cell in ws[head_row][:ncol]:
        cell.font, cell.fill = Font(bold=True, color="FFFFFF"), HEAD
        cell.alignment = Alignment(horizontal="center")
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 34
    for j in range(2, ncol + 1):
        if j > 2:
            ws.column_dimensions[get_column_letter(j)].width = width
        for row in ws.iter_rows(min_row=head_row + 1, min_col=j, max_col=j):
            row[0].number_format = num
