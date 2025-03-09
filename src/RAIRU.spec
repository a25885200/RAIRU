# RAIRU.spec

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['Run.py'],
    pathex=['J:\\Remote Control Software\\Master\\dev_rairu\\RAIRU\\src'],
    binaries=[
        # Add additional binaries here, e.g.,
        # ('path/to/binary.exe', 'destination_folder'),
    ],
    datas=[
        ('assets/forms/*', 'assets/forms'),  # Include forms directory
        ('assets/configs/*', 'assets/configs'),  # Include configs directory
        ('assets/img/*', 'assets/img'),  # Include img directory
        ('J:\\Remote Control Software\\Master\\dev_rairu\\RAIRU\\LICENSE.txt', '.'),  # Include LICENSE
        ('J:\\Remote Control Software\\Master\\dev_rairu\\RAIRU\\pyproject.toml', '.'),  # Include pyproject
        ('J:\\Remote Control Software\\Master\\dev_rairu\\RAIRU\\README.md', '.'),  # Include README
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
    name='RAIRU-v0.1.1-alpha',  # Include version in the executable name
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
    name='RAIRU-v0.1.1-alpha',  # Include version in the collected folder name
    outdir='J:\\Remote Control Software\\Master\\dist'  # Ensure this path exists
)