@echo off
cd /d "%~dp0"
title Woori Real Estate System Launcher

echo ===================================================
echo [1/4] Pulling latest code and data from GitHub...
echo ===================================================
git pull origin main

echo ===================================================
echo [2/4] Cleaning up ports 8501 and 8502...
echo ===================================================
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8501 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8502 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 /nobreak >nul

echo ===================================================
echo [3/4] Starting Main CRM (8501) and Sub Studio (8502)...
echo ===================================================
start "Main_CRM_8501" cmd /k "python -m streamlit run app.py --server.port 8501 --server.headless true"
start "Sub_Studio_8502" cmd /k "python -m streamlit run sub_app.py --server.port 8502 --server.headless true"

echo ===================================================
echo [4/4] Opening web browsers in 3 seconds...
echo ===================================================
timeout /t 3 /nobreak >nul
start http://localhost:8501
start http://localhost:8502

exit