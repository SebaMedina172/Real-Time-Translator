# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_dynamic_libs, collect_all

block_cipher = None

# Recoge TODO lo de whisper (código, assets, librerías nativas)
whisper_datas, whisper_binaries, whisper_hiddenimports = collect_all('whisper')

# Módulos que PyInstaller no detecta automáticamente
hidden_imports = [
    'wave','audioop','pysbd'
] + collect_submodules('webrtcvad') + collect_submodules('torch') + whisper_hiddenimports

# Recoge las librerías nativas de torch
torch_binaries = collect_dynamic_libs('torch')

a = Analysis(
    ['ui\\Interfaz.py'],    # tu script principal
    pathex=[],
    binaries= torch_binaries + whisper_binaries,   # <-- lista plana
    datas=[
        ('config', 'config'),
        ('modules', 'modules'),
        ('ui', 'ui'),
        ('ffmpeg/ffmpeg.exe', '.'),
        ('ui\\imgs\\icon.ico','ui\\imgs'),
    ] + whisper_datas,                            # <-- datos de whisper
    hiddenimports=hidden_imports,
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
    [],
    exclude_binaries=True,
    name='TranslatorApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='ui\\imgs\\icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RTT'
)
