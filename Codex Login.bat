@echo off
:: Codex sign-in for this PC (AI Video Editor / Review Room).
:: Uses the newest CLI from settings, the Codex app, sandbox-bin or PATH/npm.
:: Sign-in stays in your Windows user account, never in this folder.
setlocal EnableExtensions
title Codex sign-in
cd /d "%~dp0"
set "HELPER=%~dp0app\tools\codex_login.ps1"

echo.
echo   Codex sign-in for this PC
echo   =========================
echo.

:: ---- show the sign-in and CLI status without printing any token or key
:menu
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%HELPER%" -Action status
echo.
echo   [1] Sign in with ChatGPT           (opens the browser on this PC)
echo   [2] Sign in with an API key        (hidden prompt)
echo   [3] Test the sign-in
echo   [4] Sign out of this PC
echo   [5] Install or update the Codex CLI
echo   [0] Exit  (or just Enter)
echo.
set "CH="
set /p "CH=  Choose 1-5: "
if "%CH%"=="1" goto :login
if "%CH%"=="2" goto :apikey
if "%CH%"=="3" goto :test
if "%CH%"=="4" goto :logout
if "%CH%"=="5" goto :install
if "%CH%"=="0" exit /b 0
if not defined CH exit /b 0
goto :menu

:: ---- [1] the normal browser sign-in with ChatGPT
:login
powershell -NoProfile -ExecutionPolicy Bypass -File "%HELPER%" -Action login
goto :done

:: ---- [2] pass a hidden API key straight to Codex's stdin
:apikey
powershell -NoProfile -ExecutionPolicy Bypass -File "%HELPER%" -Action apikey
goto :done

:: ---- [3] a tiny read-only request proves the sign-in works
:test
powershell -NoProfile -ExecutionPolicy Bypass -File "%HELPER%" -Action test
goto :done

:: ---- [4] sign out
:logout
powershell -NoProfile -ExecutionPolicy Bypass -File "%HELPER%" -Action logout
goto :done

:: ---- [5] install or update, then find the newest CLI again
:install
powershell -NoProfile -ExecutionPolicy Bypass -File "%HELPER%" -Action install
:done
echo.
echo   Review Room picks up the new sign-in the next time you open it or send a job.
pause
goto :menu
