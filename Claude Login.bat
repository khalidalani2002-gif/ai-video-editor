@echo off
:: Claude Code sign-in for this PC (AI Video Editor / Review Room).
:: Sign in WITHOUT a browser on this PC: make a token once on any computer that has Claude Code
:: (`claude setup-token`, valid for about a year), then paste it here. The token is kept in your Windows user
:: account (environment variable CLAUDE_CODE_OAUTH_TOKEN), never in this folder.
setlocal EnableExtensions
title Claude Code sign-in
set "CLAUDE=%APPDATA%\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"

echo.
echo   Claude Code sign-in for this PC
echo   ===============================
echo.

:: ---- 1. make sure the Claude Code CLI is installed
if exist "%CLAUDE%" goto :menu
where npm >nul 2>nul
if errorlevel 1 (
  echo   Node.js is not installed. Install it first, then run this file again:
  echo       winget install OpenJS.NodeJS.LTS
  echo.
  pause & exit /b 1
)
echo   Installing Claude Code ...
call npm install -g @anthropic-ai/claude-code
if not exist "%CLAUDE%" (
  echo   The install failed. See the messages above.
  pause & exit /b 1
)

:menu
echo.
call :showstatus
echo.
echo   [1] Paste a sign-in token          (no browser on this PC)
echo   [2] Normal sign-in                 (opens the browser on this PC)
echo   [3] Make a token on this PC        (to sign in your OTHER PCs; opens the browser once)
echo   [4] Test the sign-in
echo   [5] Sign out of this PC
echo   [0] Exit  (or just Enter)
echo.
set "CH="
set /p "CH=  Choose 1-5: "
if "%CH%"=="1" goto :paste
if "%CH%"=="2" goto :login
if "%CH%"=="3" goto :maketoken
if "%CH%"=="4" goto :test
if "%CH%"=="5" goto :logout
if "%CH%"=="0" exit /b 0
if not defined CH exit /b 0
goto :menu

:: ---- [1] paste a token made with `claude setup-token` on any computer
:paste
echo.
echo   On any computer that has Claude Code (and a browser), run this once:
echo       claude setup-token
echo   Sign in there. It prints a token that starts with  sk-ant-oat
echo.
set "TOKEN="
for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "$s = Read-Host '  Paste the token (it stays hidden) and press Enter' -AsSecureString; [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))"`) do set "TOKEN=%%T"
if not defined TOKEN ( echo   Nothing pasted. & goto :menu )
if /i not "%TOKEN:~0,7%"=="sk-ant-" ( echo   That does not look like a Claude token ^(it should start with sk-ant-^). & set "TOKEN=" & goto :menu )
setx CLAUDE_CODE_OAUTH_TOKEN "%TOKEN%" >nul
set "CLAUDE_CODE_OAUTH_TOKEN=%TOKEN%"
set "TOKEN="
echo   Saved for your Windows user account.
goto :test

:: ---- [2] the normal browser sign-in
:login
echo.
"%CLAUDE%" auth login
goto :test

:: ---- [3] make a long-lived token here, for your other PCs
:maketoken
echo.
echo   This opens the browser once. Copy the token it prints and keep it private:
echo   anyone who has it can use your Claude plan. Paste it into option [1] on the other PC.
echo.
"%CLAUDE%" setup-token
echo.
pause
goto :menu

:: ---- [4] a tiny real request proves the sign-in works (auth status alone trusts any token)
:test
echo.
echo   Testing the sign-in with a tiny request ...
set "OUT="
for /f "usebackq delims=" %%L in (`" "%CLAUDE%" -p "Reply with exactly the word: ok" --max-turns 1 ^<nul 2^>^&1 "`) do set "OUT=%%L"
echo   Claude replied: %OUT%
echo %OUT% | findstr /i /c:"ok" >nul && (
  echo.
  echo   Signed in. Review Room can now send edits to Claude.
  echo   If Review Room is open, press Quit in it and open it again so it picks up the sign-in.
) || (
  echo.
  echo   The sign-in did not work. Try option [1] again with a fresh token, or option [2].
)
echo.
pause
goto :menu

:: ---- [5] sign out
:logout
echo.
reg delete "HKCU\Environment" /v CLAUDE_CODE_OAUTH_TOKEN /f >nul 2>nul
set "CLAUDE_CODE_OAUTH_TOKEN="
"%CLAUDE%" auth logout <nul >nul 2>nul
echo   Signed out of this PC (the saved token and the browser sign-in were removed).
echo.
pause
goto :menu

:showstatus
set "TOK=no"
reg query "HKCU\Environment" /v CLAUDE_CODE_OAUTH_TOKEN >nul 2>nul && set "TOK=yes"
for /f "usebackq delims=" %%V in (`" "%CLAUDE%" --version ^<nul 2^>nul "`) do echo   Claude Code: %%V
echo   Saved token on this PC: %TOK%
"%CLAUDE%" auth status <nul 2>nul | findstr /c:"\"loggedIn\": true" >nul && echo   Status: signed in || echo   Status: not signed in
exit /b 0
