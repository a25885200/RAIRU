# RAIRU.spec

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['Main.py'],
    pathex=['J:\\Remote Control Software\\Master\\dev_rairu\\RAIRU\\src'],
    binaries=[],
    datas=[
        ('assets/forms/*', 'assets/forms'),  # Include forms directory
        ('J:\\Remote Control Software\\Master\\dev_rairu\\RAIRU\\*', '.'),  # Include all files and folders
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RAIRU',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False to hide the console window
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RAIRU',
    outdir='j:\\Remote Control Software\\Master\\dist'
)