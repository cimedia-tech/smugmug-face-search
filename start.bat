@echo off
title SmugMug Face Search — Indexer

echo SmugMug Face Search — Local Indexer
echo ======================================
echo.
echo This runs face detection locally and writes results to Supabase.
echo The web app is live at https://smugmug-face-search.vercel.app
echo.

:: Check for .env in cli/
if not exist "H:\antigravity\smugmug-face-search\cli\.env" (
    echo ERROR: cli\.env not found.
    echo Copy cli\.env.example to cli\.env and fill in your keys.
    pause
    exit /b 1
)

:: Show menu
echo What would you like to do?
echo.
echo   [1] Index photos   (run cli\index.py)
echo   [2] Cluster faces  (run cli\cluster.py)
echo   [3] Both           (index then cluster)
echo.
set /p choice="Enter 1, 2, or 3: "

if "%choice%"=="1" goto index
if "%choice%"=="2" goto cluster
if "%choice%"=="3" goto both
echo Invalid choice.
pause
exit /b 1

:index
echo.
echo Starting indexer...
echo First queue a job at https://smugmug-face-search.vercel.app, then this will pick it up.
echo.
cd /d H:\antigravity\smugmug-face-search\cli
python index.py
pause
exit /b 0

:cluster
echo.
echo Starting clusterer...
cd /d H:\antigravity\smugmug-face-search\cli
python cluster.py
pause
exit /b 0

:both
echo.
echo Starting indexer...
cd /d H:\antigravity\smugmug-face-search\cli
python index.py
echo.
echo Indexing complete. Starting clusterer...
python cluster.py
pause
exit /b 0
