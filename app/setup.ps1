# Review Room setup for a new Windows PC (Setup.bat runs this). Safe to run again: every step checks what is already there.
#   -Speech   also install speech features (whisper.cpp + the large-v3-turbo model, about 1.7 GB):
#             "Speak" notes and word transcripts. Without it the app works; those two buttons are disabled.
#   -Blender  also install Blender (about 400 MB): 3D for the "Heavy edit" level.
#   -Mixkit   also download the Mixkit music, sound effects and footage of the Default assets from Mixkit (about 2.6 GB).
param([switch]$Speech, [switch]$Blender, [switch]$Mixkit)
$ErrorActionPreference = "Continue"
$App = $PSScriptRoot
$Root = Split-Path -Parent $App
function Step($m) { Write-Host "`n== $m" -ForegroundColor Cyan }
function Have($c) { [bool](Get-Command $c -ErrorAction SilentlyContinue) }
function RefreshPath { $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User") }
function Get-File($url, $out) { if (-not (Test-Path $out)) { Write-Host "  downloading $url"; Invoke-WebRequest -UseBasicParsing $url -OutFile $out } }

if (-not (Have "winget")) {
  Write-Host "winget (App Installer) is missing. Install 'App Installer' from the Microsoft Store, then run Setup.bat again." -ForegroundColor Red
  exit 1
}

Step "0/7 Portable Python for the app"
$py = Join-Path $App "python\python.exe"
if (Test-Path $py) { Write-Host "  ok $py" }
else {
  $zip = Join-Path $env:TEMP "python-3.12.10-embed-amd64.zip"
  Get-File "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip" $zip
  Expand-Archive $zip -DestinationPath (Join-Path $App "python") -Force
  Write-Host "  installed $py"
}

Step "1/7 ffmpeg and Node.js"
foreach ($p in @(@("ffmpeg", "Gyan.FFmpeg"), @("node", "OpenJS.NodeJS.LTS"))) {
  if (Have $p[0]) { Write-Host "  ok $($p[0])" }
  else { winget install --id $p[1] -e --accept-source-agreements --accept-package-agreements; RefreshPath }
}

Step "2/7 Claude Code (command line)"
$claude = Join-Path $env:APPDATA "npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"
if (Test-Path $claude) { Write-Host "  ok $(& $claude --version)" }
else {
  $npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
  if (-not $npm) { $npm = Join-Path $env:ProgramFiles "nodejs\npm.cmd" }
  & $npm install -g @anthropic-ai/claude-code
  if (Test-Path $claude) { Write-Host "  installed $(& $claude --version)" } else { Write-Host "  Claude Code did not install; see the messages above." -ForegroundColor Red }
}

Step "3/7 Video skills for Claude and Codex (HyperFrames)"
$npx = (Get-Command npx.cmd -ErrorAction SilentlyContinue).Source
if (-not $npx) { $npx = Join-Path $env:ProgramFiles "nodejs
px.cmd" }
Push-Location (Join-Path $Root "workspace"); & $npx --yes hyperframes@latest skills update; Pop-Location

Step "4/7 Speech (optional: Speak notes and transcripts)"
if (-not $Speech) { Write-Host "  skipped (run Setup.bat again and answer Y to add it)" }
else {
  $WD = Join-Path $env:LOCALAPPDATA "whisper.cpp-cuda"
  if (-not (Test-Path (Join-Path $WD "Release\whisper-cli.exe"))) {
    $nvidia = [bool](Get-Command nvidia-smi -ErrorAction SilentlyContinue)
    $rel = Invoke-RestMethod "https://api.github.com/repos/ggml-org/whisper.cpp/releases?per_page=10"
    $assets = $rel | ForEach-Object { $_.assets }
    $asset = $null
    if ($nvidia) { $asset = $assets | Where-Object { $_.name -match "win-cuda-12.*x64\.zip|cublas-12.*x64\.zip" } | Select-Object -First 1 }
    if (-not $asset) { $asset = $assets | Where-Object { $_.name -eq "whisper-bin-x64.zip" } | Select-Object -First 1 }
    $zip = Join-Path $env:TEMP $asset.name; Get-File $asset.browser_download_url $zip
    New-Item -ItemType Directory -Force (Join-Path $WD "Release") | Out-Null
    Expand-Archive $zip -DestinationPath $WD -Force
    $cli = Get-ChildItem $WD -Recurse -Filter whisper-cli.exe | Select-Object -First 1
    if ($cli -and $cli.DirectoryName -ne (Join-Path $WD "Release")) { Copy-Item "$($cli.DirectoryName)\*" (Join-Path $WD "Release") -Recurse -Force }
  } else { Write-Host "  ok whisper.cpp" }
  [Environment]::SetEnvironmentVariable("HYPERFRAMES_WHISPER_PATH", (Join-Path $WD "Release\whisper-cli.exe"), "User")
  $WM = Join-Path $HOME ".cache\hyperframes\whisper\models"; New-Item -ItemType Directory -Force $WM | Out-Null
  Get-File "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin" (Join-Path $WM "ggml-large-v3-turbo.bin")
  Get-File "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin" (Join-Path $WM "ggml-small.bin")
  Write-Host "  speech ready"
}

Step "5/7 Blender (optional: 3D in heavy edits)"
$bl = Get-ChildItem (Join-Path $env:ProgramFiles "Blender Foundation") -Recurse -Filter blender.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if ($bl) { Write-Host "  ok $($bl.FullName)" }
elseif ($Blender) { winget install --id BlenderFoundation.Blender -e --accept-source-agreements --accept-package-agreements }
else { Write-Host "  skipped (run Setup.bat again and answer Y to add it)" }

Step "6/7 Mixkit assets (optional: music, sound effects, footage from Mixkit)"
if ($Mixkit) { & (Join-Path $App "python\python.exe") (Join-Path $App "tools\fetch_mixkit_assets.py") }
else { Write-Host "  skipped (run Setup.bat again and answer Y to add them)" }

Step "7/7 Desktop shortcut"
& (Join-Path $App "make_shortcut.ps1")

Write-Host "`nSetup finished." -ForegroundColor Green
