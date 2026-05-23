param(
    [switch]$Build,
    [switch]$Seed
)

$ErrorActionPreference = "Stop"

$NginxPort = if ($env:NGINX_PORT) { $env:NGINX_PORT } else { "8080" }
$PrometheusPort = if ($env:PROMETHEUS_PORT) { $env:PROMETHEUS_PORT } else { "9090" }
$AlertmanagerPort = if ($env:ALERTMANAGER_PORT) { $env:ALERTMANAGER_PORT } else { "9093" }
$GrafanaPort = if ($env:GRAFANA_PORT) { $env:GRAFANA_PORT } else { "3000" }

$ComposeArgs = @("compose", "up", "-d")
if ($Build) {
    $ComposeArgs += "--build"
}

Write-Host "Starting DeepFace Access stack..." -ForegroundColor Cyan
docker @ComposeArgs

Write-Host ""
Write-Host "Stack is starting. Useful URLs:" -ForegroundColor Green
Write-Host "- Backend health: http://localhost:8000/health"
Write-Host "- Backend docs:   http://localhost:8000/docs"
Write-Host "- Home:           http://localhost:$NginxPort"
Write-Host "- User app:       http://localhost:$NginxPort/user/"
Write-Host "- User direct:    http://localhost:5173/user/"
Write-Host "- Admin app:      http://localhost:5174"
Write-Host "- Nginx entry:    http://localhost:$NginxPort"
Write-Host "- MinIO console:  http://localhost:9001"
Write-Host "- Prometheus:     http://localhost:$PrometheusPort"
Write-Host "- Alertmanager:   http://localhost:$AlertmanagerPort"
Write-Host "- Grafana:        http://localhost:$GrafanaPort"

if ($Seed) {
    Write-Host ""
    Write-Host "Seeding demo users..." -ForegroundColor Cyan
    docker compose run --rm db-seed
}
