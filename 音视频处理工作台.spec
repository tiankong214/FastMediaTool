# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['d:\\123123\\src\\main.py'],
    pathex=['d:\\123123\\src'],
    binaries=[],
    datas=[('resources/ffmpeg.exe', '.'), ('resources/ffprobe.exe', '.'), ('resources/avcodec-61.dll', '.'), ('resources/avdevice-61.dll', '.'), ('resources/avfilter-10.dll', '.'), ('resources/avformat-61.dll', '.'), ('resources/avutil-59.dll', '.'), ('resources/postproc-58.dll', '.'), ('resources/swresample-5.dll', '.'), ('resources/swscale-8.dll', '.'), ('resources/icon.ico', 'resources'), ('src/resources', 'resources'), ('src/version.py', '.')],
    hiddenimports=['PIL', 'cv2', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.sip', 'moviepy', 'moviepy.editor', 'proglog', 'tqdm', 'decorator', 'imageio', 'imageio_ffmpeg', 'ui', 'video_tools', 'version', 'typing', 'src.ui', 'src.ui.main_window', 'src.video_tools', 'src.utils'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='音视频处理工作台',
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
    icon=['resources\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='音视频处理工作台',
)
