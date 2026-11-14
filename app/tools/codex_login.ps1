# Codex sign-in for this PC (AI Video Editor / Review Room).
# The API key goes straight from a hidden prompt to Codex's stdin, never to a file or command argument.
param([ValidateSet('status', 'login', 'apikey', 'test', 'logout', 'install')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Python = Join-Path $Root 'app\python\python.exe'
if (-not (Test-Path $Python)) {
    Write-Host '  Run Setup.bat first to install the portable Python.'
    exit 1
}
try {
    $Info = (& $Python (Join-Path $PSScriptRoot 'codex_path.py') --status) | ConvertFrom-Json
    if ($Action -eq 'install') {
        Write-Host '  [1] Install or update the Codex app (Microsoft Store / winget)'
        Write-Host '  [2] Install or update the npm CLI (Node.js required)'
        Write-Host '  [0] Back (or just Enter)'
        $Choice = Read-Host '  Choose 1-2'
        if ($Choice -eq '1') {
            if (Get-Command winget -ErrorAction SilentlyContinue) {
                # Resolve the Store listing by name; never pin a versioned WindowsApps path.
                & winget install --name Codex --source msstore --accept-source-agreements --accept-package-agreements
                if ($LASTEXITCODE -ne 0) {
                    Write-Host '  Open Microsoft Store, search for OpenAI Codex, then Install or Update.'
                    Start-Process 'ms-windows-store://search/?query=OpenAI%20Codex'
                }
            } else { Start-Process 'ms-windows-store://search/?query=OpenAI%20Codex' }
        } elseif ($Choice -eq '2') {
            if (Get-Command npm.cmd -ErrorAction SilentlyContinue) { & npm.cmd i -g '@openai/codex@latest' }
            else { Write-Host '  Install Node.js first: winget install OpenJS.NodeJS.LTS' }
        }
        exit
    }
    if (-not $Info.path) {
        Write-Host '  Codex CLI not found. Choose [5] to install the Codex app or npm CLI.'
        exit 1
    }
    $Codex = $Info.path
    if ($Action -eq 'status') {
        Write-Host "  Codex CLI: $($Info.version)"
        Write-Host "  CLI path: $Codex"
        if ($Info.signed_in) {
            Write-Host "  Status: signed in ($($Info.method))"
            if ($Info.email) { Write-Host "  Account: $($Info.email)" }
            if ($Info.plan) { Write-Host "  Plan: $($Info.plan)" }
        } else { Write-Host '  Status: not signed in' }
    } elseif ($Action -eq 'login') {
        & $Codex login
    } elseif ($Action -eq 'logout') {
        & $Codex logout
    } elseif ($Action -eq 'apikey') {
        $Secret = Read-Host '  Paste the API key (it stays hidden) and press Enter' -AsSecureString
        $Ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secret)
        try {
            $Key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Ptr)
            if ($Key) {
                # Capture output so even an unexpected CLI error cannot echo the key.
                $ErrorActionPreference = 'Continue'
                $Result = $Key | & $Codex login --with-api-key 2>&1
                $LoginCode = $LASTEXITCODE
                $ErrorActionPreference = 'Stop'
                if ($LoginCode -eq 0) { Write-Host '  Signed in with an API key.' }
                else { Write-Host '  Sign-in failed. Check the key and try again.' }
            }
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Ptr)
            $Key = $null; $Result = $null; $Secret.Dispose()
        }
    } elseif ($Action -eq 'test') {
        $Settings = Get-Content (Join-Path $Root 'app\data\settings.default.json') -Raw | ConvertFrom-Json
        $Model = $Settings.codex_model
        if (Test-Path (Join-Path $Root 'settings.json')) {
            $Local = Get-Content (Join-Path $Root 'settings.json') -Raw | ConvertFrom-Json
            if ($Local.codex_model) { $Model = $Local.codex_model }
        }
        Write-Host "  Testing $Model with a tiny read-only request ..."
        Push-Location $Root
        try {
            $ErrorActionPreference = 'Continue'
            $Output = 'Reply with exactly the word: ok. Do not use tools.' | & $Codex exec --json --skip-git-repo-check -m $Model -c 'model_reasoning_effort=low' -s read-only - 2>&1
            $Code = $LASTEXITCODE
            $ErrorActionPreference = 'Stop'
        } finally { Pop-Location }
        $Reply = ''; $Failure = ''
        foreach ($Line in $Output) {
            try { $Event = "$Line" | ConvertFrom-Json } catch { continue }
            if ($Event.type -eq 'item.completed' -and $Event.item.type -eq 'agent_message') { $Reply = $Event.item.text }
            if ($Event.type -in @('turn.failed', 'error')) {
                $Failure = if ($Event.error.message) { $Event.error.message } else { $Event.message }
            }
        }
        if ($Code -eq 0 -and $Reply.Trim() -match '^ok[.!]?$') { Write-Host '  OK. Review Room can now send edits to Codex.' }
        else {
            Write-Host "  Test failed: $Failure"
            if (-not $Failure) { Write-Host '  No OK reply. Check your sign-in, connection and configured model.' }
            if (($Output -join ' ') -match '(?i)model' -and ($Output -join ' ') -match '(?i)not supported|unsupported|does not exist|not found|not available|model_not_found|do not have access') {
                Write-Host '  The model was rejected. Try updating Codex with option [5], then test again.'
            }
        }
    }
} catch {
    # Avoid dumping arbitrary CLI output or credentials in a PowerShell error report.
    Write-Host '  Codex could not complete this step. Check the CLI installation and try again.'
    exit 1
}
