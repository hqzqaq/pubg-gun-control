# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('pystray')
hiddenimports += ['PIL', 'PIL.Image', 'PIL.ImageDraw']

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # 注意：如果你的代码里是 import src.pubg_gun_control，
    # 确保打包后的路径能被 Python 识别
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
    a.binaries,        # 关键修改：将 binaries 加入此处
    a.zipfiles,        # 关键修改：将 zipfiles 加入此处
    a.datas,           # 关键修改：将 datas 加入此处
    [],
    exclude_binaries=False, # 必须设为 False，否则依赖库会被留在外面
    name='PUBG-Gun-Control',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,         # 如果追求启动速度可以保持 False，追求体积可设为 True
    console=False,     # True 会弹出黑窗口，False 则不会
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 注意：删除了原先的 coll = COLLECT(...) 部分