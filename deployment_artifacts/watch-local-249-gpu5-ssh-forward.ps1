[CmdletBinding()]
param(
    [string]$ServerHost = '172.18.185.249',
    [string]$ServerUser = 'liyanlei',
    [string]$ServerKeyPath = "$env:USERPROFILE\.ssh\ceramic_249_ed25519",
    [int]$ServerDecoderPort = 28765,
    [int]$LocalForwardPort = 18766,
    [int]$CheckIntervalSeconds = 10,
    [switch]$RunOnce
)

$ErrorActionPreference = 'Stop'

$deploymentDirectory = Split-Path -Parent $PSCommandPath
$projectRoot = Split-Path -Parent $deploymentDirectory
$runtimeDirectory = Join-Path $projectRoot 'tmp'
$watchdogLog = Join-Path $runtimeDirectory 'ssh-249-gpu5-watchdog.log'
$expectedModel = 'trustmark-q-57bit-real18-step113100-locator5-perspective-rotation'
$expectedCheckpointSha256 = '834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef'

if (-not (Test-Path -LiteralPath $runtimeDirectory)) {
    New-Item -ItemType Directory -Path $runtimeDirectory | Out-Null
}
if (-not (Test-Path -LiteralPath $ServerKeyPath -PathType Leaf)) {
    throw "249 SSH key not found: $ServerKeyPath"
}

function Write-WatchdogLog {
    param([Parameter(Mandatory = $true)][string]$Message)

    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fffK'), $Message
    Add-Content -LiteralPath $watchdogLog -Value $line -Encoding UTF8
}

function Get-ForwardListener {
    return Get-NetTCPConnection -LocalPort $LocalForwardPort -State Listen `
        -ErrorAction SilentlyContinue | Select-Object -First 1
}

function Test-ExpectedHealth {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$LocalForwardPort/healthz" `
            -Method Get -TimeoutSec 5
    }
    catch { return $false }

    return (
        $health.status -eq 'ok' -and
        $health.model -eq $expectedModel -and
        $health.payload_bits -eq 57 -and
        $health.checkpoint_sha256 -eq $expectedCheckpointSha256 -and
        $health.localization -eq 'outer-logo-contour+inner-square-perspective-fallback+quarter-turn-rotation-fallback' -and
        $health.localized_variants -eq 3 -and
        $health.perspective_variants -eq 12 -and
        $health.rotation_variants -eq 36 -and
        $health.device -eq 'cuda:0'
    )
}

function Remove-StaleSshListener {
    $listener = Get-ForwardListener
    if (-not $listener) { return $true }

    $owner = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    if (-not $owner -or $owner.ProcessName -ne 'ssh') {
        Write-WatchdogLog "Refusing to stop non-SSH owner of port $LocalForwardPort (PID $($listener.OwningProcess))."
        return $false
    }

    Write-WatchdogLog "Stopping stale SSH forward PID $($owner.Id)."
    Stop-Process -Id $owner.Id -Force -ErrorAction SilentlyContinue
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if (-not (Get-ForwardListener)) { return $true }
        Start-Sleep -Milliseconds 250
    }
    Write-WatchdogLog "Port $LocalForwardPort remained occupied after stopping stale SSH PID $($owner.Id)."
    return $false
}

function Start-Forward {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $sshLog = Join-Path $runtimeDirectory "ssh-249-gpu5-watchdog-$stamp.stderr.log"
    $arguments = @(
        '-N', '-T',
        '-o', 'BatchMode=yes',
        '-o', 'ConnectTimeout=8',
        '-o', 'ConnectionAttempts=1',
        '-o', 'ExitOnForwardFailure=yes',
        '-o', 'ServerAliveInterval=15',
        '-o', 'ServerAliveCountMax=2',
        '-L', "127.0.0.1:${LocalForwardPort}:127.0.0.1:${ServerDecoderPort}",
        '-i', $ServerKeyPath,
        "${ServerUser}@${ServerHost}"
    )
    $ssh = Start-Process -FilePath 'ssh.exe' -ArgumentList $arguments `
        -WindowStyle Hidden -RedirectStandardError $sshLog -PassThru
    Write-WatchdogLog "Started replacement SSH forward PID $($ssh.Id)."

    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 500
        if ($ssh.HasExited) {
            $details = (Get-Content -LiteralPath $sshLog -Raw -ErrorAction SilentlyContinue).Trim()
            if (-not $details) { $details = 'no stderr details' }
            Write-WatchdogLog "Replacement SSH PID $($ssh.Id) exited before ready: $details"
            return $false
        }
        if (Test-ExpectedHealth) {
            Write-WatchdogLog "SSH forward PID $($ssh.Id) passed exact GPU5 health verification."
            return $true
        }
    }

    Write-WatchdogLog "Replacement SSH PID $($ssh.Id) did not become healthy within 20 seconds."
    Stop-Process -Id $ssh.Id -Force -ErrorAction SilentlyContinue
    return $false
}

$failureCount = 0
Write-WatchdogLog "Watchdog started for 127.0.0.1:$LocalForwardPort -> ${ServerHost}:$ServerDecoderPort."

do {
    try {
        if (Test-ExpectedHealth) {
            $failureCount = 0
        }
        else {
            Write-WatchdogLog "Exact local health check failed; attempting SSH recovery."
            $listenerReady = Remove-StaleSshListener
            $forwardReady = $false
            if ($listenerReady) {
                $forwardReady = Start-Forward
            }
            if ($listenerReady -and $forwardReady) {
                $failureCount = 0
            }
            else {
                $failureCount++
            }
        }
    }
    catch {
        $failureCount++
        Write-WatchdogLog "Recovery cycle failed: $($_.Exception.Message)"
    }

    if ($RunOnce) { break }
    $backoffSeconds = [Math]::Min(60, $CheckIntervalSeconds * [Math]::Pow(2, [Math]::Min($failureCount, 3)))
    Start-Sleep -Seconds ([int]$backoffSeconds)
} while ($true)
