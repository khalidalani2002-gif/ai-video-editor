# Creates the "Review Room App" shortcut on the desktop (Setup.bat runs this).
$app = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $app
$lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "Review Room App.lnk"
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($lnk)
$s.TargetPath = "$env:WINDIR\System32\wscript.exe"
$s.Arguments = '"' + (Join-Path $root "Start Review Room.vbs") + '"'
$s.WorkingDirectory = $root
$s.IconLocation = (Join-Path $app "icon.ico") + ",0"
$s.Description = "Review videos and let Claude edit them"
$s.Save()
Write-Output "  Desktop shortcut: $lnk"
