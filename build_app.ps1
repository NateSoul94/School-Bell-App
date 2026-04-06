#!/usr/bin/env pwsh
"""
Build script for School Bell Application
Builds the application using PyInstaller with the custom spec file.

Usage:
    .\build_app.ps1
    or
    powershell -ExecutionPolicy Bypass -File build_app.ps1
"""

# Build configuration
$AppName = "SchoolBellApp"
$SpecFile = "SchoolBellApp.spec"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Building School Bell Application" -ForegroundColor Cyan  
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if PyInstaller is installed
Write-Host "Checking PyInstaller installation..." -ForegroundColor Yellow
try {
    $pyinstallerVersion = & python -m PyInstaller --version 2>$null
    Write-Host "✓ PyInstaller found: $pyinstallerVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ PyInstaller not found. Installing..." -ForegroundColor Red
    & python -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install PyInstaller. Please install it manually:" -ForegroundColor Red
        Write-Host "pip install pyinstaller" -ForegroundColor White
        exit 1
    }
    Write-Host "✓ PyInstaller installed successfully" -ForegroundColor Green
}

Write-Host ""

# Check if spec file exists
if (-not (Test-Path $SpecFile)) {
    Write-Host "✗ Spec file not found: $SpecFile" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Spec file found: $SpecFile" -ForegroundColor Green
Write-Host ""

# Clean previous builds
Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
    Write-Host "✓ Removed build directory" -ForegroundColor Green
}
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"  
    Write-Host "✓ Removed dist directory" -ForegroundColor Green
}
if (Test-Path "$AppName.exe") {
    Remove-Item -Force "$AppName.exe"
    Write-Host "✓ Removed old executable" -ForegroundColor Green
}

Write-Host ""

# Build the application
Write-Host "Building application..." -ForegroundColor Yellow
Write-Host "Command: python -m PyInstaller $SpecFile" -ForegroundColor Gray

$buildStart = Get-Date
& python -m PyInstaller $SpecFile

if ($LASTEXITCODE -eq 0) {
    $buildEnd = Get-Date
    $buildTime = $buildEnd - $buildStart
    
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "✓ BUILD SUCCESSFUL!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "Build time: $($buildTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Green
    Write-Host ""
    
    # Check if executable was created
    $exePath = "dist\$AppName.exe"
    if (Test-Path $exePath) {
        $fileInfo = Get-Item $exePath
        $fileSizeMB = [math]::Round($fileInfo.Length / 1MB, 2)
        
        Write-Host "Executable created: $exePath" -ForegroundColor Green
        Write-Host "File size: $fileSizeMB MB" -ForegroundColor Green
        Write-Host ""
        
        # Test the executable (optional)
        Write-Host "To test the executable:" -ForegroundColor Cyan
        Write-Host "  cd dist" -ForegroundColor White
        Write-Host "  .\$AppName.exe" -ForegroundColor White
        Write-Host ""
        
        # Show what was excluded
        Write-Host "Note: Audio files were excluded as requested." -ForegroundColor Yellow
        Write-Host "Users will need to add their own audio files to:" -ForegroundColor Yellow
        Write-Host "  %APPDATA%\Ali AHK Qasem\SchoolBellApp\audio_files\" -ForegroundColor White
        
    } else {
        Write-Host "✗ Executable not found at expected location: $exePath" -ForegroundColor Red
    }
    
} else {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Red
    Write-Host "✗ BUILD FAILED!" -ForegroundColor Red  
    Write-Host "============================================" -ForegroundColor Red
    Write-Host "Check the output above for error details." -ForegroundColor Red
    Write-Host ""
    Write-Host "Common solutions:" -ForegroundColor Yellow
    Write-Host "1. Install missing dependencies: pip install PyQt6 pygame" -ForegroundColor White
    Write-Host "2. Check that all files in the spec exist" -ForegroundColor White
    Write-Host "3. Run with verbose mode: python -m PyInstaller --log-level DEBUG $SpecFile" -ForegroundColor White
}

Write-Host ""