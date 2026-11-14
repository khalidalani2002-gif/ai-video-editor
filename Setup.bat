@echo off
:: Review Room: set up this PC (ffmpeg, Node.js, Claude Code, optional speech, desktop shortcut), then sign in to Claude.
setlocal EnableExtensions
title Review Room setup
cd /d "%~dp0"
echo.
echo   Review Room setup
echo   =================
echo   Installs what the app needs on this PC: ffmpeg, Node.js and Claude Code (free downloads),
echo   and puts a "Review Room App" shortcut on the desktop.
echo.
set "SP=" & set "BL=" & set "ARGS="
set /p "SP=  Also install speech (Speak notes + transcripts, about 1.7 GB download)? [Y/N]: "
set /p "BL=  Also install Blender (3D for heavy edits, about 400 MB)? [Y/N]: "
set "MK="
set /p "MK=  Also download the Mixkit music, sound effects and footage (about 2.6 GB)? [Y/N]: "
if /i "%SP%"=="Y" set "ARGS=%ARGS% -Speech"
if /i "%BL%"=="Y" set "ARGS=%ARGS% -Blender"
if /i "%MK%"=="Y" set "ARGS=%ARGS% -Mixkit"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0app\setup.ps1" %ARGS%
echo.
echo   Next: sign in to Claude.
pause
call "%~dp0Claude Login.bat"
