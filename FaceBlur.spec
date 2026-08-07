# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Автоматический сбор зависимостей, тем и ресурсов для CustomTkinter
ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all('customtkinter')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=ctk_binaries,
    datas=[
        ('yolov8s-face.pt', '.'),
        ('app_icon.icns', '.')
    ] + ctk_datas,
    hiddenimports=[
        'PIL._tkinter_finder',
        'imageio_ffmpeg',
        'customtkinter',
        'lap',
        'lapx'
    ] + ctk_hiddenimports,
    hookspath=[],
    hooksconfig={},
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FaceBlur Studio Executable',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.icns',
)

app = BUNDLE(
    exe,
    name='FaceBlur Studio.app',
    icon='app_icon.icns',
    bundle_identifier='com.sirdimitry.faceblur',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False'
    }
)