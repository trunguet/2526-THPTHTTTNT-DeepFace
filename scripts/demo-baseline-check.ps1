param(
    [switch]$StaticOnly
)

$ErrorActionPreference = "Stop"

$NginxPort = if ($env:NGINX_PORT) { $env:NGINX_PORT } else { "8080" }
$PrometheusPort = if ($env:PROMETHEUS_PORT) { $env:PROMETHEUS_PORT } else { "9090" }
$AlertmanagerPort = if ($env:ALERTMANAGER_PORT) { $env:ALERTMANAGER_PORT } else { "9093" }
$GrafanaPort = if ($env:GRAFANA_PORT) { $env:GRAFANA_PORT } else { "3000" }

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Command
}

function Assert-PathExists {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        throw "Missing required path: $Path"
    }
}

function Test-HttpEndpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string[]]$ExpectedText = @()
    )

    Write-Host "Checking ${Name}: $Url"
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 8
    foreach ($text in $ExpectedText) {
        if ($response.Content -notlike "*$text*") {
            throw "Endpoint $Url did not contain expected text: $text"
        }
    }
}

Run-Step "Static project files" {
    @(
        "docker-compose.yml",
        "README.md",
        "frontend/home/index.html",
        "frontend/home/Dockerfile",
        "docs/demo-checklist.md",
        "docs/roadmap.md",
        "docs/setup.md",
        "helm/deepface-access/values.yaml",
        "monitoring/prometheus/prometheus.yml",
        "monitoring/grafana/dashboards/deepface-access-overview.json",
        "scripts/check-dockerhub-readiness.ps1",
        "scripts/dev.ps1",
        "scripts/smoke-deepface.ps1",
        "scripts/backup.ps1"
    ) | ForEach-Object { Assert-PathExists $_ }
}

Run-Step "Docker Compose config" {
    docker compose config --quiet
}

if ($StaticOnly) {
    Write-Host ""
    Write-Host "Static baseline checks passed. Start the stack before runtime checks." -ForegroundColor Green
    exit 0
}

Run-Step "Docker Compose running services" {
    docker compose ps
}

Run-Step "Backend health and metrics" {
    Test-HttpEndpoint -Name "backend health" -Url "http://localhost:8000/health" -ExpectedText @('"database":"ok"', '"redis":"ok"')
    Test-HttpEndpoint -Name "backend metrics" -Url "http://localhost:8000/metrics" -ExpectedText @("deepface_backend_up", "deepface_database_up", "deepface_redis_up", "deepface_queue_length")
}

Run-Step "Frontend and nginx routes" {
    Test-HttpEndpoint -Name "home frontend" -Url "http://localhost:$NginxPort" -ExpectedText @("DeepFace", "ADMIN", "Nhan Vien")
    Test-HttpEndpoint -Name "user frontend" -Url "http://localhost:5173/user/"
    Test-HttpEndpoint -Name "nginx user route" -Url "http://localhost:$NginxPort/user/"
    Test-HttpEndpoint -Name "admin frontend" -Url "http://localhost:5174/admin/"
    Test-HttpEndpoint -Name "nginx health route" -Url "http://localhost:$NginxPort/health" -ExpectedText @('"database":"ok"', '"redis":"ok"')
    Test-HttpEndpoint -Name "nginx api route" -Url "http://localhost:$NginxPort/api/health" -ExpectedText @('"database":"ok"', '"redis":"ok"')
}

Run-Step "Monitoring endpoints" {
    Test-HttpEndpoint -Name "prometheus" -Url "http://localhost:$PrometheusPort/-/ready"
    Test-HttpEndpoint -Name "alertmanager" -Url "http://localhost:$AlertmanagerPort/-/ready"
    Test-HttpEndpoint -Name "grafana" -Url "http://localhost:$GrafanaPort/api/health"
}

Run-Step "Storage and vector services" {
    Test-HttpEndpoint -Name "qdrant" -Url "http://localhost:6333/healthz"
    Test-HttpEndpoint -Name "minio" -Url "http://localhost:9000/minio/health/ready"
}

Run-Step "Redis queues" {
    docker compose exec -T redis redis-cli llen embedding_jobs
    docker compose exec -T redis redis-cli llen access_jobs
}

Write-Host ""
Write-Host "Runtime baseline checks passed. Run .\scripts\smoke-deepface.ps1 -SkipBuild for AI runtime proof." -ForegroundColor Green
