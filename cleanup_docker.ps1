# Docker Cleanup Script for AdaptiveProjectManagerEnv
# This script removes all old containers and images to ensure a clean state

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "Docker Cleanup for AdaptiveProjectManagerEnv" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop and remove ALL containers related to this project
Write-Host "Step 1: Stopping and removing old containers..." -ForegroundColor Yellow

# Find and stop containers based on old image names
$oldImages = @("hustlers_env", "hustlers_env:latest", "adaptive-project-manager")
$containersRemoved = 0

foreach ($imageName in $oldImages) {
    Write-Host "  Checking for containers from image: $imageName" -ForegroundColor Gray
    
    # Get container IDs
    $containerIds = docker ps -a --filter "ancestor=$imageName" -q
    
    if ($containerIds) {
        foreach ($id in $containerIds) {
            Write-Host "    Stopping container: $id" -ForegroundColor Gray
            docker stop $id 2>&1 | Out-Null
            Write-Host "    Removing container: $id" -ForegroundColor Gray
            docker rm -f $id 2>&1 | Out-Null
            $containersRemoved++
        }
    }
}

Write-Host "  ✓ Removed $containersRemoved container(s)" -ForegroundColor Green
Write-Host ""

# Step 2: Remove dangling/stopped containers
Write-Host "Step 2: Removing any dangling containers..." -ForegroundColor Yellow
$danglingContainers = docker ps -a -f status=exited -q
if ($danglingContainers) {
    docker rm $danglingContainers 2>&1 | Out-Null
    Write-Host "  ✓ Cleaned up dangling containers" -ForegroundColor Green
} else {
    Write-Host "  ✓ No dangling containers found" -ForegroundColor Green
}
Write-Host ""

# Step 3: List current images
Write-Host "Step 3: Current Docker images:" -ForegroundColor Yellow
docker images | Select-String -Pattern "hustlers|adaptive-project-manager|REPOSITORY"
Write-Host ""

# Step 4: Remove old images but keep the latest adaptive-project-manager:latest
Write-Host "Step 4: Removing old images..." -ForegroundColor Yellow

# Remove old hustlers_env images (all of them)
$hustlersImages = docker images --filter "reference=hustlers_env" -q
if ($hustlersImages) {
    Write-Host "  Removing old hustlers_env images..." -ForegroundColor Gray
    foreach ($imageId in $hustlersImages) {
        docker rmi -f $imageId 2>&1 | Out-Null
    }
    Write-Host "  ✓ Removed hustlers_env images" -ForegroundColor Green
} else {
    Write-Host "  ✓ No hustlers_env images to remove" -ForegroundColor Green
}

# Remove old adaptive-project-manager images (except the latest)
$allAdaptiveImages = docker images --filter "reference=adaptive-project-manager" --format "{{.ID}} {{.Tag}} {{.CreatedAt}}"
if ($allAdaptiveImages) {
    $imageList = $allAdaptiveImages -split "`n"
    
    # Sort by creation date and keep only the most recent
    if ($imageList.Count -gt 1) {
        Write-Host "  Found $($imageList.Count) adaptive-project-manager images" -ForegroundColor Gray
        
        # Get all but the first (newest) image
        $imagesToRemove = $imageList | Select-Object -Skip 1
        
        foreach ($imageLine in $imagesToRemove) {
            $imageId = ($imageLine -split " ")[0]
            if ($imageId) {
                Write-Host "    Removing old image: $imageId" -ForegroundColor Gray
                docker rmi -f $imageId 2>&1 | Out-Null
            }
        }
        Write-Host "  ✓ Removed old adaptive-project-manager images" -ForegroundColor Green
    } else {
        Write-Host "  ✓ Only one adaptive-project-manager image exists (keeping it)" -ForegroundColor Green
    }
}
Write-Host ""

# Step 5: Clean up dangling images
Write-Host "Step 5: Removing dangling/untagged images..." -ForegroundColor Yellow
$danglingImages = docker images -f "dangling=true" -q
if ($danglingImages) {
    docker rmi $danglingImages 2>&1 | Out-Null
    Write-Host "  ✓ Removed dangling images" -ForegroundColor Green
} else {
    Write-Host "  ✓ No dangling images found" -ForegroundColor Green
}
Write-Host ""

# Step 6: System prune (optional but recommended)
Write-Host "Step 6: Docker system prune (removing unused data)..." -ForegroundColor Yellow
docker system prune -f 2>&1 | Out-Null
Write-Host "  ✓ System prune complete" -ForegroundColor Green
Write-Host ""

# Step 7: Final verification
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "Cleanup Complete! Current state:" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Running containers:" -ForegroundColor Yellow
docker ps
Write-Host ""

Write-Host "Project images:" -ForegroundColor Yellow
docker images | Select-String -Pattern "adaptive-project-manager|REPOSITORY"
Write-Host ""

Write-Host "✓ Cleanup successful!" -ForegroundColor Green
Write-Host "  - All old containers removed" -ForegroundColor Green
Write-Host "  - Old images cleaned up" -ForegroundColor Green
Write-Host "  - Only latest adaptive-project-manager:latest kept" -ForegroundColor Green
Write-Host ""
Write-Host "You can now run: uv run python inference.py" -ForegroundColor Cyan
Write-Host ""
