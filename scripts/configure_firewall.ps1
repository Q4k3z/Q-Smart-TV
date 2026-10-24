param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run setup.bat first.' }
Push-Location -LiteralPath $taskRoot
try {
    $taskPortOutput = & $taskPython -c 'from config import settings; print(settings.PORT)'
    if ($LASTEXITCODE -ne 0) { throw 'Invalid application configuration.' }
    $taskPort = [int]$taskPortOutput
    if ($taskPort -lt 1 -or $taskPort -gt 65535) { throw 'Invalid port.' }

    $taskIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $taskPrincipal = [Security.Principal.WindowsPrincipal]::new($taskIdentity)
    if (-not $taskPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Start-Process netsh -ArgumentList "advfirewall firewall delete rule name=`"Q Smart TV Server`"" -Verb RunAs -Wait
        Start-Process netsh -ArgumentList "advfirewall firewall add rule name=`"Q Smart TV Server`" dir=in action=allow protocol=TCP localport=$taskPort profile=any" -Verb RunAs -Wait
    } else {
        Get-NetFirewallRule -DisplayName 'Q Smart TV Server' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
        New-NetFirewallRule -DisplayName 'Q Smart TV Server' -Direction Inbound -Action Allow -Protocol TCP -LocalPort $taskPort -Profile Any -RemoteAddress LocalSubnet | Out-Null
    }
    Write-Host "Allowed Q Smart TV TCP $taskPort on LocalSubnet (All Profiles)."
} finally { Pop-Location }
