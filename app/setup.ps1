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
# download once; with $sha256 the file must match the publisher's checksum or it is deleted and setup stops
function Get-File($url, $out, $sha256) {
  if (-not (Test-Path $out)) { Write-Host "  downloading $url"; Invoke-WebRequest -UseBasicParsing $url -OutFile $out }
  if ($sha256) {
    $h = (Get-FileHash $out -Algorithm SHA256).Hash.ToLower()
    if ($h -ne $sha256.ToLower()) { Remove-Item $out -Force; throw "Checksum mismatch for $url (got $h). The download was deleted; run Setup again." }
    Write-Host "  checksum ok"
  }
}
$HyperframesVersion = "0.9.43"   # pinned: update deliberately, after testing

if (-not (Have "winget")) {
  Write-Host "winget (App Installer) is missing. Install 'App Installer' from the Microsoft Store, then run Setup.bat again." -ForegroundColor Red
  exit 1
}

Step "0/7 Portable Python for the app"
$py = Join-Path $App "python\python.exe"
if (Test-Path $py) { Write-Host "  ok $py" }
else {
  $zip = Join-Path $env:TEMP "python-3.12.10-embed-amd64.zip"
  Get-File "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip" $zip "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"   # SHA-256 from python.org's sigstore bundle
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
Push-Location (Join-Path $Root "workspace"); & $npx --yes "hyperframes@$HyperframesVersion" skills update; Pop-Location

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
    # AMD / Intel (no CUDA): the OpenBLAS CPU build is the fastest whisper.cpp for Windows x64
    if (-not $asset) { $asset = $assets | Where-Object { $_.name -eq "whisper-blas-bin-x64.zip" } | Select-Object -First 1 }
    if (-not $asset) { $asset = $assets | Where-Object { $_.name -eq "whisper-bin-x64.zip" } | Select-Object -First 1 }
    $zip = Join-Path $env:TEMP $asset.name; Get-File $asset.browser_download_url $zip ($asset.digest -replace "^sha256:", "")   # GitHub's published digest
    New-Item -ItemType Directory -Force (Join-Path $WD "Release") | Out-Null
    Expand-Archive $zip -DestinationPath $WD -Force
    $cli = Get-ChildItem $WD -Recurse -Filter whisper-cli.exe | Select-Object -First 1
    if ($cli -and $cli.DirectoryName -ne (Join-Path $WD "Release")) { Copy-Item "$($cli.DirectoryName)\*" (Join-Path $WD "Release") -Recurse -Force }
  } else { Write-Host "  ok whisper.cpp" }
  [Environment]::SetEnvironmentVariable("HYPERFRAMES_WHISPER_PATH", (Join-Path $WD "Release\whisper-cli.exe"), "User")
  $WM = Join-Path $HOME ".cache\hyperframes\whisper\models"; New-Item -ItemType Directory -Force $WM | Out-Null
  Get-File "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin" (Join-Path $WM "ggml-large-v3-turbo.bin") "1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69"
  Get-File "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin" (Join-Path $WM "ggml-small.bin") "1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b"
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

Step "GPU check (NVIDIA / AMD / Intel)"
# tests the hardware video encoders, the Blender render device and the whisper build; prints a driver link if one is too old
& (Join-Path $App "python\python.exe") (Join-Path $App "gpu.py") --force

Write-Host "`nSetup finished." -ForegroundColor Green
