# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files



# Modelos spacy
spacy_es = 'C:\\Users\\usuario\\OneDrive\\Escritorio\\Mis_Proyectos\\Translator\\venv\\Lib\\site-packages\\es_core_news_md\\es_core_news_md-3.8.0'
spacy_en = 'C:\\Users\\usuario\\OneDrive\\Escritorio\\Mis_Proyectos\\Translator\\venv\\Lib\\site-packages\\en_core_web_md\\en_core_web_md-3.8.0'

spacy_models = [
    (spacy_es, 'spacy_models/es_core_news_md'),
    (spacy_en, 'spacy_models/en_core_web_md')
]

# Verificar la existencia de la carpeta 'config' y agregarla a los datos de PyInstaller
config_dir = os.path.join(os.getcwd(), 'config')
config_files = [(os.path.join(config_dir, f), 'config') for f in os.listdir(config_dir)]


datas = [
    ('ui/RTT_dock.ui', 'ui'),
    ('ui/imgs/icon.ico', 'ui/imgs'),
    ('ui/imgs', 'ui/imgs'),
    *config_files,
    ('./credentials/service_account.json', 'credentials'),
    ('modules/audio_handler.py', 'modules'),
    ('modules/speech_processing.py', 'modules'),
    ('modules/circular_buffer.py', 'modules'),
    ('package.json', '.'),
    ('package-lock.json', '.'),
    ('C:/Ffmpeg/ffmpeg.exe', './Ffmpeg'),
    *spacy_models,
    *collect_data_files('pyaudio'),  #Todos los archivos de pyaudio
    *collect_data_files('whisper', include_py_files=True),  # Incluye archivos no Python de whisper
    *collect_data_files('google', include_py_files=True),  # Incluye archivos no Python de google
    *collect_data_files('grpc', include_py_files=True),  
    *collect_data_files('grpc_status', include_py_files=True),  
    *collect_data_files('proto', include_py_files=True),  # Incluye archivos no Python de proto
    *collect_data_files('httpx', include_py_files=True),
    *collect_data_files('urllib3', include_py_files=True),
]

a = Analysis(
    ['C:\\Users\\usuario\\OneDrive\\Escritorio\\Mis_Proyectos\\Translator\\ui\\interfaz.py'],
    pathex=[],
    binaries=[
        ('C:/Ffmpeg/ffmpeg.exe', 'Ffmpeg'),
    ],
    datas=datas,
    hiddenimports=collect_submodules('spacy') + collect_submodules('numba') + collect_submodules('whisper') + ['wave', 'webrtcvad', 'grpc._cython.cygrpc','ffmpeg', 'openai-whisper', 'httpx', 'urllib3', 'spacy', 'pyaudio', 'hpack', 'google.cloud'],
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
    name='RTT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ui/imgs/icon.ico',  # Ruta al icono
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='interfaz',
)