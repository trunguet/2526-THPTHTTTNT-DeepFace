param(
    [string]$TaskName = "DeepFaceBackupS3",
    [string]$StartTime = "02:00",
    [string]$ScriptPath = "",
    [string]$LogPath = "",
    [switch]$RunNow
)

$ErrorActionPreference = "Stop"

if (-not $ScriptPath) {
    $ScriptPath = Join-Path $PSScriptRoot "backup-s3.ps1"
}

$resolvedScript = (Resolve-Path $ScriptPath).Path
if (-not $LogPath) {
    $LogPath = Join-Path $PSScriptRoot "..\logs\backup-s3.log"
}

$logDirectory = Split-Path -Parent $LogPath
if ($logDirectory) {
    New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
}

$resolvedLog = if ($logDirectory) {
    Join-Path (Resolve-Path $logDirectory).Path (Split-Path -Leaf $LogPath)
}
else {
    (Resolve-Path $LogPath).Path
}

New-Item -ItemType File -Force -Path $resolvedLog | Out-Null

$taskCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$resolvedScript`" -LogPath `"$resolvedLog`""

Write-Host "Creating scheduled task '$TaskName' every 5 days at $StartTime..." -ForegroundColor Cyan
Write-Host "Log file: $resolvedLog" -ForegroundColor Cyan
schtasks /Create /SC DAILY /MO 5 /ST $StartTime /TN $TaskName /TR $taskCommand /F | Out-Null

if ($RunNow) {
    schtasks /Run /TN $TaskName | Out-Null
    Write-Host "Scheduled task triggered: $TaskName" -ForegroundColor Green
}
else {
    Write-Host "Scheduled task created: $TaskName" -ForegroundColor Green
}
