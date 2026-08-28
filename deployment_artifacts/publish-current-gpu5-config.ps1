[CmdletBinding()]
param(
    [string]$ConfigPath = '',
    [string]$UpdateUrl = $env:DECODER_CONFIG_UPDATE_URL,
    [string]$UpdateKey = $env:DECODER_CONFIG_UPDATE_KEY
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
if ([string]::IsNullOrWhiteSpace($ConfigPath)) { $ConfigPath = Join-Path $projectRoot 'tmp\current-gpu5-decode-url.json' }
if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) { throw "Config file not found: $ConfigPath" }
if ([string]::IsNullOrWhiteSpace($UpdateUrl)) { throw 'DECODER_CONFIG_UPDATE_URL is not configured.' }
if ([string]::IsNullOrWhiteSpace($UpdateKey)) { throw 'DECODER_CONFIG_UPDATE_KEY is not configured.' }
$state = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$json = $state | ConvertTo-Json -Depth 10 -Compress
$headers = @{ 'X-Decoder-Config-Key' = $UpdateKey; 'Content-Type' = 'application/json' }
$result = Invoke-RestMethod -Uri $UpdateUrl -Method Post -Headers $headers -Body $json -TimeoutSec 15
if (-not $result.ok) { throw 'CloudBase configuration update was rejected.' }
Write-Output ($result | ConvertTo-Json -Compress)
