param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$taskPrincipal = [Security.Principal.WindowsPrincipal]::new($taskIdentity)
if (-not $taskPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run mo_khoa_ket_noi.bat as administrator only if you want to allow LAN access.'
}
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run setup.bat first.' }
Push-Location -LiteralPath $taskRoot
try {
    $taskPortOutput = & $taskPython -c 'from config import settings; print(settings.PORT)'
    if ($LASTEXITCODE -ne 0) { throw 'Invalid application configuration.' }
    $taskPort = [int]$taskPortOutput
    if ($taskPort -lt 1 -or $taskPort -gt 65535) { throw 'Invalid port.' }
    Get-NetFirewallRule -DisplayName 'Q Smart TV Server' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -DisplayName 'Q Smart TV Server' -Direction Inbound -Action Allow -Protocol TCP -LocalPort $taskPort -Profile Private -RemoteAddress LocalSubnet | Out-Null
    Write-Host "Allowed Q Smart TV TCP $taskPort on Private networks and LocalSubnet only."
    Write-Host 'No Windows network category was changed.'
} finally { Pop-Location }
