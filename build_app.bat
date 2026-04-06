@echo off
REM Build script for School Bell Application
REM Simple batch file version

echo ============================================
echo Building School Bell Application  
echo ============================================
echo.

REM Check PyInstaller
echo Checking PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo Failed to install PyInstaller
        echo Please run: pip install pyinstaller
        pause
        exit /b 1
    )
)
echo PyInstaller is ready

echo.
echo Building application...
echo Command: python -m PyInstaller SchoolBellApp.spec

REM Clean previous builds
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"  
if exist "SchoolBellApp.exe" del /q "SchoolBellApp.exe"

REM Build
python -m PyInstaller SchoolBellApp.spec

if errorlevel 1 (
    echo.
    echo ============================================
    echo BUILD FAILED!
    echo ============================================
    echo Check the output above for errors
    pause
    exit /b 1
) else (
    echo.
    echo ============================================
    echo BUILD SUCCESSFUL!
    echo ============================================
    if exist "dist\SchoolBellApp.exe" (
        echo Executable created: dist\SchoolBellApp.exe
        echo.
        echo Note: Audio files excluded as requested
        echo Users need to add audio files to:
        echo   %%APPDATA%%\Ali AHK Qasem\SchoolBellApp\audio_files\
    )
    echo.
    echo To test: cd dist ^&^& SchoolBellApp.exe
)

pause