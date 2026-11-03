@echo off
rem ============================================================
rem  Windows PC 에서 한 번 실행하면 dist\ClaimReport 폴더(실행 파일 포함)가 만들어집니다.
rem  필요한 것: 이 PC 에 Python 3.9 이상 + 인터넷(빌드할 때 한 번만)
rem ============================================================
setlocal
cd /d "%~dp0\.."
echo [1/4] Installing build tools (internet needed this one time)...
python -m pip install -r requirements.txt pyinstaller || goto :fail
echo [2/4] Building runtime (takes a few minutes)...
python -m PyInstaller --noconfirm --clean --onedir --name ClaimReport ^
  --collect-all streamlit --copy-metadata streamlit ^
  --collect-data plotly --collect-data reportlab --collect-data openpyxl ^
  --distpath dist --workpath build\work --specpath build ^
  packaging\launcher.py || goto :fail
echo [3/4] Copying app files (editable folder)...
robocopy . dist\ClaimReport\app /E /XD dist build .git .github packaging __pycache__ /XF *.pyc *.zip *.bat 실행방법.txt >nul
if errorlevel 8 goto :fail
echo [4/4] Copying helper files...
copy /Y packaging\dist_files\* dist\ClaimReport\ >nul
echo.
echo Done: dist\ClaimReport\ClaimReport.exe
echo Copy the whole dist\ClaimReport folder to the target PC.
if not defined CI pause
exit /b 0
:fail
echo.
echo BUILD FAILED. Check the messages above.
if not defined CI pause
exit /b 1
