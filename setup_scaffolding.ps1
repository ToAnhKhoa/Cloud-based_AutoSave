# PowerShell Scaffolding Script for Cloud Save System
# Save this as scaffolding.ps1 and run it from the root directory.

# Root Directory paths
$backendDir = "backend"
$clientDir = "client"

# Backend Directories
$backendDirs = @(
    "$backendDir\app\api\routes",
    "$backendDir\app\services",
    "$backendDir\app\db",
    "$backendDir\app\models",
    "$backendDir\app\schemas",
    "$backendDir\app\core",
    "$backendDir\storage"
)

# Backend Files
$backendFiles = @(
    "$backendDir\requirements.txt",
    "$backendDir\.env",
    "$backendDir\app\__init__.py",
    "$backendDir\app\main.py",
    "$backendDir\app\api\__init__.py",
    "$backendDir\app\api\dependencies.py",
    "$backendDir\app\api\routes\__init__.py",
    "$backendDir\app\api\routes\auth.py",
    "$backendDir\app\api\routes\sync.py",
    "$backendDir\app\services\__init__.py",
    "$backendDir\app\services\auth_service.py",
    "$backendDir\app\services\sync_service.py",
    "$backendDir\app\db\__init__.py",
    "$backendDir\app\db\database.py",
    "$backendDir\app\models\__init__.py",
    "$backendDir\app\models\user.py",
    "$backendDir\app\models\app_data.py",
    "$backendDir\app\schemas\__init__.py",
    "$backendDir\app\schemas\user.py",
    "$backendDir\app\schemas\sync.py",
    "$backendDir\app\core\__init__.py",
    "$backendDir\app\core\config.py",
    "$backendDir\app\core\security.py",
    "$backendDir\storage\.keep"
)

# Client Directories
$clientDirs = @(
    "$clientDir\gui",
    "$clientDir\core"
)

# Client Files
$clientFiles = @(
    "$clientDir\requirements.txt",
    "$clientDir\.env",
    "$clientDir\main.py",
    "$clientDir\gui\__init__.py",
    "$clientDir\gui\app.py",
    "$clientDir\gui\login.py",
    "$clientDir\gui\settings.py",
    "$clientDir\core\__init__.py",
    "$clientDir\core\api_client.py",
    "$clientDir\core\watcher.py",
    "$clientDir\core\sync_manager.py"
)

# Combine all directories and files
$allDirs = $backendDirs + $clientDirs
$allFiles = $backendFiles + $clientFiles

# Create directories
foreach ($dir in $allDirs) {
    if (-not (Test-Path -Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "Created directory: $dir" -ForegroundColor Green
    }
}

# Create empty files
foreach ($file in $allFiles) {
    if (-not (Test-Path -Path $file)) {
        New-Item -ItemType File -Path $file | Out-Null
        Write-Host "Created file: $file" -ForegroundColor Yellow
    }
}

Write-Host "Scaffolding complete!" -ForegroundColor Cyan
