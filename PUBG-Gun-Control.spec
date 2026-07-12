# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('voice', 'voice'),
        ('templates', 'templates'),
        ('config.json', '.'),
        ('1.2.2-2024.5.20.-GHUB.-github.lua', '.'),
    ],
    hiddenimports=[
        'keyboard',
        'mouse',
        'pystray',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'pubg_gun_control.config_manager',
        'pubg_gun_control.input_listener',
        'pubg_gun_control.overlay_window',
        'pubg_gun_control.voice_prompt',
        'pubg_gun_control.settings_window',
        'pubg_gun_control.tray_icon',
        'pubg_gun_control.rec_lua_writer',
        'pubg_gun_control.recognizer',
        'pubg_gun_control.template_capture',
        'pubg_gun_control.roi_selector',
        'pubg_gun_control.lua_generator',
        'pubg_gun_control.lua_parser',
        'pubg_gun_control.ballistic_data',
        'pubg_gun_control.ballistic_analyzer',
        'pubg_gun_control.preset_manager',
        'pubg_gun_control.editor_ui',
        'pubg_gun_control.editor_ui.main_window',
        'pubg_gun_control.editor_ui.gun_list_panel',
        'pubg_gun_control.editor_ui.gun_detail_panel',
        'pubg_gun_control.editor_ui.attachment_panel',
        'pubg_gun_control.editor_ui.trajectory_view',
        'pubg_gun_control.editor_ui.preset_dialog',
        'cv2',
        'numpy',
        'skimage',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PUBG-Gun-Control',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
