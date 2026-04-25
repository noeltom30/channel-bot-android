param(
    [string]$BlueStacksPath,
    [string]$Device = "127.0.0.1:5555",
    [int]$BlueStacksBootTimeoutSec = 120,
    [int]$AdbRetryIntervalSec = 3,
    [switch]$SkipBlueStacks,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[PIPELINE] $Message" -ForegroundColor Cyan
}

function Resolve-BlueStacksPath {
    param([string]$OverridePath)

    if ($OverridePath) {
        if (Test-Path -LiteralPath $OverridePath) {
            return (Resolve-Path -LiteralPath $OverridePath).Path
        }
        throw "BlueStacks executable not found at: $OverridePath"
    }

    $candidates = @(
        "$env:ProgramFiles\BlueStacks_nxt\HD-Player.exe",
        "$env:ProgramFiles\BlueStacks\HD-Player.exe",
        "$env:ProgramFiles(x86)\BlueStacks_nxt\HD-Player.exe",
        "$env:ProgramFiles(x86)\BlueStacks\HD-Player.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "Could not locate BlueStacks automatically. Pass -BlueStacksPath <path to HD-Player.exe>."
}

function Get-AdbCommand {
    param(
        [string]$ProjectRoot,
        [string]$BlueStacksExe
    )

    $localAdb = Join-Path $ProjectRoot ".venv\Scripts\adb.exe"
    if (Test-Path -LiteralPath $localAdb) {
        return $localAdb
    }

    if ($BlueStacksExe) {
        $bsFolder = Split-Path -Parent $BlueStacksExe
        $bsAdb = Join-Path $bsFolder "HD-Adb.exe"
        if (Test-Path -LiteralPath $bsAdb) {
            return $bsAdb
        }
    }

    $adbFromPath = Get-Command adb -ErrorAction SilentlyContinue
    if ($adbFromPath) {
        return $adbFromPath.Source
    }

    throw "adb not found. Install Android platform-tools or ensure BlueStacks HD-Adb.exe is present."
}

function Wait-ForAdbDevice {
    param(
        [string]$Adb,
        [string]$Device,
        [int]$TimeoutSec,
        [int]$RetryIntervalSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)

    while ((Get-Date) -lt $deadline) {
        & $Adb connect $Device | Out-Null
        $devices = (& $Adb devices) -join "`n"
        if ($devices -match [regex]::Escape("$Device`tdevice")) {
            return $true
        }
        Start-Sleep -Seconds $RetryIntervalSec
    }

    return $false
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$appScript = Join-Path $projectRoot "src\motion.py"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Python virtual environment not found at: $pythonExe"
}

if (-not (Test-Path -LiteralPath $appScript)) {
    throw "Application entry script not found at: $appScript"
}

$resolvedBlueStacksPath = $null
if (-not $SkipBlueStacks) {
    $resolvedBlueStacksPath = Resolve-BlueStacksPath -OverridePath $BlueStacksPath
    Write-Step "Starting BlueStacks: $resolvedBlueStacksPath"
    if (-not $DryRun) {
        Start-Process -FilePath $resolvedBlueStacksPath | Out-Null
    }
}
else {
    Write-Step "Skipping BlueStacks startup because -SkipBlueStacks was provided."
}

$adb = $null
if ($DryRun) {
    Write-Step "Dry run enabled: skipping adb discovery and device readiness check."
}
else {
    $adb = Get-AdbCommand -ProjectRoot $projectRoot -BlueStacksExe $resolvedBlueStacksPath
    Write-Step "Using adb: $adb"

    Write-Step "Waiting for emulator device $Device to become available..."
    $ready = Wait-ForAdbDevice -Adb $adb -Device $Device -TimeoutSec $BlueStacksBootTimeoutSec -RetryIntervalSec $AdbRetryIntervalSec
    if (-not $ready) {
        throw "Timed out waiting for $Device to become available in adb."
    }
}

Write-Step "Launching automation app: $appScript"
if ($DryRun) {
    Write-Host "[DRY RUN] & `"$pythonExe`" `"$appScript`"" -ForegroundColor Yellow
}
else {
    Push-Location $projectRoot
    try {
        & $pythonExe $appScript
    }
    finally {
        Pop-Location
    }
}

Write-Step "Pipeline finished."