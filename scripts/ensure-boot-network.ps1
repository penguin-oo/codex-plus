param(
    [int]$WaitSeconds = 180,
    [string[]]$ExtraServiceNames = @()
)

$ErrorActionPreference = "Continue"

$logDir = Join-Path $env:ProgramData "CodexSessionManager"
$logPath = Join-Path $logDir "ensure-boot-network.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logPath -Value "$timestamp $Message"
}

function Ensure-ServiceRunning {
    param([string]$Name)

    $service = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if (-not $service) {
        Write-Log "service missing: $Name"
        return $false
    }

    if ($service.Status -ne "Running") {
        Write-Log "starting service: $Name"
        Start-Service -Name $Name -ErrorAction Continue
        $service.WaitForStatus("Running", [TimeSpan]::FromSeconds(30))
    }

    $service.Refresh()
    Write-Log "service status: $Name=$($service.Status)"
    return ($service.Status -eq "Running")
}

function Test-NetworkReady {
    $hasAdapter = Get-NetAdapter -ErrorAction SilentlyContinue |
        Where-Object { $_.Status -eq "Up" } |
        Select-Object -First 1
    if (-not $hasAdapter) {
        return $false
    }

    $hasRoute = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue |
        Where-Object { $_.NextHop -and $_.NextHop -ne "0.0.0.0" } |
        Select-Object -First 1
    return [bool]$hasRoute
}

Write-Log "boot network check started"
$configuredExtraServices = @()
if ($env:CODEX_SESSION_MANAGER_BOOT_SERVICES) {
    $configuredExtraServices = $env:CODEX_SESSION_MANAGER_BOOT_SERVICES -split "," |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ }
}
foreach ($serviceName in @($ExtraServiceNames + $configuredExtraServices)) {
    Ensure-ServiceRunning -Name $serviceName | Out-Null
}

$deadline = (Get-Date).AddSeconds($WaitSeconds)
do {
    if (Test-NetworkReady) {
        Write-Log "network ready"
        break
    }

    Write-Log "network not ready, waiting"
    Start-Sleep -Seconds 10
} while ((Get-Date) -lt $deadline)

Ensure-ServiceRunning -Name "Tailscale" | Out-Null

$tailscale = Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"
if (Test-Path $tailscale) {
    $status = & $tailscale status --json 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $status) {
        Write-Log "tailscale status unavailable, restarting service"
        Restart-Service -Name "Tailscale" -Force -ErrorAction Continue
    } else {
        Write-Log "tailscale status available"
    }
}

Write-Log "boot network check finished"
