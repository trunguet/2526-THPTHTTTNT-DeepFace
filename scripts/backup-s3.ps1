param(
    [string]$Bucket = $env:S3_BUCKET,
    [string]$Prefix = $env:S3_PREFIX,
    [string]$EndpointUrl = $env:S3_ENDPOINT_URL,
    [string]$Region = $env:AWS_REGION,
    [string]$Profile = $env:AWS_PROFILE,
    [string]$OutputRoot = "backup-s3",
    [int]$KeepLocal = 0,
    [switch]$UseDockerAwsCli,
    [string]$LogPath = $env:S3_LOG_PATH
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not [System.IO.Path]::IsPathRooted($OutputRoot)) {
    $OutputRoot = Join-Path $repoRoot.Path $OutputRoot
}

$script:LogFile = ""
if ($LogPath) {
    $logDirectory = Split-Path -Parent $LogPath
    if ($logDirectory) {
        New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
    }
    if (-not [System.IO.Path]::IsPathRooted($LogPath)) {
        $LogPath = Join-Path (Get-Location).Path $LogPath
    }
    $script:LogFile = $LogPath
    New-Item -ItemType File -Force -Path $script:LogFile | Out-Null
}

function Write-Log {
    param(
        [string]$Message,
        [string]$Color = ""
    )

    $timestamped = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    if ($Color) {
        Write-Host $timestamped -ForegroundColor $Color
    }
    else {
        Write-Host $timestamped
    }
    if ($script:LogFile) {
        Add-Content -Path $script:LogFile -Value $timestamped
    }
    Write-Output $timestamped
}

function Import-EnvFile {
    param([string]$Path)

    Get-Content -Path $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line) {
            return
        }
        if ($line.StartsWith("#")) {
            return
        }
        $parts = $line -split "=", 2
        if ($parts.Count -lt 2) {
            return
        }
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if (-not $name) {
            return
        }
        if ($value.StartsWith('"') -and $value.EndsWith('"')) {
            $value = $value.Trim('"')
        }
        if ($value.StartsWith("'") -and $value.EndsWith("'")) {
            $value = $value.Trim("'")
        }

        $current = (Get-Item -Path "Env:$name" -ErrorAction SilentlyContinue).Value
        if (-not $current) {
            Set-Item -Path "Env:$name" -Value $value
        }
    }
}

$envFile = Join-Path $PSScriptRoot "backup-s3.env"
if (Test-Path $envFile) {
    Import-EnvFile -Path $envFile
}

if (-not $Bucket) {
    $Bucket = $env:S3_BUCKET
}
if (-not $Prefix) {
    $Prefix = $env:S3_PREFIX
}
if (-not $EndpointUrl) {
    $EndpointUrl = $env:S3_ENDPOINT_URL
}
if (-not $Region) {
    $Region = $env:AWS_REGION
}
if (-not $Profile) {
    $Profile = $env:AWS_PROFILE
}

if (-not $Bucket) {
    throw "S3_BUCKET is required."
}

$useDocker = $false
if ($UseDockerAwsCli) {
    $useDocker = $true
}
elseif ($env:S3_USE_DOCKER_CLI) {
    $flag = $env:S3_USE_DOCKER_CLI.Trim().ToLower()
    $useDocker = $flag -in @("1", "true", "yes", "on")
}
elseif (Get-Command aws -ErrorAction SilentlyContinue) {
    $useDocker = $false
}
elseif (Get-Command docker -ErrorAction SilentlyContinue) {
    $useDocker = $true
}
else {
    throw "AWS CLI is required or enable Docker AWS CLI (S3_USE_DOCKER_CLI=true)."
}

try {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupDir = Join-Path $OutputRoot $timestamp
    $dbDumpPath = Join-Path $backupDir "postgres.sql"
    $manifestPath = Join-Path $backupDir "manifest.txt"

    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

    Push-Location $repoRoot.Path
    try {
        Write-Log "Creating PostgreSQL dump..." "Cyan"
        $dumpCommand = 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
        docker compose exec -T database sh -c $dumpCommand | Out-File -FilePath $dbDumpPath -Encoding utf8
    }
    finally {
        Pop-Location
    }

    $prefixNormalized = if ($Prefix) { $Prefix } else { "deepface-db-backups" }
    $prefixNormalized = $prefixNormalized.Trim("/")
    $targetBase = "s3://$Bucket/$prefixNormalized/$timestamp"

    $restoreHint = "restore_hint=aws s3 cp $targetBase/postgres.sql - | docker compose exec -T database sh -c 'psql -U `"`$POSTGRES_USER`" -d `"`$POSTGRES_DB`"'"

    @(
        "created_at=$((Get-Date).ToString('o'))"
        "database_dump=postgres.sql"
        "s3_bucket=$Bucket"
        "s3_prefix=$prefixNormalized"
        "compose_project=$((Split-Path -Leaf $repoRoot.Path))"
        $restoreHint
    ) | Set-Content -Path $manifestPath -Encoding utf8

function Invoke-AwsCopy {
    param(
        [string]$Source,
        [string]$Target
    )

    if (-not $useDocker) {
        $args = @("s3", "cp", $Source, $Target, "--only-show-errors")
        if ($EndpointUrl) {
            $args += @("--endpoint-url", $EndpointUrl)
        }
        if ($Region) {
            $args += @("--region", $Region)
        }
        if ($Profile) {
            $args += @("--profile", $Profile)
        }

        & aws @args
        if ($LASTEXITCODE -ne 0) {
            throw "aws s3 cp failed for $Source"
        }
        return
    }

    $localDir = Split-Path -Parent $Source
    if (-not [System.IO.Path]::IsPathRooted($localDir)) {
        $localDir = Join-Path (Get-Location).Path $localDir
    }
    $fileName = Split-Path -Leaf $Source
    $containerSource = "/data/$fileName"
    $dockerEndpoint = $EndpointUrl
    if ($dockerEndpoint -match "localhost|127\.0\.0\.1") {
        $dockerEndpoint = $dockerEndpoint -replace "localhost|127\.0\.0\.1", "host.docker.internal"
    }

    $dockerArgs = @("run", "--rm", "-v", "${localDir}:/data")
    $awsConfigPath = if ($env:USERPROFILE) { Join-Path $env:USERPROFILE ".aws" } else { "" }
    if ($Profile -and $awsConfigPath -and (Test-Path $awsConfigPath)) {
        $dockerArgs += @("-v", "${awsConfigPath}:/root/.aws:ro")
    }

    foreach ($name in @(
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
        "AWS_PROFILE"
    )) {
        $value = (Get-Item -Path "Env:$name" -ErrorAction SilentlyContinue).Value
        if ($value) {
            $dockerArgs += @("-e", "$name=$value")
        }
    }

    $dockerArgs += "amazon/aws-cli"
    $dockerArgs += @("s3", "cp", $containerSource, $Target, "--only-show-errors")
    if ($dockerEndpoint) {
        $dockerArgs += @("--endpoint-url", $dockerEndpoint)
    }
    if ($Region) {
        $dockerArgs += @("--region", $Region)
    }
    if ($Profile) {
        $dockerArgs += @("--profile", $Profile)
    }

    & docker @dockerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker aws s3 cp failed for $Source"
    }
}

    Write-Log "Uploading backup to $targetBase..." "Cyan"
    Invoke-AwsCopy -Source $dbDumpPath -Target "$targetBase/postgres.sql"
    Invoke-AwsCopy -Source $manifestPath -Target "$targetBase/manifest.txt"

    if ($KeepLocal -le 0) {
        Remove-Item -LiteralPath $backupDir -Recurse -Force
    }
    else {
        $existingBackups = Get-ChildItem -Path $OutputRoot -Directory |
            Where-Object { $_.Name -match '^\d{8}-\d{6}$' } |
            Sort-Object Name -Descending

        $existingBackups |
            Select-Object -Skip $KeepLocal |
            ForEach-Object {
                Write-Log "Removing old local backup: $($_.FullName)" "Yellow"
                Remove-Item -LiteralPath $_.FullName -Recurse -Force
            }
    }

    Write-Log "Backup uploaded to $targetBase" "Green"
}
catch {
    Write-Log "Backup failed: $($_.Exception.Message)" "Red"
    throw
}
