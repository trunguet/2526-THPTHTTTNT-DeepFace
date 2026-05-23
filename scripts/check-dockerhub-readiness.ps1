param(
    [string]$Namespace = $env:DOCKERHUB_NAMESPACE,
    [string]$ImageTag = $(if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "latest" }),
    [switch]$SkipRemote
)

$ErrorActionPreference = "Stop"

$composeRepositories = @(
    "deepface-backend",
    "deepface-worker",
    "deepface-frontend-user",
    "deepface-frontend-home",
    "deepface-frontend-admin"
)

$helmRepositories = @(
    "deepface-backend",
    "deepface-worker",
    "deepface-frontend-user",
    "deepface-frontend-admin"
)

function Write-Step {
    param([string]$Name)

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
}

function Assert-TextContains {
    param(
        [string]$Text,
        [string]$Expected
    )

    if ($Text -notlike "*$Expected*") {
        throw "Expected text was not found: $Expected"
    }
}

if ([string]::IsNullOrWhiteSpace($Namespace) -or $Namespace -eq "your-dockerhub-username") {
    throw "Set DOCKERHUB_NAMESPACE to your real Docker Hub username/namespace before checking readiness."
}

Write-Step "Docker Compose image names"
$previousNamespace = $env:DOCKERHUB_NAMESPACE
$previousImageTag = $env:IMAGE_TAG
$env:DOCKERHUB_NAMESPACE = $Namespace
$env:IMAGE_TAG = $ImageTag
try {
    $composeImages = docker compose config --images | Out-String
} finally {
    $env:DOCKERHUB_NAMESPACE = $previousNamespace
    $env:IMAGE_TAG = $previousImageTag
}
foreach ($repo in $composeRepositories) {
    Assert-TextContains -Text $composeImages -Expected "$Namespace/${repo}:$ImageTag"
}

Write-Step "Helm image names"
$helmOutput = docker run --rm -v "${PWD}:/workspace" -w /workspace alpine/helm:3.15.4 template deepface-access helm/deepface-access --set global.imageRegistry=$Namespace --set global.imageTag=$ImageTag | Out-String
foreach ($repo in $helmRepositories) {
    Assert-TextContains -Text $helmOutput -Expected "$Namespace/${repo}:$ImageTag"
}

if ($SkipRemote) {
    Write-Host ""
    Write-Host "Docker Hub local config checks passed. Remote Docker Hub repository/tag checks were skipped." -ForegroundColor Green
    exit 0
}

Write-Step "Docker Hub remote repositories"
foreach ($repo in $composeRepositories) {
    $tagUrl = "https://hub.docker.com/v2/repositories/$Namespace/$repo/tags/$ImageTag/"
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $tagUrl -TimeoutSec 15
        if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
            throw "Unexpected status code $($response.StatusCode)"
        }
        Write-Host "Found $Namespace/${repo}:$ImageTag"
    } catch {
        throw "Docker Hub tag is not reachable yet: $Namespace/${repo}:$ImageTag. Create the repository and push the image, or rerun with -SkipRemote before the first publish."
    }
}

Write-Host ""
Write-Host "Docker Hub readiness checks passed." -ForegroundColor Green
