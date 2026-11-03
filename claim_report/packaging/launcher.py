# -*- coding: utf-8 -*-
"""
exe 런처 — 파이썬과 라이브러리를 담은 실행 엔진입니다. 우리 프로그램 소스는 exe 옆의 app/ 폴더에 그대로 두고 불러옵니다.
(그래서 config.py / stats_config.py 를 메모장으로 고칠 수 있습니다. 고친 뒤에는 프로그램을 껐다 켜세요)

  ClaimReport.exe                 → 프로그램 실행 (브라우저가 자동으로 열립니다)
  ClaimReport.exe --check         → 점검 (점검.bat 과 같은 것)
  ClaimReport.exe --structure 파일 → 엑셀 구조 요약 (셀 값은 출력하지 않음)

※ 아래 import 목록은 'app/ 소스가 쓰는 라이브러리'를 exe 에 빠뜨리지 않고 담기 위한 것입니다.
   app 에서 새 라이브러리를 쓰게 되면 여기에도 추가하세요. (점검.bat 이 빠진 것을 알려줍니다)
"""
import os
import runpy
import socket
import sys
import threading
import time
import traceback
import webbrowser

# --- 라이브러리를 exe 에 담기 위한 import (사용하지 않아도 지우지 마세요) ---
import numpy  # noqa: F401
import openpyxl  # noqa: F401
import pandas  # noqa: F401
import plotly.graph_objects  # noqa: F401
import plotly.subplots  # noqa: F401
import reportlab.lib.pagesizes  # noqa: F401
import reportlab.pdfbase.ttfonts  # noqa: F401
import reportlab.platypus  # noqa: F401
import streamlit  # noqa: F401
import streamlit.web.cli as stcli

sys.dont_write_bytecode = True


def app_dir() -> str:
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(base, "app"), os.path.dirname(base)):
        if os.path.isfile(os.path.join(cand, "app.py")):
            return cand
    raise FileNotFoundError("app 폴더를 찾을 수 없습니다. ClaimReport.exe 와 같은 폴더에 app 폴더가 있어야 합니다.")


def free_port(start: int = 8501, tries: int = 30) -> int:
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            if s.connect_ex(("127.0.0.1", port)) != 0:      # 연결이 안 되면 비어 있는 포트
                return port
    raise RuntimeError("사용 가능한 포트를 찾지 못했습니다.")


def open_browser_when_ready(port: int):
    def _run():
        for _ in range(240):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
                webbrowser.open(f"http://localhost:{port}")
                return
            except OSError:
                time.sleep(0.5)
    threading.Thread(target=_run, daemon=True).start()


def run_server(d: str):
    port = free_port()
    print("=" * 60)
    print(" 심사청구 통계 프로그램")
    print(f" 잠시 후 브라우저가 열립니다.  주소: http://localhost:{port}")
    print(" 끄려면 이 창을 닫으세요. (설정을 고친 뒤에는 껐다가 다시 켜세요)")
    print("=" * 60)
    open_browser_when_ready(port)
    sys.argv = ["streamlit", "run", os.path.join(d, "app.py"),
                "--global.developmentMode=false", f"--server.port={port}", "--server.address=127.0.0.1", "--server.headless=true",
                "--server.fileWatcherType=none", "--browser.gatherUsageStats=false"]
    stcli.main()


def main():
    d = app_dir()
    os.chdir(d)                                  # .streamlit/config.toml(색 테마, 통계 전송 끄기)을 찾기 위해
    sys.path.insert(0, d)
    args = sys.argv[1:]
    if args[:1] == ["--check"]:
        sys.argv = [os.path.join(d, "tests", "run_checks.py")]
        runpy.run_path(sys.argv[0], run_name="__main__")
    elif args[:1] == ["--structure"]:
        sys.argv = [os.path.join(d, "structure_report.py")] + args[1:]
        runpy.run_path(sys.argv[0], run_name="__main__")
    else:
        run_server(d)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:                      # 점검/구조요약이 끝날 때의 정상 종료
        if len(sys.argv) > 0 and any(k in " ".join(sys.argv) for k in ("run_checks", "structure_report")):
            input("\n엔터를 누르면 창이 닫힙니다...")
        sys.exit(e.code)
    except Exception:                            # 창이 바로 사라지면 원인을 볼 수 없으므로 멈춰서 보여줍니다
        traceback.print_exc()
        input("\n오류가 발생했습니다. 위 내용을 확인하세요. 엔터를 누르면 창이 닫힙니다...")
        sys.exit(1)
