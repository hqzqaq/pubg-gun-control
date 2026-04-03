# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('pystray')
hiddenimports += ['PIL', 'PIL.Image', 'PIL.ImageDraw']

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('src/pubg_gun_control', 'pubg_gun_control')],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=True,
    name='PUBG-Gun-Control',
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='PUBG-Gun-Control',
)
