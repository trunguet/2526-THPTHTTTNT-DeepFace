$ErrorActionPreference = "Stop"

Write-Host "Seeding DeepFace Access demo data..." -ForegroundColor Cyan
docker compose run --rm db-seed
