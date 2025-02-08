import sys
import os
# Agregar la carpeta raíz del proyecto al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from logging.handlers import RotatingFileHandler

# Configuración del logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('app.log', maxBytes=5 * 1024 * 1024, backupCount=5)  # 5 MB por archivo, hasta 5 backups
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

import wave
import pyaudio
import webrtcvad
import numpy as np
import threading
import time
import asyncio

# Importamos el worker desde el módulo creado (workers.py)
from worker import AudioProcessingWorker

# Importamos el buffer circular
from modules.circular_buffer import CircularBuffer

# Configuración de PyQt para el ThreadPool
from PyQt5.QtCore import QThreadPool

import config.configuracion as cfg
from config.configuracion import settings, load_settings, calcular_valores_dinamicos

# Cargar la configuración
load_settings()
calcular_valores_dinamicos()

# Configuración de audio
audio = pyaudio.PyAudio()
stream = audio.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=settings["RATE"],
                    input=True,
                    frames_per_buffer=cfg.CHUNK)
vad = webrtcvad.Vad(settings["VAD"])  # Sensibilidad del micrófono

# Variables globales
audio_buffer = CircularBuffer(size=settings["BUFFER_SIZE"])
is_speaking = False
silence_counter = 0
lock = threading.Lock()

def save_temp_audio(frames, file_suffix=""):
    temp_dir = os.path.abspath('./temp')
    os.makedirs(temp_dir, exist_ok=True)
    timestamp = int(time.time())
    temp_file_path = os.path.join(temp_dir, f"temp_audio_{timestamp}{file_suffix}.wav")

    try:
        logger.debug(f"Abriendo archivo WAV para escritura: {temp_file_path}")
        with wave.open(temp_file_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(settings["RATE"])
            wf.writeframes(b''.join(frames))
            logger.debug(f"Archivo WAV guardado correctamente en: {temp_file_path}")
    except Exception as e:
        logger.debug(f"Error al guardar el archivo de audio: {e}")

    return temp_file_path

def is_loud_enough(frame, threshold=settings["THRESHOLD"]):
    audio_data = np.frombuffer(frame, dtype=np.int16)
    avg_volume = np.abs(audio_data).mean()
    return avg_volume > threshold

def record_audio(translator, app_instance, mic_index):
    global audio_buffer, is_speaking, silence_counter, stream

    # Reiniciar el flujo de audio
    stream.stop_stream()
    stream.close()

    # Obtener información del dispositivo
    p = pyaudio.PyAudio()
    device_info = p.get_device_info_by_index(mic_index)
    logger.debug(f"Dispositivo seleccionado: {device_info['name']}, Info completa: {device_info}")

    stream = audio.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=settings["RATE"],
                        input=True,
                        frames_per_buffer=cfg.CHUNK,
                        input_device_index=mic_index)

    logger.debug("Iniciando grabación...")
    start_time = time.time()
    
    # Configurar el QThreadPool global y establecer el máximo de hilos concurrentes en 3
    threadpool = QThreadPool.globalInstance()
    threadpool.setMaxThreadCount(3)
    
    while cfg.recording_active:
        frame = stream.read(cfg.CHUNK, exception_on_overflow=False)
        try:
            is_voice = vad.is_speech(frame, settings["RATE"]) or is_loud_enough(frame)
        except Exception as e:
            logger.debug(f"Error en VAD: {e}")
            continue

        if is_voice:
            silence_counter = 0
            audio_buffer.append(frame)
            is_speaking = True

            if time.time() - start_time > settings["MAX_CONTINUOUS_SPEECH_TIME"]:
                cut_index = int(settings["CUT_TIME"] * settings["RATE"] / cfg.CHUNK)
                temp_audio = audio_buffer.get_data()[-cut_index:]
                temp_file = save_temp_audio(temp_audio)
                
                if temp_file:
                    worker = AudioProcessingWorker(temp_file, translator)
                    worker.signals.finished.connect(app_instance.update_text_edit)
                    threadpool.start(worker)
                audio_buffer.clear()
                is_speaking = False
                start_time = time.time()

        elif is_speaking:
            silence_counter += 1
            if silence_counter > int(settings["RATE"] / cfg.CHUNK * settings["VOICE_WINDOW"]):
                if len(audio_buffer.get_data()) >= int(settings["MIN_VOICE_DURATION"] * settings["RATE"] / cfg.CHUNK):
                    cut_index = int(settings["CUT_TIME"] * settings["RATE"] / cfg.CHUNK)
                    temp_audio = audio_buffer.get_data()[-cut_index:]
                    temp_file = save_temp_audio(temp_audio)
                    
                    if temp_file:
                        worker = AudioProcessingWorker(temp_file, translator)
                        worker.signals.finished.connect(app_instance.update_text_edit)
                        threadpool.start(worker)
                audio_buffer.clear()
                is_speaking = False
                start_time = time.time()

        else:
            silence_counter += 1
            if silence_counter > int(settings["RATE"] / cfg.CHUNK * settings["MAX_CONTINUOUS_SPEECH_TIME"]):
                silence_counter = 0
                start_time = time.time()

def stop_recording():
    global audio_buffer, stream
    cfg.recording_active = False
    audio_buffer.clear()
    logger.debug("Deteniendo la grabación...")
    stream.stop_stream()  # Detener el flujo de audio
    stream.close()  # Cerrar el flujo de audio