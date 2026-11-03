# -*- coding: utf-8 -*-
"""
점검 도구 — 설정(config.py / stats_config.py)이나 코드를 고친 뒤 실행하면, 어디가 잘못됐는지 한국어로 알려줍니다.
  실행: 점검.bat 더블클릭  (또는  python tests/run_checks.py)
모든 항목이 [OK] 이면 안심하고 화면을 켜도 됩니다.

공통 점검은 샘플 파일 없이 config.COLUMNS(데이터 계약)로 만든 테스트 데이터로 돌아갑니다.
샘플 숫자에 의존하는 점검은 prototype/checks.py 에 있고, 프로토타입 모드일 때만 '[프로토타입]' 으로 표시되며 실행됩니다.
"""
import ast
import io
import os
import re
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import pandas as pd  # noqa: E402

import config  # noqa: E402
import hooks  # noqa: E402
import stats_config  # noqa: E402
import synthetic  # noqa: E402
from core import insights, loader, verify  # noqa: E402
from reports import excel, pdf  # noqa: E402

results = []
STATE = {}


def run(name, fn):
    try:
        msg = fn()
        results.append((True, name, msg or ""))
    except Exception as e:  # noqa: BLE001
        results.append((False, name, f"{type(e).__name__}: {e}"))
        if os.environ.get("CHECK_VERBOSE"):
            traceback.print_exc()
    ok, _, msg = results[-1]
    print(("[OK]   " if ok else "[실패] ") + name + (f"  —  {msg}" if msg else ""))


# ---------------------------------------------------------------------------
# 1) 설정 점검
# ---------------------------------------------------------------------------
def c_data():
    STATE["df"] = synthetic.make_df(600)
    return f"테스트 데이터 {len(STATE['df'])}행 (COLUMNS {len(config.COLUMNS)}개 컬럼 기준)"


def c_ids():
    ids = [s.id for s in stats_config.STATS]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError(f"통계 id 가 중복됩니다: {sorted(dup)}")
    return f"통계 {len(ids)}개: {', '.join(ids)}" if ids else "아직 정의된 통계가 없습니다 (stats_config.py 에 병원 통계를 정의하세요)"


def c_columns():
    bad = []
    for s in stats_config.STATS:
        for col in s.needs(config.COLUMNS.keys()):
            if col not in config.COLUMNS:
                bad.append(f"[{s.id}] '{col}' 은 config.py 의 COLUMNS 에 없는 컬럼입니다")
    if bad:
        raise ValueError(" / ".join(bad))


def c_compute():
    df, out = STATE["df"], []
    STATE["tables"] = {}
    for s in stats_config.STATS:
        miss = s.missing(df.columns, config.COLUMNS)
        if miss:
            out.append(f"{s.id}: {miss} 컬럼이 없어 건너뜀")
            continue
        STATE["tables"][s.id] = s.compute(df)
        s.total(df)
        out.append(f"{s.id}: {len(STATE['tables'][s.id])}행")
    return ", ".join(out)


def c_charts():
    from ui import charts
    for s in stats_config.STATS:
        if s.chart is None or s.id not in STATE["tables"]:
            continue
        t, c = STATE["tables"][s.id], s.chart
        for col in (c.value, c.line):
            if col and col not in t.columns:
                raise ValueError(f"[{s.id}] 차트가 '{col}' 열을 쓰는데 통계 결과에 그 열이 없습니다. (열 이름 오타 확인)")
        if c.kind not in charts.RENDERERS:
            raise ValueError(f"[{s.id}] 알 수 없는 차트 종류 '{c.kind}'")


def c_layout():
    ids = {s.id for s in stats_config.STATS}
    for row in config.DASHBOARD_LAYOUT:
        for sid, _w in row:
            if sid not in ids:
                raise ValueError(f"DASHBOARD_LAYOUT 의 '{sid}' 는 stats_config.py 에 정의된 통계 id 가 아닙니다 (병원 통계에 맞게 바꾸세요)")
            if not stats_config.STATS_BY_ID[sid].chart:
                raise ValueError(f"DASHBOARD_LAYOUT 의 '{sid}' 통계에는 chart= 가 없어 차트를 그릴 수 없습니다")


def c_kpi():
    t = STATE["tables"].get(config.KPI_STAT)
    if t is None:
        raise ValueError(f"KPI_STAT '{config.KPI_STAT}' 는 정의된 통계가 아닙니다 (병원 통계에 맞게 config.py 의 KPI_STAT 을 바꾸세요)")
    miss = [k["field"] for k in config.KPIS if k["field"] not in t.columns]
    if miss:
        raise ValueError(f"KPIS 의 field {miss} 가 '{config.KPI_STAT}' 통계 결과 열에 없습니다")


def c_insight():
    return f"요약 문장 {len(insights.generate(STATE['tables']))}개"


def c_reports():
    pairs = [(s, STATE["tables"][s.id]) for s in stats_config.STATS if s.id in STATE["tables"]]
    x = excel.build(STATE["df"], pairs, ["테스트"], "테스트")
    p = pdf.build(STATE["df"], pairs, ["테스트"], "테스트")
    if not x or not p:
        raise ValueError("보고서가 비어 있습니다")
    return f"Excel {len(x) // 1024}KB, PDF {len(p) // 1024}KB"


def c_verify():
    ref = pd.DataFrame({"구분": ["a", "b"], "건수": [1, 2]})
    t = pd.DataFrame({"구분": ["a", "b"], "청구건수": [1, 3]})
    _, s = verify.compare(t, "구분", ref, "구분", [("청구건수", "건수")])
    if (s["일치"], s["불일치"]) != (1, 1):
        raise ValueError("검증 비교가 올바르게 동작하지 않습니다")


# ---------------------------------------------------------------------------
# 2) 보안 · 장애 격리 · 성능
# ---------------------------------------------------------------------------
APP_DIRS = ["", "core", "ui", "reports", "prototype"]


def _py_files(dirs=APP_DIRS):
    out = []
    for d in dirs:
        folder = os.path.join(config.BASE_DIR, d)
        if os.path.isdir(folder):
            out += [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.endswith(".py")]
    return out


def c_no_network_or_danger():
    banned = {"requests", "urllib", "urllib3", "http", "httpx", "aiohttp", "socket", "smtplib", "ftplib",
              "telnetlib", "paramiko", "subprocess", "pickle", "ctypes", "webbrowser"}
    bad = []
    for f in _py_files():
        rel = os.path.relpath(f, config.BASE_DIR)
        for node in ast.walk(ast.parse(open(f, encoding="utf-8").read())):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            bad += [f"{rel}: '{m}' 가져오기(외부 통신/위험 기능)" for m in mods if m in banned]
            if isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Name) and fn.id in ("eval", "exec", "compile", "__import__"):
                    bad.append(f"{rel}:{node.lineno} 내장 {fn.id}() 사용")
                if isinstance(fn, ast.Attribute) and fn.attr in ("system", "popen") and isinstance(fn.value, ast.Name) and fn.value.id == "os":
                    bad.append(f"{rel}:{node.lineno} os.{fn.attr}() 사용")
    if bad:
        raise ValueError(" / ".join(bad))


def c_no_urls_or_secrets():
    bad = []
    secret = re.compile(r"(?i)(password|passwd|secret|api[_-]?key|token)\s*=\s*[\"'][^\"']{4,}[\"']")
    for f in _py_files():
        rel = os.path.relpath(f, config.BASE_DIR).replace("\\", "/")
        text = open(f, encoding="utf-8").read()
        if re.search(r"https?://", text) and rel != "ui/theme.py":
            bad.append(f"{rel}: 주소(URL)가 들어 있습니다")
        if secret.search(text):
            bad.append(f"{rel}: 비밀번호/키로 보이는 값이 코드에 있습니다")
    if bad:
        raise ValueError(" / ".join(bad))
    if config.USE_WEB_FONT:
        return "주의: USE_WEB_FONT=True 라서 화면 글꼴을 인터넷에서 받아옵니다 (보안 환경에서는 False 권장)"


def c_telemetry_off():
    path = os.path.join(config.BASE_DIR, ".streamlit", "config.toml")
    if not os.path.exists(path):
        raise ValueError(".streamlit/config.toml 이 없습니다 (사용 통계 전송을 끄는 설정)")
    # tomllib 은 파이썬 3.11 부터라서(병원/개인 PC 가 3.10 일 수 있음) 글자 검사로 확인합니다
    text = re.sub(r"(?m)^\s*#.*$", "", open(path, encoding="utf-8").read())
    if not re.search(r"(?m)^\s*gatherUsageStats\s*=\s*false\s*$", text):
        raise ValueError(".streamlit/config.toml 의 [browser] gatherUsageStats 가 false 여야 합니다")
    if not re.search(r'(?m)^\s*address\s*=\s*"127\.0\.0\.1"\s*$', text):
        raise ValueError('.streamlit/config.toml 의 [server] address 가 "127.0.0.1" 이어야 합니다 '
                         "(없으면 같은 네트워크의 다른 PC 에서도 이 프로그램에 접속할 수 있습니다)")
    launcher = os.path.join(config.BASE_DIR, "packaging", "launcher.py")
    if os.path.exists(launcher) and "--server.address=127.0.0.1" not in open(launcher, encoding="utf-8").read():
        raise ValueError("packaging/launcher.py 의 실행 옵션에 --server.address=127.0.0.1 이 없습니다 (exe 가 외부에 열림)")


HOSTILE = ['<img src=x onerror="alert(1)">', "내과 & 외과 <b>굵게</b>", '=HYPERLINK("http://evil.example","x")',
           "+SUM(1+1)", "@SUM(1)", "A&B <para>", "</para><b>"]


def c_hostile_values():
    from core.format import esc
    from ui.components import chip
    if "<img" in chip(HOSTILE[0]) or "<" in esc(HOSTILE[1]):
        raise ValueError("화면 HTML 에 태그가 그대로 들어갑니다 (이스케이프 누락)")
    df = STATE["df"].head(60).copy()
    text_cols = [c for c, sp in config.COLUMNS.items() if sp.get("type") == "text" and c != "청구번호"]
    for j, col in enumerate(text_cols):
        for i, h in enumerate(HOSTILE):
            df.loc[df.index[i * 8:(i + 1) * 8], col] = h
    pairs = [(s, s.compute(df)) for s in stats_config.STATS if not s.missing(df.columns, config.COLUMNS)]
    ins = insights.generate({s.id: t for s, t in pairs}) + HOSTILE
    pdf.build(df, pairs, ins, "2026-01 ~ 2026-06")
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(excel.build(df, pairs, ins, HOSTILE[0])))
    formulas = [c.coordinate for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.data_type == "f"]
    if formulas:
        raise ValueError(f"Excel 보고서에 수식으로 저장된 셀이 있습니다 (수식 주입 위험): {formulas[:3]}")
    return "태그/수식/특수문자 포함 데이터로 PDF·Excel 생성 확인"


def c_isolation():
    from core.stats import Stat
    broken = Stat(id="broken", title="고장", group_by="진료과", metrics={"x": ("청구금액", "countt")})
    try:
        broken.compute(STATE["df"])
    except ValueError:
        return "고장 난 정의는 오류를 내고, 다른 통계는 정상 계산됨 (화면에서는 영역별로 경고만 표시)"
    raise ValueError("잘못된 집계 방식이 오류로 걸러지지 않습니다")


def c_performance():
    big = synthetic.make_df(200_000, seed=2)
    t0 = time.perf_counter()
    df, _ = loader.prepare(big, {c: c for c in config.COLUMNS})
    tables = {s.id: s.compute(df) for s in stats_config.STATS if not s.missing(df.columns, config.COLUMNS)}
    insights.generate(tables)
    sec = time.perf_counter() - t0
    if sec > 10:
        raise ValueError(f"{len(big):,}행 처리에 {sec:.1f}초 걸립니다 (기준 10초). 새로 추가한 통계/수식을 확인하세요")
    return f"{len(big):,}행 처리 {sec:.2f}초"


def c_structure_no_values():
    from openpyxl import Workbook
    from core import structure
    secrets = ["홍길동", "010-1234-5678", "SECRET-9XZ", "980101-1234567", "김철수", "이영희", "비밀진료과", "99887766"]
    wb = Workbook()
    ws = wb.active
    ws.title = "청구"
    ws.append(["청구월", "청구번호", "진료과", "청구금액", "980101-1234567", "99887766"])
    for i in range(30):
        ws.append(["2026-01", f"N{i}", "비밀진료과" if i % 2 else "홍길동", 1000 + i, "010-1234-5678", "SECRET-9XZ"])
    ws2 = wb.create_sheet("머리글없음")
    ws2.append(["김철수", "이영희"])
    ws2.append(["김철수", "이영희"])
    buf = io.BytesIO()
    wb.save(buf)
    text = "\n".join(structure.summarize("x.xlsx", buf.getvalue()))
    leaked = [v for v in secrets if v in text]
    if leaked:
        raise ValueError(f"구조 요약에 값이 출력되었습니다: {leaked}")
    if structure.HIDDEN not in text:
        raise ValueError("값처럼 보이는 컬럼 이름이 숨겨지지 않았습니다")
    # 통계표(항목 × 기간) 모양: 항목 이름·기간 이름이 출력되면 안 되고, 모양 설명은 나와야 함
    wb2 = Workbook()
    w2 = wb2.active
    w2.title = "통계"
    w2.append(["구분", "세부", "비밀기간A", "비밀기간B", "비밀기간C", "비밀기간D"])
    for i in range(6):
        w2.append([f"비밀항목{i}", "비밀세부", 10 + i, 20 + i, 30 + i, 40 + i])
    buf2 = io.BytesIO()
    wb2.save(buf2)
    t2 = "\n".join(structure.summarize("y.xlsx", buf2.getvalue()))
    leaked2 = [v for v in ("비밀항목0", "비밀항목5", "비밀세부", "비밀기간A", "비밀기간D") if v in t2]
    if leaked2:
        raise ValueError(f"통계표 모양의 구조 요약에 이름이 출력되었습니다: {leaked2}")
    if "통계표(항목 × 기간)" not in t2:
        raise ValueError("통계표 모양을 설명하는 부분이 나오지 않습니다")
    return "이름/전화/주민번호 모양 값 8종, 통계표의 항목·기간 이름이 출력되지 않음"


# ---------------------------------------------------------------------------
# 3) 구조 점검: 프로토타입 기능이 '한 곳'에만 있는지
# ---------------------------------------------------------------------------
def c_prototype_isolated():
    """prototype/ 폴더를 지워도 돌아가도록: 다른 파일이 prototype 을 직접 가져오거나 샘플 전용 문구를 쓰지 않는지"""
    allowed = {"hooks.py"}
    forbidden_text = ["샘플 데이터로 시작", "더미데이터", "연습용_", "use_sample"]
    bad = []
    for f in _py_files(["", "core", "ui", "reports"]):
        rel = os.path.relpath(f, config.BASE_DIR).replace("\\", "/")
        src = open(f, encoding="utf-8").read()
        for node in ast.walk(ast.parse(src)):
            mod = None
            if isinstance(node, ast.Import):
                mod = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mod = [node.module.split(".")[0]]
            if mod and "prototype" in mod and rel not in allowed:
                bad.append(f"{rel}:{node.lineno} prototype 를 직접 가져옵니다 (hooks.py 를 통해서만 부르세요)")
        for t in forbidden_text:
            if t in src and rel not in allowed:
                bad.append(f"{rel}: 프로토타입 전용 문구 '{t}' 가 본 프로그램 코드에 있습니다 (prototype/ 로 옮기세요)")
    if bad:
        raise ValueError(" / ".join(bad))
    return "프로토타입 모드 " + ("켜짐" if hooks.enabled() else "꺼짐(실사용 모드)")


def c_bat_safe():
    """윈도우 .bat 의 echo 줄에 > < | & 가 있으면 파일을 덮어쓰거나 명령으로 해석될 수 있습니다."""
    bad = []
    for root, dirs, files in os.walk(config.BASE_DIR):
        dirs[:] = [d for d in dirs if d not in (".git", "dist", "build", "__pycache__")]
        for f in files:
            if not f.lower().endswith(".bat"):
                continue
            path = os.path.join(root, f)
            for i, line in enumerate(open(path, encoding="utf-8", errors="replace").read().splitlines(), 1):
                m = re.match(r"(?i)^\s*echo[ .:]\s*(.*)$", line)
                if m and re.search(r"[<>|&]", m.group(1).replace("^>", "").replace("^<", "").replace("^|", "").replace("^&", "")):
                    bad.append(f"{os.path.relpath(path, config.BASE_DIR)}:{i} echo 줄에 > < | & 가 있습니다: {line.strip()[:50]}")
            if b"\r\n" not in open(path, "rb").read() and open(path, "rb").read().strip():
                bad.append(f"{os.path.relpath(path, config.BASE_DIR)}: 줄바꿈이 CRLF 가 아닙니다 (윈도우에서 오동작할 수 있음)")
    if bad:
        raise ValueError(" / ".join(bad))


def c_launcher_imports():
    """app 이 쓰는 외부 라이브러리가 exe 런처(packaging/launcher.py)에 모두 담겨 있는지"""
    launcher = os.path.join(config.BASE_DIR, "packaging", "launcher.py")
    if not os.path.exists(launcher):
        return "packaging/launcher.py 가 없어 건너뜀"
    own = {n[:-3] for n in os.listdir(config.BASE_DIR) if n.endswith(".py")} | {
        d for d in os.listdir(config.BASE_DIR) if os.path.isdir(os.path.join(config.BASE_DIR, d))}
    own |= {n[:-3] for n in os.listdir(HERE) if n.endswith(".py")}          # tests/ 안의 내부 모듈(synthetic 등)
    std = set(sys.stdlib_module_names) | {"__future__"}

    def tops(path):
        mods = set()
        for node in ast.walk(ast.parse(open(path, encoding="utf-8").read())):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mods.add(node.module.split(".")[0])
        return mods

    used = set()
    for f in _py_files(["", "core", "ui", "reports", "prototype", "tests"]):
        used |= tops(f)
    missing = sorted(m for m in used - std - own if m not in tops(launcher))
    if missing:
        raise ValueError(f"app 이 쓰는 라이브러리 {missing} 가 packaging/launcher.py 의 import 목록에 없습니다 (exe 에서 'No module named' 오류가 납니다)")
    return f"app 이 쓰는 외부 라이브러리 {len(used - std - own)}개가 런처에 모두 있음"


def c_chart_export():
    """차트 이미지(PNG) 저장: 켜면 카메라 버튼·흰 배경·안전한 파일 이름, 끄면 버튼과 안내 문구가 모두 사라지는지"""
    from ui import charts
    import plotly.graph_objects as go
    saved = getattr(config, "CHART_IMAGE_EXPORT", True)
    try:
        config.CHART_IMAGE_EXPORT = True
        cfg = charts.plot_config('월별: 청구건수/삭감률 <테스트>')
        if cfg.get("modeBarButtons") != [["toImage"]] or cfg.get("toImageButtonOptions", {}).get("format") != "png":
            raise ValueError("차트에 PNG 저장 버튼 설정이 없습니다 (ui/charts.py 의 plot_config)")
        name = cfg["toImageButtonOptions"]["filename"]
        if re.search(r'[\\/:*?"<>|]', name) or not name:
            raise ValueError(f"저장 파일 이름에 윈도우에서 쓸 수 없는 글자가 있습니다: {name!r}")
        if not charts.export_hint():
            raise ValueError("저장 기능이 켜져 있는데 안내 문구가 없습니다")
        config.CHART_IMAGE_EXPORT = False
        if charts.plot_config("x").get("displayModeBar") is not False or charts.export_hint():
            raise ValueError("CHART_IMAGE_EXPORT = False 인데 저장 버튼 또는 안내 문구가 남아 있습니다")
    finally:
        config.CHART_IMAGE_EXPORT = saved
    if charts._style(go.Figure(), 300).layout.paper_bgcolor != "#FFFFFF":
        raise ValueError("차트 배경이 흰색이 아니라서 저장된 이미지가 투명해집니다")
    return f"파일 이름 예: {name}.png / 끄기 스위치 동작 확인"


def c_chart_single_exit():
    """모든 차트가 charts._show 한 곳으로만 나가는지 (새 차트 종류가 저장 설정을 빠뜨리는 것을 막음)"""
    bad = []
    for f in _py_files(["", "core", "ui", "reports", "prototype"]):
        rel = os.path.relpath(f, config.BASE_DIR).replace("\\", "/")
        tree = ast.parse(open(f, encoding="utf-8").read())
        parents = {}
        for node in ast.walk(tree):
            for ch in ast.iter_child_nodes(node):
                parents[ch] = node
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "plotly_chart":
                cur, owner = node, None
                while cur in parents:
                    cur = parents[cur]
                    if isinstance(cur, ast.FunctionDef):
                        owner = cur.name
                        break
                if not (rel == "ui/charts.py" and owner == "_show"):
                    bad.append(f"{rel}:{node.lineno} st.plotly_chart 를 직접 호출합니다 (charts._show 를 쓰세요)")
    if bad:
        raise ValueError(" / ".join(bad))


def c_chart_render():
    """모든 차트 코드를 실제로 실행해 봅니다 (이름 오타·빠진 변수 같은 오류를 화면을 켜기 전에 발견)"""
    from ui import charts
    drawn, orig = [], charts._show
    charts._show = lambda fig, chart: drawn.append((chart.title, len(fig.data)))
    try:
        ctx = {"alert_threshold": 5.0, "alert_field": getattr(config, "KPIS", [{}])[-1].get("field")}
        todo = [s for s in stats_config.STATS if s.chart is not None and s.id in STATE["tables"] and not STATE["tables"][s.id].empty]
        for s in todo:
            charts.render(s, STATE["tables"][s.id], ctx)
    finally:
        charts._show = orig
    if len(drawn) != len(todo) or any(n == 0 for _, n in drawn):
        raise ValueError(f"그려지지 않은 차트가 있습니다: 기대 {len(todo)}개, 실제 {drawn}")
    return f"차트 {len(drawn)}개를 실제로 그려 봄"


def c_sidebar_toggle_css():
    """사이드바를 접은 뒤 다시 펼칠 수 있어야 합니다. 상단 도구줄(stToolbar)을 통째로 숨기면 '펼치기' 버튼까지 사라집니다."""
    css = open(os.path.join(config.BASE_DIR, "ui", "theme.py"), encoding="utf-8").read()
    for rule in css.split("}"):
        if "display: none" in rule and '[data-testid="stToolbar"]' in rule:
            raise ValueError('ui/theme.py 가 [data-testid="stToolbar"] 를 숨기고 있습니다 (사이드바를 접으면 다시 열 수 없게 됩니다). '
                             "Deploy/메뉴만 따로 숨기세요")
    if "stExpandSidebarButton" not in css and "stSidebarCollapsedControl" not in css:
        raise ValueError("사이드바 펼치기 버튼을 보이게 하는 스타일이 없습니다 (남색 상단 바에 묻혀 안 보일 수 있음)")


# ---------------------------------------------------------------------------
# 통계표 모드(항목 × 기간) 점검
# ---------------------------------------------------------------------------
def c_table_layouts():
    """가상 표 여러 모양(단순 / 병합 셀·띄어쓰기·합계 열 / 숫자 표기 제각각 / 가로세로 반대)을 올바르게 읽는지"""
    import synthetic_tables as stb
    from core import table_mode as tm
    done = []
    cases = [(n, f) for n, f in stb.ALL.items()] + list(stb.MULTI.items()) + list(stb.HIER.items()) + [("가로세로 반대(바꾸기)", stb.layout_transposed)]
    for name, fn in cases:
        raw, exp = fn()
        if name.startswith("가로세로"):
            raw = raw.T.reset_index(drop=True)
        p = tm.read(raw, **exp.get("overrides", {}))
        L = p.long
        if "warn_zero" in exp:
            zero = [w for w in p.warnings if "모두 0" in w]
            if not zero or f"{exp['warn_zero']}개" not in zero[0]:
                raise ValueError(f"[{name}] 값이 모두 0인 줄 경고가 없거나 개수가 다릅니다: {zero} (기대 {exp['warn_zero']}개)")
        if exp.get("no_note") and p.spec.auto_note:
            raise ValueError(f"[{name}] 문제가 풀리지 않는데도 자동 해석을 바꿨습니다(안내문 있음): {p.spec.auto_note[:60]}")
        if exp.get("no_drop") and any("항목 이름이 없는 줄" in w for w in p.warnings):
            raise ValueError(f"[{name}] 값이 있는 줄을 항목 이름이 없다며 제외했습니다: {[w[:60] for w in p.warnings]}")
        if exp.get("no_reverse") and (p.spec.reverse_labels or p.spec.block_cols):
            raise ValueError(f"[{name}] 뒤집으면 안 되는 표를 자동으로 뒤집었습니다")
        if "dropped_rows_hint" in exp:
            hint = [w for w in p.warnings if "항목 이름이 없는 줄" in w]
            if not hint or any(str(r) not in hint[0] for r in exp["dropped_rows_hint"]) or f"열 {exp['dropped_cols_hint']}" not in hint[0]:
                raise ValueError(f"[{name}] 항목 이름 없는 줄 안내가 없거나 줄 번호/열이 다릅니다: {hint}")
        if exp.get("expect_dup"):
            hint = [w for w in p.warnings if "줄 번호" in w]
            if not p.duplicates or not hint or any(str(r) not in hint[0] for r in exp["dup_rows_hint"]):
                raise ValueError(f"[{name}] 겹침 안내가 없거나 줄 번호가 다릅니다: 겹침 {p.duplicates}, 경고 {hint} (기대 줄 {exp['dup_rows_hint']})")
        if exp.get("no_dup") and p.duplicates:
            raise ValueError(f"[{name}] 같은 항목이 겹칩니다(블록 이름을 못 읽음): {p.duplicates}개")
        if len(p.items) != exp["items"] or len(p.series) != exp["series"] or p.periods != exp["periods"]:
            raise ValueError(f"[{name}] 항목/기간 수가 다릅니다: 항목 {len(p.items)}(기대 {exp['items']}), 기간 {p.periods}")
        if "header_start" in exp and p.spec.header_start != exp["header_start"]:
            raise ValueError(f"[{name}] 머리글 첫 줄 탐지가 다릅니다: {p.spec.header_start} (기대 {exp['header_start']})")
        if "absent_sub" in exp and (L["하위구분"] == exp["absent_sub"]).any():
            raise ValueError(f"[{name}] 제외해야 할 '{exp['absent_sub']}' 묶음이 남아 있습니다")
        if p.spec.label_cols != exp["label_cols"] or p.spec.header_row != exp["header_row"]:
            raise ValueError(f"[{name}] 열/줄 탐지가 다릅니다: 항목열 {p.spec.label_cols}, 기간줄 {p.spec.header_row}")
        for item, sub, per, val in exp.get("spot", []):
            r = L[(L["항목"] == item) & (L["하위구분"] == sub) & (L["기간"] == per)]
            if len(r) != 1 or abs(r["값"].iloc[0] - val) > 1e-9:
                raise ValueError(f"[{name}] 값이 다릅니다: {item}/{sub}/{per} 기대 {val}, 실제 {None if r.empty else r['값'].iloc[0]}")
        for item, sub, per in exp.get("missing", []):
            if not L[(L["항목"] == item) & (L["하위구분"] == sub) & (L["기간"] == per)].empty:
                raise ValueError(f"[{name}] 비어 있어야 할 칸에 값이 있습니다: {item}/{per}")
        if "cleaned" in exp and not exp["cleaned"] <= set(p.items):
            raise ValueError(f"[{name}] 띄어쓰기 정리 실패: {sorted(exp['cleaned'] - set(p.items))}")
        if "pct" in exp and p.pct_series != exp["pct"]:
            raise ValueError(f"[{name}] % 표시 인식 실패: {p.pct_series}")
        done.append(name)
    return f"{len(done)}가지 모양 OK: " + ", ".join(done)


def c_table_hostile():
    """항목 이름에 태그/수식/특수문자가 있어도 보고서(Excel/PDF)가 안전하고, 이스케이프 도구가 동작하는지"""
    import synthetic_tables as stb
    import openpyxl
    from core import table_mode as tm, table_stats as ts
    from core.format import esc
    from reports import table_report
    p = tm.read(stb.hostile_table())
    if len(p.items) != 5:
        raise ValueError(f"악성 이름 표를 읽지 못했습니다: 항목 {len(p.items)}개")
    mat = ts.matrix(p.long, p.series, p.periods)
    summ = ts.summary(mat)
    ins = ts.sentences(summ, p.periods)
    meta = {"period": "2026-01 ~ 2026-06", "n_items": len(p.items)}
    table_report.build_pdf(mat, summ, ins, meta)
    wb = openpyxl.load_workbook(io.BytesIO(table_report.build_excel(p.long, mat, summ, ins, meta)))
    formulas = [c.coordinate for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.data_type == "f"]
    if formulas:
        raise ValueError(f"통계표 Excel 보고서에 수식으로 저장된 셀이 있습니다: {formulas[:3]}")
    if "<" in esc(p.items[0]) or "<" in esc(ins[1] if len(ins) > 1 else ""):
        raise ValueError("이스케이프 도구가 태그를 걸러내지 못합니다")
    return "태그·수식·특수문자 항목 5개로 요약/PDF/Excel 생성 확인"


def c_table_perf():
    """항목 3,000개 × 기간 36개 표를 읽고 요약하는 데 걸리는 시간"""
    import synthetic_tables as stb
    from core import table_mode as tm, table_stats as ts
    raw = stb.big_table(3000, 36)
    t0 = time.perf_counter()
    p = tm.read(raw)
    mat = ts.matrix(p.long, p.series, p.periods)
    ts.sentences(ts.summary(mat), p.periods)
    sec = time.perf_counter() - t0
    if len(p.long) != 3000 * 36 or sec > 8:
        raise ValueError(f"값 {len(p.long):,}개(기대 {3000 * 36:,}), {sec:.1f}초 (기준 8초)")
    return f"항목 3,000 × 기간 36 → {len(p.long):,}개 값, {sec:.2f}초"


def c_core_no_streamlit():
    """core/ 는 화면 라이브러리(streamlit)를 가져오지 않는 순수 계산 모듈이어야 합니다 (테스트/재사용을 위해)"""
    bad = []
    for f in _py_files(["core"]):
        for node in ast.walk(ast.parse(open(f, encoding="utf-8").read())):
            names = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else (
                [node.module.split(".")[0]] if isinstance(node, ast.ImportFrom) and node.module else [])
            if "streamlit" in names:
                bad.append(os.path.relpath(f, config.BASE_DIR))
    if bad:
        raise ValueError(f"core/ 에서 streamlit 을 가져옵니다: {sorted(set(bad))} (화면 코드는 ui/ 로 옮기세요)")


def c_no_data_files():
    """병원 데이터가 프로그램 폴더 안에 섞여 있지 않은지, 그리고 .gitignore 가 데이터 파일을 막고 있는지"""
    exts = (".xlsx", ".xlsm", ".xlsb", ".xls", ".csv", ".tsv")
    allowed = os.path.join(config.BASE_DIR, "prototype", "data")
    found = []
    for root, dirs, files in os.walk(config.BASE_DIR):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "dist", "build")]
        if os.path.abspath(root).startswith(os.path.abspath(allowed)):
            continue
        found += [os.path.relpath(os.path.join(root, f), config.BASE_DIR) for f in files if f.lower().endswith(exts)]
    if found:
        raise ValueError(f"프로그램 폴더 안에 데이터 파일 {len(found)}개가 있습니다: {', '.join(found[:3])}{' …' if len(found) > 3 else ''} "
                         "— 병원 데이터는 프로그램 폴더 밖에 두세요. (GitHub 등에 올라가거나 압축에 포함될 수 있습니다)")
    gi = os.path.join(config.BASE_DIR, ".gitignore")
    if not os.path.exists(gi):
        raise ValueError(".gitignore 가 없습니다 (엑셀/CSV 가 GitHub 에 올라가는 것을 막는 파일)")
    lines = [ln.strip() for ln in open(gi, encoding="utf-8").read().splitlines() if ln.strip() and not ln.strip().startswith("#")]
    missing = [e for e in ("*.xlsx", "*.xls", "*.csv") if e not in lines]
    if missing:
        raise ValueError(f".gitignore 에 {missing} 규칙이 없습니다 (데이터 파일이 GitHub 에 올라갈 수 있음)")


def c_replica_no_leak():
    """구조 복제본에 원본의 이름·숫자·메타정보(시트 이름, 문서 속성, 메모, 이름 정의, 머리글/바닥글)가 남지 않고 구조는 같은지"""
    import re as _re
    import zipfile
    import openpyxl
    import synthetic_replica as sr
    from core import anonymize
    data = sr.build_hostile_xlsx()
    rep, report, ok = anonymize.make_replica("x.xlsx", data, seed=3)
    if not ok or not rep:
        raise ValueError(f"복제본을 만들지 못했습니다: {report}")
    import html
    z = zipfile.ZipFile(io.BytesIO(rep))
    leaked = {}
    for n in z.namelist():
        blob = html.unescape(z.read(n).decode("utf-8", errors="ignore"))       # openpyxl 은 한글을 &#...; 로 저장하므로 풀어서 검사
        for sc in sr.SECRETS:
            if sc in blob:
                leaked.setdefault(sc, []).append(n)
    if leaked:
        raise ValueError(f"복제본에 원본 정보가 남아 있습니다: {leaked}")
    # 문자 참조를 푸는 검사가 실제로 한글을 찾아내는지 (이 검사 자체가 헛돌지 않는지)
    if "홍길동" not in html.unescape(z.read("xl/worksheets/sheet1.xml").decode("utf-8", errors="ignore")) and True:
        pass
    probe = io.BytesIO()
    pw = openpyxl.Workbook()
    pw.active["A1"] = "홍길동"
    pw.save(probe)
    pz = zipfile.ZipFile(io.BytesIO(probe.getvalue()))
    if "홍길동" not in html.unescape(pz.read("xl/worksheets/sheet1.xml").decode("utf-8", errors="ignore")) or \
            "홍길동" in pz.read("xl/worksheets/sheet1.xml").decode("utf-8", errors="ignore"):
        raise ValueError("파일 내부 검사 방식이 한글 저장 방식(문자 참조)과 맞지 않습니다")
    cell_texts = [c.value for ws in openpyxl.load_workbook(io.BytesIO(rep)).worksheets for row in ws.iter_rows() for c in row if isinstance(c.value, str)]
    hit = [sc for sc in sr.SECRETS for t in cell_texts if sc in t]
    if hit:
        raise ValueError(f"복제본의 글자 칸에 원본 정보가 남아 있습니다: {sorted(set(hit))}")
    wb = openpyxl.load_workbook(io.BytesIO(rep))
    if wb.sheetnames != ["시트1", "시트2"] or wb.properties.creator or list(wb.defined_names.keys()):
        raise ValueError(f"시트 이름/문서 속성/이름 정의가 남아 있습니다: {wb.sheetnames}, {wb.properties.creator!r}")
    src = openpyxl.load_workbook(io.BytesIO(data))
    if sorted(str(r) for r in wb["시트1"].merged_cells.ranges) != sorted(str(r) for r in src.worksheets[0].merged_cells.ranges):
        raise ValueError("병합 셀이 원본과 다릅니다")
    texts = [c.value for row in wb["시트1"].iter_rows() for c in row if isinstance(c.value, str)]
    nums = [c.value for row in wb["시트1"].iter_rows() for c in row if isinstance(c.value, (int, float))]
    if "2026-01" not in texts or "합계" not in texts:
        raise ValueError("기간 이름(2026-01)이나 '합계'가 보존되지 않았습니다")
    if not any(_re.fullmatch(r"(\S ){3,}\S", t) for t in texts):
        raise ValueError("띄어 쓴 이름의 모양이 보존되지 않았습니다")
    if nums.count(0) < 6:
        raise ValueError("0 인 칸이 보존되지 않았습니다")
    fm = {c.number_format for row in wb["시트1"].iter_rows() for c in row if c.value is not None}
    if "#,##0" not in fm or "0.0%" not in fm or any(_re.search(r"[가-힣]", f) for f in fm):
        raise ValueError(f"숫자 서식 처리가 올바르지 않습니다: {fm}")
    if not any("동일" in l for l in report) or any("다릅니다" in l for l in report):
        raise ValueError(f"읽기 결과 비교가 동일하지 않습니다: {report}")
    # 안전장치(fail-closed): 이름 바꾸기가 고장 나서 원본 이름이 그대로 남으면 복제본을 만들지 않아야 함 (변환 기록과 무관하게 검출)
    orig_token = anonymize._State.token
    anonymize._State.token = lambda self, key, s: s
    try:
        bad_rep, bad_report, bad_ok = anonymize.make_replica("x.xlsx", data, seed=3)
    finally:
        anonymize._State.token = orig_token
    if bad_ok or bad_rep:
        raise ValueError("이름 바꾸기가 실패했는데도 복제본을 만들었습니다 (누출 검사가 동작하지 않음)")
    if anonymize._leaks(data, anonymize._original_label_keys(openpyxl.load_workbook(io.BytesIO(data)), anonymize._vocab())) < 1:
        raise ValueError("누출 검사가 원본 파일 자체의 이름을 찾아내지 못합니다")
    return "시트 이름·문서 속성·메모·이름 정의·머리글 제거, 비밀 문자열 0건, 병합 셀·서식·0 보존"


def c_replica_structure():
    """가상 표 여러 모양과 병합 엑셀의 복제본이 원본과 '읽기 결과 모양'이 같은지 (복제본으로 구조 문제를 재현할 수 있는지)"""
    import synthetic_replica as sr
    import synthetic_tables as stb
    from core import anonymize
    cases = [(n, f) for n, f in stb.ALL.items()] + list(stb.MULTI.items()) + list(stb.HIER.items())
    done = []
    for name, fn in cases:
        raw, exp = fn()
        buf = io.BytesIO()
        raw.to_excel(buf, header=False, index=False, sheet_name="s")
        _, report, ok = anonymize.make_replica("x.xlsx", buf.getvalue(), seed=5)
        bad = [l for l in report if "다릅니다" in l]
        if not ok or bad or not any("동일" in l for l in report):
            raise ValueError(f"[{name}] 복제본의 구조가 원본과 다릅니다: {bad or report}")
        done.append(name)
    _, report, ok = anonymize.make_replica("x.xlsx", sr.build_merged_xlsx(), seed=5)
    if not ok or any("다릅니다" in l for l in report) or not any("동일" in l for l in report):
        raise ValueError(f"[병합 엑셀] 복제본의 구조가 원본과 다릅니다: {report}")
    return f"{len(done) + 1}가지 모양에서 복제본의 읽기 결과 = 원본"


def c_replica_perf():
    """표가 커도(항목 1,000 × 기간 36) 복제본이 충분히 빨리 만들어지는지"""
    from openpyxl import Workbook
    from core import anonymize
    wb = Workbook()
    ws = wb.active
    ws.append(["구분"] + [f"2024-{(m % 12) + 1:02d}" if m < 12 else f"{2025 + (m - 12) // 12}-{(m % 12) + 1:02d}" for m in range(36)])
    for i in range(1000):
        ws.append([f"항목{i:04d}"] + [(i * 7 + j * 13) % 9999 + 1 for j in range(36)])
    buf = io.BytesIO()
    wb.save(buf)
    t0 = time.perf_counter()
    rep, report, ok = anonymize.make_replica("x.xlsx", buf.getvalue(), seed=2)
    sec = time.perf_counter() - t0
    if not ok or sec > 20:
        raise ValueError(f"{sec:.1f}초 (기준 20초) / {report}")
    return f"1,000 × 36 표 {sec:.1f}초"


def c_panel_uses_suggested_spec():
    """suggest() 가 자동으로 고르는 설정(열·줄·체크박스)이 통계표 설정 화면의 기본값에 모두 연결되어 있는지.
    (코어가 '열 D 추가 + 합쳐진 칸 채우기'를 골랐는데 화면 체크박스가 False 로 박혀 있어 겹침이 안 풀리던 실수를 막음)"""
    src = open(os.path.join(config.BASE_DIR, "ui", "table_panel.py"), encoding="utf-8").read()
    need = ["label_cols", "value_cols", "header_row", "header_start", "use_sections", "reverse_labels", "ffill_sub", "auto_note", "block_cols", "reset_on_blank"]
    missing = [f for f in need if f"spec0.{f}" not in src]
    if missing:
        raise ValueError(f"ui/table_panel.py 가 자동 추천 설정을 화면 기본값에 연결하지 않았습니다: {missing}")


def c_merged_grid():
    """엑셀의 진짜 병합 범위를 읽어서 채우는지: 블록 이름이 '빈 줄을 끼고' 여러 줄에 합쳐져 있어도 아래 줄들의 항목을 잃지 않아야 함"""
    from openpyxl import Workbook
    from core import loader, table_mode as tm
    wb = Workbook()
    ws = wb.active
    ws.title = "s"
    ws.append(["구분", "세부"] + [f"2026-{m:02d}" for m in range(1, 7)])
    for blk, base in (("X", 100), ("Y", 200)):
        start = ws.max_row + 1
        for k, sub in enumerate(["a", "b", "c"]):
            ws.append([blk if k == 0 else None, sub] + [base + 10 * k + j for j in range(6)])
            if k == 1:
                ws.append([])                                              # 합쳐진 칸 안에 끼어 있는 빈 줄
        ws.merge_cells(start_row=start, start_column=1, end_row=ws.max_row, end_column=1)
    buf = io.BytesIO()
    wb.save(buf)
    data = buf.getvalue()
    grid = loader.read_raw_grid("x.xlsx", data, "s")
    col0 = [grid.iat[i, 0] for i in range(len(grid))]
    if col0[1:5] != ["X", "X", "X", "X"] or col0[5:9] != ["Y", "Y", "Y", "Y"]:
        raise ValueError(f"병합된 칸이 병합 범위 전체에 채워지지 않았습니다: {col0}")
    p = tm.read(grid)
    if len(p.items) != 2 or len(p.series) != 6 or any("항목 이름이 없는 줄" in w for w in p.warnings):
        raise ValueError(f"병합 범위를 반영한 읽기 결과가 다릅니다: 항목 {len(p.items)}, 시리즈 {len(p.series)}, 경고 {p.warnings}")
    raw_old = pd.read_excel(io.BytesIO(data), header=None)                      # 예전 방식(병합 정보 버림)
    old = tm.parse(raw_old, tm.detect(raw_old))                                  # 자동 보정 없이 탐지만 하면 빈 줄 뒤의 줄들을 잃음
    if not any("항목 이름이 없는 줄" in w for w in old.warnings):
        raise ValueError("(시험 자체 점검) 예전 방식에서도 줄을 잃지 않아서, 이 시험이 병합 범위의 효과를 확인하지 못합니다")
    return "빈 줄을 낀 병합 칸도 정확히 채움 (예전 방식은 줄 손실)"


def c_table_paths_use_merged_grid():
    """통계표 모드의 모든 읽기 경로(화면 설정, 시트 고르기, 구조 요약, 구조 복제본)가 병합 범위를 채우는 읽기(read_raw_grid)를 쓰는지.
    (한 곳이라도 예전 방식 pandas 로 읽으면, 병합된 칸이 빈 칸이 되어 화면에서는 항목이 사라짐)"""
    need = {"ui/table_panel.py": 2, "core/structure.py": 1, "core/anonymize.py": 1}
    bad = []
    for rel, n in need.items():
        src = open(os.path.join(config.BASE_DIR, rel), encoding="utf-8").read()
        if src.count("read_raw_grid") < n:
            bad.append(f"{rel}: read_raw_grid 사용 {src.count('read_raw_grid')}번 (필요 {n}번 이상)")
        if "loader.read_table(name, data, sheet, None)" in src or "loader.read_table(name, data, sh, None)" in src:
            bad.append(f"{rel}: header=None 로 loader.read_table 을 직접 호출합니다 (병합 범위가 반영되지 않음)")
    if bad:
        raise ValueError(" / ".join(bad))


GENERIC = [
    ("테스트 데이터 만들기", c_data), ("통계 id 중복 확인", c_ids), ("통계가 쓰는 컬럼이 COLUMNS 에 있는지", c_columns),
    ("통계 계산", c_compute), ("차트 설정", c_charts), ("모든 차트 코드 실행", c_chart_render),
    ("차트 배치(DASHBOARD_LAYOUT)", c_layout),
    ("KPI 카드 설정", c_kpi), ("자동 요약 문장", c_insight), ("Excel/PDF 보고서 만들기", c_reports),
    ("결과 검증 비교", c_verify),
    ("외부 통신/위험 코드 없음 (정적 검사)", c_no_network_or_danger), ("코드에 주소·비밀번호 없음", c_no_urls_or_secrets),
    ("사용 통계 전송 꺼짐 + 이 PC 안에서만 접속(127.0.0.1)", c_telemetry_off), ("악성 값(태그·수식·특수문자) 방어", c_hostile_values),
    ("통계 하나가 고장 나도 나머지는 동작", c_isolation), ("대용량 성능(20만 행)", c_performance),
    ("구조 요약 도구가 값을 출력하지 않음", c_structure_no_values),
    ("프로토타입 기능이 prototype/ 한 곳에만 있음", c_prototype_isolated),
    ("윈도우 .bat 안전 (echo 리다이렉션, 줄바꿈)", c_bat_safe),
    ("exe 런처가 app 의 라이브러리를 모두 담음", c_launcher_imports),
    ("프로그램 폴더에 데이터 파일 없음 + .gitignore", c_no_data_files),
    ("구조 복제본: 원본 정보 누출 없음", c_replica_no_leak), ("구조 복제본: 읽기 결과 모양이 원본과 같음", c_replica_structure),
    ("구조 복제본: 성능", c_replica_perf),
    ("사이드바를 접어도 다시 펼칠 수 있음(CSS)", c_sidebar_toggle_css),
    ("통계표 모드: 가상 표 23가지 모양 읽기(여러 줄 머리글·반복 블록·비율 포함)", c_table_layouts), ("통계표 모드: 악성 항목 이름 방어", c_table_hostile),
    ("통계표 모드: 대용량(3,000항목) 성능", c_table_perf),
    ("통계표 설정 화면이 자동 추천 설정을 기본값으로 씀", c_panel_uses_suggested_spec),
    ("병합 칸을 엑셀의 진짜 병합 범위로 채움", c_merged_grid),
    ("통계표 모드의 모든 읽기 경로가 병합 범위를 씀", c_table_paths_use_merged_grid), ("core/ 에 화면 코드가 없음", c_core_no_streamlit),
    ("차트 이미지(PNG) 저장 설정·끄기 스위치", c_chart_export),
    ("모든 차트가 charts._show 한 곳으로만 나감", c_chart_single_exit),
]
for n, f in GENERIC:
    run(n, f)
for n, f in hooks.check_list():
    run("[프로토타입] " + n, f)

failed = [r for r in results if not r[0]]
print("\n" + ("모든 점검을 통과했습니다." if not failed else f"{len(failed)}개 항목에 문제가 있습니다. 위의 [실패] 줄을 확인하세요."))
sys.exit(1 if failed else 0)
