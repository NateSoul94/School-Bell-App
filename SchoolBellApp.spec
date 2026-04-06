# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for School Bell Application (Refactored Version)
Created for the new organized folder structure.

This spec file:
- Uses the new organized structure with src/ directory
- Includes necessary assets (icons, images) but excludes audio_files
- Optimized for Windows deployment
- Includes all required modules and dependencies
"""

import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

# Application paths
app_name = 'SchoolBellApp'
main_script = 'main.py'

# Define paths relative to spec file location
spec_root = SPECPATH
src_path = os.path.join(spec_root, 'src')
assets_path = os.path.join(spec_root, 'assets')
docs_path = os.path.join(spec_root, 'docs')

# Data files to include (only essential assets - no audio files, database, or config)
datas = [
    # Icons
    (os.path.join(assets_path, 'icons', 'icon.ico'), 'assets/icons'),
    (os.path.join(assets_path, 'icons', 'icon.png'), 'assets/icons'),
]

# Remove None entries
datas = [item for item in datas if item is not None]

# Hidden imports (modules that PyInstaller might miss)
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui', 
    'PyQt6.QtWidgets',
    'pygame',
    'sqlite3',
    'logging',
    'threading',
    'datetime',
    'pathlib',
    'json',
    'os',
    'sys',
    'gc',
    'functools',
    'platform',
    'psutil',  # For memory monitoring
]

# Binaries to exclude (reduce file size)
excludes = [
    'tkinter',
    'matplotlib',
    'numpy',
    'scipy',
    'pandas',
    'PIL',
    'cv2',
    'tensorflow',
    'torch',
    'django',
    'flask',
]

# Path to search for modules (include src directory)
pathex = [
    spec_root,
    src_path,
]

# Analysis configuration
a = Analysis(
    [main_script],
    pathex=pathex,
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# No audio files or database included - they are handled by the application at runtime

# Create PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging, False for release
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(assets_path, 'icons', 'icon.ico'),  # Application icon
    version_info={
        'version': (1, 0, 0, 0),
        'company_name': 'Ali AHK Qasem',
        'file_description': 'School Bell Application - Refactored',
        'product_name': 'School Bell App',
        'product_version': '1.0.0',
    }
)

# Optional: Create a distribution folder (COLLECT) - uncomment if needed
# This creates a folder with the executable and all dependencies
# Useful for debugging or when you need separate files
"""
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name + '_dist'
)
"""