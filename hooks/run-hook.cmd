@echo off
REM Run hook script for Deep Search plugin
REM Usage: run-hook.cmd <hook-name>

setlocal

set "SCRIPT_DIR=%~dp0"
set "PLUGIN_ROOT=%SCRIPT_DIR%.."

if "%1"=="" (
    echo Error: No hook name specified
    exit /b 1
)

set "HOOK_NAME=%1"

if "%HOOK_NAME%"=="session-start" (
    bash "%SCRIPT_DIR%session-start"
) else if "%HOOK_NAME%"=="session-start-codex" (
    bash "%SCRIPT_DIR%session-start-codex"
) else (
    echo Error: Unknown hook: %HOOK_NAME%
    exit /b 1
)

endlocal
