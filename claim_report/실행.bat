@echo off
cd /d "%~dp0"
echo Installing packages (first run may take a minute)...
python -m pip install -r requirements.txt --quiet
echo Starting... a browser window will open. Close this window to stop.
python -m streamlit run app.py
pause
