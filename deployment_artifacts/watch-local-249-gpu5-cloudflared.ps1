[CmdletBinding()]
param(
    [int]$LocalForwardPort = 18766,
    [int]$CheckIntervalSeconds = 30,
    [switch]$RunOnce
)

$ErrorActionPreference = 'Stop'

$deploymentDirectory = Split-Path -Parent $PSCommandPath
$projectRoot = Split-Path -Parent $deploymentDirectory
$runtimeDirectory = Join-Path $projectRoot 'tmp'
$startScript = Join-Path $deploymentDirectory 'start-local-249-gpu5-decoder-tunnel.ps1'
$watchdogLog = Join-Path $runtimeDirectory 'cloudflared-249-gpu5-watchdog.log'
$currentUrlPath = Join-Path $runtimeDirectory 'current-gpu5-decode-url.json'
$publishScript = Join-Path $deploymentDirectory 'publish-current-gpu5-config.ps1'

if (-not (Test-Path -LiteralPath $runtimeDirectory)) {
    New-Item -ItemType Directory -Path $runtimeDirectory | Out-Null
}
if (-not (Test-Path -LiteralPath $startScript -PathType Leaf)) {
    throw "GPU5 tunnel launcher not found: $startScript"
}

function Publish-CurrentState {
    if ([string]::IsNullOrWhiteSpace($env:DECODER_CONFIG_UPDATE_URL)) { return $true }
    if (-not (Test-Path -LiteralPath $publishScript -PathType Leaf)) {
        Write-WatchdogLog "Publisher not found: $publishScript"
        return $false
    }
    try {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $publishScript | Out-Null
        Write-WatchdogLog 'Published current decoder configuration to CloudBase.'
        return $true
    }
    catch {
        Write-WatchdogLog "CloudBase configuration publish failed: $($_.Exception.Message)"
        return $false
    }
}

function Write-WatchdogLog {
    param([Parameter(Mandatory = $true)][string]$Message)
    Add-Content -LiteralPath $watchdogLog -Encoding UTF8 -Value (
        '{0} {1}' -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fffK'), $Message
    )
}

function Get-TunnelProcesses {
    return @(
        Get-CimInstance Win32_Process -Filter "Name = 'cloudflared.exe'" |
            Where-Object {
                $_.CommandLine -and $_.CommandLine -like "*127.0.0.1:$LocalForwardPort*"
            }
    )
}

function Test-StateFile {
    if (-not (Test-Path -LiteralPath $currentUrlPath -PathType Leaf)) { return $null }
    try {
        $state = Get-Content -LiteralPath $currentUrlPath -Raw | ConvertFrom-Json -ErrorAction Stop
        if ($state.decode_url -notlike 'https://*.trycloudflare.com/decode') { return $null }
        try {
            $health = Invoke-RestMethod -Uri $state.health_url -Method Get -TimeoutSec 12
            if ($health.status -eq 'ok' -and $health.model -eq 'trustmark-q-57bit-real18-step113100-locator5-perspective-rotation' -and $health.device -eq 'cuda:0') {
                return $state
            }
        }
        catch { return $null }
    }
    catch { return $null }
    return $null
}

function Restore-Tunnel {
    $currentState = Test-StateFile
    if ($null -ne $currentState) {
        Write-WatchdogLog "Current tunnel healthy: $($currentState.decode_url)"
        return $true
    }
    $hadProcess = (Get-TunnelProcesses).Count -gt 0
    try {
        # The launcher verifies the exact remote health contract. If an existing
        # quick tunnel is bad, it replaces it; otherwise it keeps that hostname.
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $startScript | Out-Null
        if (-not (Test-StateFile)) {
            throw 'Tunnel launcher completed without publishing a current URL state file.'
        }
        if (-not (Publish-CurrentState)) { throw 'Tunnel is healthy but CloudBase configuration publish failed.' }
        $state = Get-Content -LiteralPath $currentUrlPath -Raw | ConvertFrom-Json
        $action = if ($hadProcess) { 'verified or recovered' } else { 'started' }
        Write-WatchdogLog "Tunnel ${action}: $($state.decode_url)"
        return $true
    }
    catch {
        Write-WatchdogLog "Tunnel recovery failed: $($_.Exception.Message)"
        return $false
    }
}

$failureCount = 0
$unhealthyChecks = 0
Write-WatchdogLog "Cloudflare watchdog started for local port $LocalForwardPort."
do {
    $state = Test-StateFile
    if ($null -ne $state) {
        $unhealthyChecks = 0
        $failureCount = 0
        Write-WatchdogLog "Current tunnel healthy: $($state.decode_url)"
    }
    else {
        $unhealthyChecks++
        if ($unhealthyChecks -lt 3) {
            Write-WatchdogLog "Public tunnel health check failed ($unhealthyChecks/3); waiting before recovery."
        }
        else {
            $ok = Restore-Tunnel
            if ($ok) { $failureCount = 0; $unhealthyChecks = 0 } else { $failureCount++ }
        }
    }
    if ($RunOnce) { break }
    $backoffSeconds = [Math]::Min(120, $CheckIntervalSeconds * [Math]::Pow(2, [Math]::Min($failureCount, 2)))
    Start-Sleep -Seconds ([int]$backoffSeconds)
} while ($true)
