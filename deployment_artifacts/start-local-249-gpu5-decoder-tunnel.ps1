[CmdletBinding()]
param(
    [string]$ServerHost = '172.18.185.249',
    [string]$ServerUser = 'liyanlei',
    [string]$ServerKeyPath = "$env:USERPROFILE\.ssh\ceramic_249_ed25519",
    [int]$ServerDecoderPort = 28765,
    [int]$LocalForwardPort = 18766,
    [string]$CloudflaredPath = '',
    [switch]$ForceNewTunnel
)

$ErrorActionPreference = 'Stop'

$deploymentDirectory = Split-Path -Parent $PSCommandPath
$projectRoot = Split-Path -Parent $deploymentDirectory
$runtimeDirectory = Join-Path $projectRoot 'tmp'
$expectedModel = 'trustmark-q-57bit-real18-step113100-locator5-perspective-rotation'
$expectedCheckpointSha256 = '834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef'
$logPrefix = 'cloudflared-249-gpu5'

if (-not (Test-Path -LiteralPath $runtimeDirectory)) {
    New-Item -ItemType Directory -Path $runtimeDirectory | Out-Null
}
if (-not (Test-Path -LiteralPath $ServerKeyPath -PathType Leaf)) {
    throw "249 SSH key not found: $ServerKeyPath"
}

if ([string]::IsNullOrWhiteSpace($CloudflaredPath)) {
    $bundled = Join-Path $projectRoot 'tmp\cloudflared-local\cloudflared.exe'
    $installed = Get-Command cloudflared.exe -ErrorAction SilentlyContinue
    if ($installed) { $CloudflaredPath = $installed.Source }
    elseif (Test-Path -LiteralPath $bundled -PathType Leaf) {
        $CloudflaredPath = $bundled
    }
    else { throw 'cloudflared.exe was not found.' }
}

function Get-Health {
    param([Parameter(Mandatory = $true)][string]$BaseUrl)

    try {
        $health = Invoke-RestMethod -Uri "$BaseUrl/healthz" -Method Get -TimeoutSec 12
    }
    catch { $health = $null }
    if (
        $health -and $health.status -eq 'ok' -and
        $health.model -eq $expectedModel -and
        $health.payload_bits -eq 57 -and
        $health.checkpoint_sha256 -eq $expectedCheckpointSha256 -and
        $health.localization -eq 'outer-logo-contour+inner-square-perspective-fallback+quarter-turn-rotation-fallback' -and
        $health.localized_variants -eq 3 -and
        $health.perspective_variants -eq 12 -and
        $health.rotation_variants -eq 36 -and
        $health.device -eq 'cuda:0'
    ) { return $health }

    try {
        $uri = [uri]$BaseUrl
        if ($uri.Scheme -ne 'https' -or $uri.DnsSafeHost -notlike '*.trycloudflare.com') {
            return $null
        }
        $curl = Get-Command curl.exe -ErrorAction Stop
        $nameServers = @(
            Resolve-DnsName trycloudflare.com -Type NS -DnsOnly -ErrorAction Stop |
                Where-Object NameHost |
                Select-Object -ExpandProperty NameHost -Unique
        )
        foreach ($nameServer in $nameServers) {
            $addresses = @(
                Resolve-DnsName $uri.DnsSafeHost -Type A -Server $nameServer `
                    -DnsOnly -QuickTimeout -ErrorAction Stop |
                    Where-Object IPAddress |
                    Select-Object -ExpandProperty IPAddress -Unique
            )
            foreach ($address in $addresses) {
                $resolveValue = '{0}:443:{1}' -f $uri.DnsSafeHost, $address
                $raw = & $curl.Source -fsS --max-time 12 --resolve $resolveValue `
                    "$BaseUrl/healthz" 2>$null
                if ($LASTEXITCODE -ne 0 -or -not $raw) { continue }
                $health = ($raw -join "`n") | ConvertFrom-Json -ErrorAction Stop
                if (
                    $health.status -eq 'ok' -and
                    $health.model -eq $expectedModel -and
                    $health.payload_bits -eq 57 -and
                    $health.checkpoint_sha256 -eq $expectedCheckpointSha256 -and
                    $health.localization -eq 'outer-logo-contour+inner-square-perspective-fallback+quarter-turn-rotation-fallback' -and
                    $health.localized_variants -eq 3 -and
                    $health.perspective_variants -eq 12 -and
                    $health.rotation_variants -eq 36 -and
                    $health.device -eq 'cuda:0'
                ) { return $health }
            }
        }
    }
    catch { return $null }
    return $null
}

function Get-TunnelProcesses {
    return @(
        Get-CimInstance Win32_Process -Filter "Name = 'cloudflared.exe'" |
            Where-Object {
                $_.CommandLine -and
                $_.CommandLine -like "*127.0.0.1:$LocalForwardPort*"
            }
    )
}

function Get-LoggedUrls {
    $seen = @{}
    foreach ($log in @(
        Get-ChildItem -LiteralPath $runtimeDirectory -Filter "$logPrefix-*.stderr.log" `
            -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 20
    )) {
        $content = Get-Content -LiteralPath $log.FullName -Raw -ErrorAction SilentlyContinue
        foreach ($match in [regex]::Matches($content, 'https://[a-zA-Z0-9-]+\.trycloudflare\.com')) {
            if (-not $seen.ContainsKey($match.Value)) {
                $seen[$match.Value] = $true
                $match.Value
            }
        }
    }
}

$localBaseUrl = "http://127.0.0.1:$LocalForwardPort"
$listener = Get-NetTCPConnection -LocalPort $LocalForwardPort -State Listen `
    -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    if (-not (Get-Health -BaseUrl $localBaseUrl)) {
        throw "Port $LocalForwardPort is in use but is not the expected GPU5 decoder."
    }
    $sshProcessId = $listener.OwningProcess
}
else {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $sshLog = Join-Path $runtimeDirectory "ssh-249-gpu5-$stamp.stderr.log"
    $arguments = @(
        '-N', '-T',
        '-o', 'BatchMode=yes',
        '-o', 'ExitOnForwardFailure=yes',
        '-o', 'ServerAliveInterval=30',
        '-o', 'ServerAliveCountMax=3',
        '-L', "127.0.0.1:${LocalForwardPort}:127.0.0.1:${ServerDecoderPort}",
        '-i', $ServerKeyPath,
        "${ServerUser}@${ServerHost}"
    )
    $ssh = Start-Process -FilePath 'ssh.exe' -ArgumentList $arguments `
        -WindowStyle Hidden -RedirectStandardError $sshLog -PassThru
    $sshProcessId = $ssh.Id
    $localHealth = $null
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 500
        if ($ssh.HasExited) {
            $details = Get-Content -LiteralPath $sshLog -Raw -ErrorAction SilentlyContinue
            throw "SSH forwarding exited before ready. $details"
        }
        $localHealth = Get-Health -BaseUrl $localBaseUrl
        if ($localHealth) { break }
    }
    if (-not $localHealth) { throw 'GPU5 SSH forwarding health check timed out.' }
}

$tunnelProcesses = @(Get-TunnelProcesses)
if ($ForceNewTunnel) {
    foreach ($process in $tunnelProcesses) {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
    $tunnelProcesses = @()
    Start-Sleep -Milliseconds 500
}
elseif ($tunnelProcesses.Count -gt 0) {
    foreach ($url in Get-LoggedUrls) {
        $health = Get-Health -BaseUrl $url
        if ($health) {
            [pscustomobject]@{
                topology = 'Mini Program -> Cloudflare -> local PC -> SSH -> 249 GPU5'
                base_url = $url
                decode_url = "$url/decode"
                model = $health.model
                checkpoint_sha256 = $health.checkpoint_sha256
                device = $health.device
                ssh_process_id = $sshProcessId
                cloudflared_process_id = $tunnelProcesses[0].ProcessId
                reused_existing_tunnel = $true
            } | ConvertTo-Json -Compress
            return
        }
    }
    foreach ($process in $tunnelProcesses) {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 500
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stdout = Join-Path $runtimeDirectory "$logPrefix-$stamp.stdout.log"
$stderr = Join-Path $runtimeDirectory "$logPrefix-$stamp.stderr.log"
$cloudflared = Start-Process -FilePath $CloudflaredPath -ArgumentList @(
    'tunnel', '--no-autoupdate', '--edge-ip-version', '4',
    '--protocol', 'http2', '--url', $localBaseUrl
) -WindowStyle Hidden -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr -PassThru

$verifiedUrl = $null
$verifiedHealth = $null
for ($attempt = 0; $attempt -lt 90; $attempt++) {
    Start-Sleep -Seconds 1
    if ($cloudflared.HasExited) {
        $details = Get-Content -LiteralPath $stderr -Raw -ErrorAction SilentlyContinue
        throw "cloudflared exited before ready. $details"
    }
    $content = Get-Content -LiteralPath $stderr -Raw -ErrorAction SilentlyContinue
    $match = [regex]::Match($content, 'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
    if ($match.Success) {
        $health = Get-Health -BaseUrl $match.Value
        if ($health) {
            $verifiedUrl = $match.Value
            $verifiedHealth = $health
            break
        }
    }
}
if (-not $verifiedUrl) { throw "GPU5 tunnel verification timed out. See $stderr" }

[pscustomobject]@{
    topology = 'Mini Program -> Cloudflare -> local PC -> SSH -> 249 GPU5'
    base_url = $verifiedUrl
    decode_url = "$verifiedUrl/decode"
    model = $verifiedHealth.model
    checkpoint_sha256 = $verifiedHealth.checkpoint_sha256
    device = $verifiedHealth.device
    ssh_process_id = $sshProcessId
    cloudflared_process_id = $cloudflared.Id
    reused_existing_tunnel = $false
} | ConvertTo-Json -Compress
