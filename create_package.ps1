# BVH Retarget 打包脚本
# 将扩展打包为 zip 文件，用于 Blender 安装

$ErrorActionPreference = "Stop"

# 获取当前目录
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 从 __init__.py 读取版本号（主要来源）
$Version = "0.0.0"
$InitFile = Join-Path $SourceDir "__init__.py"
if (Test-Path $InitFile) {
    $Content = Get-Content $InitFile -Raw
    if ($Content -match '"version":\s*\((\d+),\s*(\d+),\s*(\d+)\)') {
        $Version = "$($Matches[1]).$($Matches[2]).$($Matches[3])"
    }
}

# 校验 blender_manifest.toml 版本一致性
$ManifestFile = Join-Path $SourceDir "blender_manifest.toml"
if (Test-Path $ManifestFile) {
    $Content = Get-Content $ManifestFile -Raw
    if ($Content -match 'version\s*=\s*"([^"]+)"') {
        $ManifestVersion = $Matches[1]
        if ($ManifestVersion -ne $Version) {
            Write-Host "WARNING: blender_manifest.toml version ($ManifestVersion) != __init__.py version ($Version)" -ForegroundColor Yellow
        }
    }
}

# 生成文件名
$Timestamp = Get-Date -Format "yyyyMMdd"
$ZipFilename = "bvh_retarget_${Version}_${Timestamp}.zip"
$ZipPath = Join-Path $SourceDir $ZipFilename

Write-Host "========================================"
Write-Host " BVH Retarget Package Builder"
Write-Host "========================================"
Write-Host ""
Write-Host "Version: $Version"
Write-Host "Timestamp: $Timestamp"
Write-Host "Output: $ZipFilename"
Write-Host ""

# 清理旧的zip文件
if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}

# 要打包的文件
$FilesToInclude = @(
    "__init__.py",
    "blender_manifest.toml",
    "operators.py",
    "panels.py",
    "properties.py",
    "retarget.py",
    "ui_list.py"
)

# 创建临时目录
$TempDir = Join-Path $SourceDir "temp_package"
if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempDir | Out-Null
$TempBvhDir = Join-Path $TempDir "bvh_retarget"
New-Item -ItemType Directory -Path $TempBvhDir | Out-Null

# 复制文件到临时目录
Write-Host "Copying files..."
foreach ($File in $FilesToInclude) {
    $SourceFile = Join-Path $SourceDir $File
    $DestFile = Join-Path $TempBvhDir $File
    if (Test-Path $SourceFile) {
        Copy-Item $SourceFile $DestFile
        Write-Host "  Added: $File"
    } else {
        Write-Host "  Warning: $File not found, skipping"
    }
}

# 创建zip文件
Write-Host ""
Write-Host "Creating zip archive..."
Compress-Archive -Path $TempBvhDir -DestinationPath $ZipPath -Force

# 清理临时目录
Remove-Item $TempDir -Recurse -Force

# 检查zip文件是否创建成功
if (Test-Path $ZipPath) {
    $FileSize = (Get-Item $ZipPath).Length
    $SizeKB = [math]::Round($FileSize / 1024, 1)
    
    Write-Host ""
    Write-Host "========================================"
    Write-Host " Package created successfully!"
    Write-Host "========================================"
    Write-Host ""
    Write-Host "File: $ZipFilename"
    Write-Host "Size: $SizeKB KB"
    Write-Host ""
    Write-Host "To install in Blender:"
    Write-Host "1. Edit > Preferences > Add-ons > Install from Disk"
    Write-Host "2. Select: $ZipFilename"
    Write-Host "3. Enable 'BVH Retarget'"
} else {
    Write-Host ""
    Write-Host "ERROR: Failed to create zip file!"
}

Write-Host ""
