param(
    [switch]$SkipBuild,
    [string]$QdrantCollection = "deepface_smoke_$(Get-Date -Format 'yyyyMMddHHmmss')"
)

$ErrorActionPreference = "Stop"

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Command
}

function Wait-ForPostgres {
    for ($Attempt = 1; $Attempt -le 30; $Attempt++) {
        docker compose exec -T database pg_isready -U deepface -d deepface_access | Out-Null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 2
    }

    throw "PostgreSQL did not become ready in time."
}

function Wait-ForQdrant {
    for ($Attempt = 1; $Attempt -le 30; $Attempt++) {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:6333/healthz" -TimeoutSec 2 | Out-Null
            return
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }

    throw "Qdrant did not become ready in time."
}

$env:QDRANT_COLLECTION = $QdrantCollection

if (-not $SkipBuild) {
    Run-Step "Build backend and worker images" {
        docker compose build backend worker
    }
}

Run-Step "Start only smoke dependencies" {
    docker compose up -d database qdrant
}

Run-Step "Wait for PostgreSQL and Qdrant" {
    Wait-ForPostgres
    Wait-ForQdrant
}

Run-Step "Initialize database schema" {
    docker compose run --rm --no-deps backend python -m app.db.init_db
}

Run-Step "Run real DeepFace smoke test inside worker container" {
    docker compose run --rm --no-deps -v deepface_weights:/root/.deepface worker python -m app.smoke.deepface_smoke
}

Write-Host ""
Write-Host "DeepFace smoke test finished with Qdrant collection '$QdrantCollection'." -ForegroundColor Green
