@echo off
cd /d "%~dp0"
title Woori Real Estate Data Sync

echo ===================================================
echo Backing up today's work data to GitHub...
echo ===================================================
git add .
git commit -m "Sync work data from Windows PC"
git push origin main

echo ===================================================
echo [DONE] Backup completed successfully!
echo ===================================================
pause