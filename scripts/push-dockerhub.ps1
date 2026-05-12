param(
  [Parameter(Mandatory = $true)]
  [string]$Namespace,

  [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

$images = @(
  @{ Local = "deepface_backend:latest"; Remote = "$Namespace/deepface-backend:$Tag" },
  @{ Local = "deepface_frontend_home:latest"; Remote = "$Namespace/deepface-frontend-home:$Tag" },
  @{ Local = "deepface_frontend_admin:latest"; Remote = "$Namespace/deepface-frontend-admin:$Tag" },
  @{ Local = "deepface_frontend_user:latest"; Remote = "$Namespace/deepface-frontend-user:$Tag" },
  @{ Local = "deepface_backup:latest"; Remote = "$Namespace/deepface-backup:$Tag" }
)

Write-Host "[build] Building project images..."
docker compose build backend frontend-home frontend-admin frontend-user backup

foreach ($image in $images) {
  Write-Host "[tag] $($image.Local) -> $($image.Remote)"
  docker tag $image.Local $image.Remote
}

foreach ($image in $images) {
  Write-Host "[push] $($image.Remote)"
  docker push $image.Remote
}

Write-Host ""
Write-Host "Docker Hub images pushed:"
foreach ($image in $images) {
  Write-Host "  $($image.Remote)"
}
Write-Host ""
Write-Host "Run from pulled images with:"
Write-Host "  docker compose --env-file .env.dockerhub -f docker-compose.images.yml up -d"
