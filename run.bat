@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" (
    echo =======================================================
    echo   Stack Cuts - Stream Highlight ^& Vertical Reel Studio
    echo =======================================================
    echo.
    echo Usage:
    echo   run.bat "<youtube_stream_url>" [options]
    echo.
    echo Examples:
    echo   run.bat "https://www.youtube.com/live/..." --layout stacked --max-clips 10
    echo   run.bat "https://www.youtube.com/live/..." --layout fill --minutes 60
    echo.
    echo Running automated selftest...
    python cli.py selftest
    pause
    exit /b
)

python cli.py run %*
pause
