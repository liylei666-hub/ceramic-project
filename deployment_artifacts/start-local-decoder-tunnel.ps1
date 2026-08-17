[CmdletBinding()]
param(
    [string]$EcsHost = '8.138.42.34',
    [string]$EcsUser = 'root',
    [string]$EcsKeyPath = "$env:USERPROFILE\.ssh\aliyun_ceramic_temp_rsa",
    [int]$EcsDecoderPort = 8765,
    [int]$LocalForwardPort = 18765,
    [string]$CloudflaredPath = '',
    [switch]$ForceNewTunnel
)

$ErrorActionPreference = 'Stop'

$deploymentDirectory = Split-Path -Parent $PSCommandPath
$projectRoot = Split-Path -Parent $deploymentDirectory
$runtimeDirectory = Join-Path $projectRoot 'tmp'
$expectedModel = 'trustmark-q-57bit-900k-real18-legacy-adapt-pilot3-step600-candidate'
$expectedCheckpointSha256 = '834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef'

if (-not (Test-Path -LiteralPath $runtimeDirectory)) {
    New-Item -ItemType Directory -Path $runtimeDirectory | Out-Null
}
if (-not (Test-Path -LiteralPath $EcsKeyPath -PathType Leaf)) {
    throw "ECS SSH key not found: $EcsKeyPath"
}

if ([string]::IsNullOrWhiteSpace($CloudflaredPath)) {
    $bundledCloudflared = Join-Path $projectRoot 'tmp\cloudflared-local\cloudflared.exe'
    $installedCloudflared = Get-Command cloudflared.exe -ErrorAction SilentlyContinue
    if ($installedCloudflared) {
        $CloudflaredPath = $installedCloudflared.Source
    }
    elseif (Test-Path -LiteralPath $bundledCloudflared -PathType Leaf) {
        $CloudflaredPath = $bundledCloudflared
    }
    else {
        throw 'cloudflared.exe was not found in PATH or tmp\cloudflared-local.'
    }
}
if (-not (Test-Path -LiteralPath $CloudflaredPath -PathType Leaf)) {
    throw "cloudflared.exe not found: $CloudflaredPath"
}

function Get-Health {
    param([Parameter(Mandatory = $true)][string]$BaseUrl)

    $health = $null
    try {
        $health = Invoke-RestMethod -Uri "$BaseUrl/healthz" -Method Get -TimeoutSec 12
    }
    catch {
        $health = $null
    }
    if (
        $health -and
        $health.status -eq 'ok' -and
        $health.model -eq $expectedModel -and
        $health.payload_bits -eq 57 -and
        $health.checkpoint_sha256 -eq $expectedCheckpointSha256
    ) {
        return $health
    }

    # A newly-created Quick Tunnel can already exist in Cloudflare's
    # authoritative DNS while the operator PC's upstream resolver still caches
    # an earlier NXDOMAIN. Verify that narrow case with the authoritative
    # answer and curl --resolve so a healthy tunnel is not discarded.
    try {
        $uri = [uri]$BaseUrl
        if ($uri.Scheme -ne 'https' -or $uri.DnsSafeHost -notlike '*.trycloudflare.com') {
            return $null
        }
        $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
        if (-not $curl) {
            return $null
        }
        $nameServers = @(
            Resolve-DnsName trycloudflare.com -Type NS -DnsOnly -ErrorAction Stop |
                Where-Object { $_.NameHost } |
                Select-Object -ExpandProperty NameHost -Unique
        )
        foreach ($nameServer in $nameServers) {
            $addresses = @(
                Resolve-DnsName $uri.DnsSafeHost `
                    -Type A `
                    -Server $nameServer `
                    -DnsOnly `
                    -QuickTimeout `
                    -ErrorAction Stop |
                    Where-Object { $_.IPAddress } |
                    Select-Object -ExpandProperty IPAddress -Unique
            )
            foreach ($address in $addresses) {
                $resolveValue = '{0}:443:{1}' -f $uri.DnsSafeHost, $address
                $raw = & $curl.Source `
                    -fsS `
                    --max-time 12 `
                    --resolve $resolveValue `
                    "$BaseUrl/healthz" 2>$null
                if ($LASTEXITCODE -ne 0 -or -not $raw) {
                    continue
                }
                $health = ($raw -join "`n") | ConvertFrom-Json -ErrorAction Stop
                if (
                    $health.status -eq 'ok' -and
                    $health.model -eq $expectedModel -and
                    $health.payload_bits -eq 57 -and
                    $health.checkpoint_sha256 -eq $expectedCheckpointSha256
                ) {
                    return $health
                }
            }
        }
    }
    catch {
        return $null
    }
    return $null
}

function Get-ProjectCloudflaredProcesses {
    return @(
        Get-CimInstance Win32_Process -Filter "Name = 'cloudflared.exe'" |
            Where-Object {
                $_.CommandLine -and
                $_.CommandLine -like "*127.0.0.1:$LocalForwardPort*"
            }
    )
}

function Get-LoggedTunnelUrls {
    $seen = @{}
    $urls = [System.Collections.Generic.List[string]]::new()
    $logs = @(
        Get-ChildItem -LiteralPath $runtimeDirectory -Filter 'cloudflared-*.stderr.log' -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 20
    )
    foreach ($log in $logs) {
        $content = Get-Content -LiteralPath $log.FullName -Raw -ErrorAction SilentlyContinue
        foreach ($match in [regex]::Matches($content, 'https://[a-zA-Z0-9-]+\.trycloudflare\.com')) {
            $url = $match.Value
            if (-not $seen.ContainsKey($url)) {
                $seen[$url] = $true
                $urls.Add($url)
            }
        }
    }
    return $urls
}

$localBaseUrl = "http://127.0.0.1:$LocalForwardPort"
$listener = Get-NetTCPConnection -LocalPort $LocalForwardPort -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1

if ($listener) {
    if (-not (Get-Health -BaseUrl $localBaseUrl)) {
        throw "Port $LocalForwardPort is already in use but does not reach the expected 900K decoder."
    }
    $sshProcessId = $listener.OwningProcess
}
else {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $sshLog = Join-Path $runtimeDirectory "ssh-ecs-decoder-local-$stamp.stderr.log"
    $sshArguments = @(
        '-N', '-T',
        '-o', 'BatchMode=yes',
        '-o', 'ExitOnForwardFailure=yes',
        '-o', 'ServerAliveInterval=30',
        '-o', 'ServerAliveCountMax=3',
        '-L', "127.0.0.1:${LocalForwardPort}:127.0.0.1:${EcsDecoderPort}",
        '-i', $EcsKeyPath,
        "${EcsUser}@${EcsHost}"
    )
    $sshProcess = Start-Process `
        -FilePath 'ssh.exe' `
        -ArgumentList $sshArguments `
        -WindowStyle Hidden `
        -RedirectStandardError $sshLog `
        -PassThru
    $sshProcessId = $sshProcess.Id

    $localHealth = $null
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 500
        if ($sshProcess.HasExited) {
            $details = Get-Content -LiteralPath $sshLog -Raw -ErrorAction SilentlyContinue
            throw "SSH forwarding process exited before becoming ready. $details"
        }
        $localHealth = Get-Health -BaseUrl $localBaseUrl
        if ($localHealth) {
            break
        }
    }
    if (-not $localHealth) {
        throw 'Timed out waiting for the local SSH forwarding path to the ECS decoder.'
    }
}

$cloudflaredProcesses = @(Get-ProjectCloudflaredProcesses)
if ($ForceNewTunnel) {
    foreach ($process in $cloudflaredProcesses) {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
    $cloudflaredProcesses = @()
    Start-Sleep -Milliseconds 500
}
elseif ($cloudflaredProcesses.Count -gt 0) {
    foreach ($url in Get-LoggedTunnelUrls) {
        $health = Get-Health -BaseUrl $url
        if ($health) {
            [pscustomobject]@{
                topology = 'Mini Program -> Cloudflare -> local PC -> SSH -> ECS decoder'
                base_url = $url
                decode_url = "$url/decode"
                model = $health.model
                checkpoint_sha256 = $health.checkpoint_sha256
                ssh_process_id = $sshProcessId
                cloudflared_process_id = $cloudflaredProcesses[0].ProcessId
                reused_existing_tunnel = $true
            } | ConvertTo-Json -Compress
            return
        }
    }

    foreach ($process in $cloudflaredProcesses) {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 500
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$cloudflaredStdout = Join-Path $runtimeDirectory "cloudflared-900k-local-$stamp.stdout.log"
$cloudflaredStderr = Join-Path $runtimeDirectory "cloudflared-900k-local-$stamp.stderr.log"
$cloudflaredArguments = @(
    'tunnel',
    '--no-autoupdate',
    '--edge-ip-version', '4',
    '--protocol', 'http2',
    '--url', $localBaseUrl
)
$cloudflaredProcess = Start-Process `
    -FilePath $CloudflaredPath `
    -ArgumentList $cloudflaredArguments `
    -WindowStyle Hidden `
    -RedirectStandardOutput $cloudflaredStdout `
    -RedirectStandardError $cloudflaredStderr `
    -PassThru

$verifiedUrl = $null
$verifiedHealth = $null
for ($attempt = 0; $attempt -lt 90; $attempt++) {
    Start-Sleep -Seconds 1
    if ($cloudflaredProcess.HasExited) {
        $details = Get-Content -LiteralPath $cloudflaredStderr -Raw -ErrorAction SilentlyContinue
        throw "cloudflared exited before the tunnel became ready. $details"
    }
    $content = Get-Content -LiteralPath $cloudflaredStderr -Raw -ErrorAction SilentlyContinue
    $match = [regex]::Match($content, 'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
    if ($match.Success) {
        $candidateUrl = $match.Value
        $candidateHealth = Get-Health -BaseUrl $candidateUrl
        if ($candidateHealth) {
            $verifiedUrl = $candidateUrl
            $verifiedHealth = $candidateHealth
            break
        }
    }
}

if (-not $verifiedUrl) {
    throw "Timed out waiting for a verified trycloudflare.com URL. See $cloudflaredStderr"
}

[pscustomobject]@{
    topology = 'Mini Program -> Cloudflare -> local PC -> SSH -> ECS decoder'
    base_url = $verifiedUrl
    decode_url = "$verifiedUrl/decode"
    model = $verifiedHealth.model
    checkpoint_sha256 = $verifiedHealth.checkpoint_sha256
    ssh_process_id = $sshProcessId
    cloudflared_process_id = $cloudflaredProcess.Id
    reused_existing_tunnel = $false
} | ConvertTo-Json -Compress
