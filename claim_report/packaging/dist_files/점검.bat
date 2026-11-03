@echo off
cd /d "%~dp0"
chcp 65001 > nul
ClaimReport.exe --check
