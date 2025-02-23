# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\main.py'],
    pathex=['D:\\123123\\src', 'D:\\123123'],
    binaries=[('D:\\123123\\resources\\ffmpeg.exe', '.'), ('D:\\123123\\resources\\ffprobe.exe', '.')],
    datas=[('LICENSE', '.'), ('src/__init__.py', 'src'), ('src/ui/__init__.py', 'src/ui'), ('src/video_tools/__init__.py', 'src/video_tools'), ('src/utils/__init__.py', 'src/utils')],
    hiddenimports=['PyQt6', 'cv2', 'ffmpeg', 'main_window', 'ui.compress_dialog', 'ui.split_dialog', 'ui.convert_dialog', 'ui.video_preview', 'video_tools.compressor', 'video_tools.splitter', 'utils', 'utils.resources'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [('v', None, 'OPTION')],
    name='FastMediaTool',
    debug=True,
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
    icon=['resources\\icon.ico'],
)
