param(
    [string]$OutputRoot = "backup",
    [int]$Keep = 10
)

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $OutputRoot $timestamp
$dbDumpPath = Join-Path $backupDir "postgres.sql"
$dataArchivePath = Join-Path $backupDir "data.zip"
$manifestPath = Join-Path $backupDir "manifest.txt"

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

Write-Host "Creating PostgreSQL dump..." -ForegroundColor Cyan
docker compose exec -T database sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | Out-File -FilePath $dbDumpPath -Encoding utf8

if (Test-Path "data") {
    Write-Host "Archiving local data folder..." -ForegroundColor Cyan
    if (Test-Path $dataArchivePath) {
        Remove-Item -LiteralPath $dataArchivePath
    }
    Compress-Archive -Path "data\*" -DestinationPath $dataArchivePath
}
else {
    Write-Host "Skipping data archive because ./data does not exist." -ForegroundColor Yellow
}

@(
    "created_at=$((Get-Date).ToString('o'))"
    "database_dump=postgres.sql"
    "data_archive=data.zip"
    "compose_project=$((Split-Path -Leaf (Get-Location)))"
    "notes=Restore database with: Get-Content postgres.sql | docker compose exec -T database sh -c 'psql -U ""$POSTGRES_USER"" -d ""$POSTGRES_DB""'"
) | Set-Content -Path $manifestPath -Encoding utf8

$existingBackups = Get-ChildItem -Path $OutputRoot -Directory |
    Where-Object { $_.Name -match '^\d{8}-\d{6}$' } |
    Sort-Object Name -Descending

$existingBackups |
    Select-Object -Skip $Keep |
    ForEach-Object {
        Write-Host "Removing old backup: $($_.FullName)" -ForegroundColor Yellow
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
    }

Write-Host "Backup created at $backupDir" -ForegroundColor Green
