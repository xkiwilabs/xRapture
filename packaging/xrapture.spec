# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the xRapture macOS app bundle.

Build:  bash packaging/build_app.sh   (or: pyinstaller packaging/xrapture.spec)

The heavy ML/audio dependencies (faster-whisper, ctranslate2, av, …) ship binary
libraries and data files, so we collect_all() them rather than relying on hooks.
The bundle is a menu-bar agent (LSUIElement) and declares microphone usage.
"""

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in (
    "faster_whisper", "ctranslate2", "av", "sounddevice",
    "plyer", "pystray", "tokenizers", "huggingface_hub", "onnxruntime",
):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:  # optional/transitive deps may be absent
        print(f"[spec] collect_all({pkg}) skipped: {exc}")

# plyer loads its backend lazily; PyInstaller can't see it statically.
hiddenimports += ["plyer.platforms.macosx.notification", "pyobjus"]


a = Analysis(
    ["xrapture_launch.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
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
    [],
    exclude_binaries=True,
    name="xRapture",
    console=False,            # windowed → no terminal needed
    argv_emulation=False,
    icon="xRapture.icns",
)
coll = COLLECT(exe, a.binaries, a.datas, name="xRapture")

app = BUNDLE(
    coll,
    name="xRapture.app",
    icon="xRapture.icns",
    bundle_identifier="com.xkiwilabs.xrapture",
    info_plist={
        "LSUIElement": True,  # menu-bar agent (no Dock icon)
        "NSMicrophoneUsageDescription":
            "xRapture records your microphone to transcribe meetings and conversations.",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleName": "xRapture",
        "CFBundleDisplayName": "xRapture",
    },
)
