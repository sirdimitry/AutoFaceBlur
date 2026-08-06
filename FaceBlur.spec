# -*- mode: python ; coding: utf-8 -*-

import os
import customtkinter
import ultralytics
import imageio_ffmpeg

ctk_path = os.path.dirname(customtkinter.__file__)
ultralytics_path = os.path.dirname(ultralytics.__file__)
ffmpeg_path = os.path.dirname(imageio_ffmpeg.__file__)

datas = [
    ('yolov8s-face.pt', '.'),
    ('AutoBlureFace_icon.png', '.'),
    (ctk_path, 'customtkinter'),
    (ultralytics_path, 'ultralytics'),
    (ffmpeg_path, 'imageio_ffmpeg'),
]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PIL._tkinter_finder',
        'customtkinter',
        'ultralytics',
        'imageio_ffmpeg',
        'cv2',
        'numpy'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter.test'],
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
    name='FaceBlur',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FaceBlur',
)

app = BUNDLE(
    coll,
    name='FaceBlur Studio.app',
    icon='app_icon.icns',
    bundle_identifier='com.faceblur.studio',
)
