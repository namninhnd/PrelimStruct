@echo off
echo Launching OpenCode in WSL...
echo.

:: Convert Windows path to WSL path
set "WIN_PATH=%CD%"
set "WSL_PATH=%WIN_PATH:C:=/mnt/c%"
set "WSL_PATH=%WSL_PATH:\=/%"
set "WSL_PATH=%WSL_PATH: =\ %"

:: Launch WSL with opencode in current directory
wsl -d Ubuntu -e bash -c "cd '%WSL_PATH%' && opencode"

:: Pause if opencode exits with error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo OpenCode exited with error code %ERRORLEVEL%
    pause
)
