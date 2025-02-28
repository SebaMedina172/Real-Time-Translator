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
import tempfile

# Importamos el worker desde el módulo creado (workers.py)
from modules.worker import AudioProcessingWorker

# Importamos el buffer circular
from modules.circular_buffer import CircularBuffer

# Configuración de PyQt para el ThreadPool
from PyQt5.QtCore import QThreadPool

import config.configuracion as cfg
from config.configuracion import settings, load_settings, calcular_valores_dinamicos

# Variable global adicional para almacenar el índice del último frame con voz
last_voice_index = 0

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
    try:
        with tempfile.NamedTemporaryFile(suffix=f"{file_suffix}.wav", delete=False) as temp_file:
            temp_file_path = temp_file.name

        logger.debug(f"Abriendo archivo WAV para escritura: {temp_file_path}")
        with wave.open(temp_file_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(settings["RATE"])
            wf.writeframes(b''.join(frames))
            logger.debug(f"Archivo WAV guardado correctamente en: {temp_file_path}")

    except Exception as e:
        logger.debug(f"Error al guardar el archivo de audio: {e}")
        return None

    return temp_file_path

def is_valid_audio(audio_data, min_size=256, min_energy=100):
    """
    Verifica que el segmento de audio tenga al menos `min_size` bytes y una energía promedio superior a `min_energy`.
    Se calculan sobre el total de bytes concatenados de todos los frames.
    """
    audio_bytes = b''.join(audio_data)
    if len(audio_bytes) < min_size:
        return False
    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
    if np.abs(audio_array).mean() < min_energy:
        return False
    return True

def is_loud_enough(frame, threshold=settings["THRESHOLD"]):
    audio_data = np.frombuffer(frame, dtype=np.int16)
    avg_volume = np.abs(audio_data).mean()
    return avg_volume > threshold

def process_audio_segment(translator, app_instance, threadpool, pre_roll_duration=0.0, data_to_process=None):
    """
    Procesa el segmento de audio actual y, opcionalmente, reinserta un pre-roll para mantener contexto.
    Ahora se puede pasar directamente el segmento a procesar (data_to_process) para que no incluya
    frames de silencio al final.
    """
    if data_to_process is None:
        data_to_process = audio_buffer.get_data()

    if not is_valid_audio(data_to_process):
        logger.debug("Segmento de audio inválido; se descarta y limpia el buffer.")
        audio_buffer.clear()
        return

    # En este caso usamos el segmento completo que se pasó (ya recortado hasta el último frame con voz)
    temp_audio = data_to_process

    temp_file = save_temp_audio(temp_audio)
    if temp_file:
        worker = AudioProcessingWorker(temp_file, translator)
        worker.signals.finished.connect(app_instance.update_text_edit)
        threadpool.start(worker)

    # Manejo del pre-roll (si corresponde)
    if pre_roll_duration > 0.0:
        overlap_frames = int(pre_roll_duration * settings["RATE"] / cfg.CHUNK)
        if len(data_to_process) > overlap_frames:
            pre_roll = data_to_process[-overlap_frames:]
        else:
            pre_roll = []
    else:
        pre_roll = []

    # Limpiar el buffer y reinsertar el pre-roll si aplica
    audio_buffer.clear()
    for frame in pre_roll:
        audio_buffer.append(frame)

def record_audio(translator, app_instance, mic_index):
    global audio_buffer, is_speaking, silence_counter, stream, last_voice_index

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
    last_logged_duration = 0  # Para controlar la frecuencia de logs
    last_voice_index = 0      # Inicializa el índice del último frame con voz

    # Configurar el QThreadPool global (máximo 3 hilos concurrentes)
    threadpool = QThreadPool.globalInstance()
    threadpool.setMaxThreadCount(3)
    
    while cfg.recording_active:
        frame = stream.read(cfg.CHUNK, exception_on_overflow=False)
        try:
            # Determina si el frame contiene voz (usando VAD o umbral de volumen)
            is_voice = vad.is_speech(frame, settings["RATE"]) or is_loud_enough(frame)
        except Exception as e:
            logger.debug(f"Error en VAD: {e}")
            continue

        if is_voice:
            silence_counter = 0
            audio_buffer.append(frame)
            is_speaking = True
            # Actualiza el índice del último frame que contiene voz
            last_voice_index = len(audio_buffer.get_data()) - 1

            if time.time() - start_time > settings["MAX_CONTINUOUS_SPEECH_TIME"]:
                duration_sec = (len(audio_buffer.get_data()) * cfg.CHUNK) / settings["RATE"]
                if duration_sec < 1.0:
                    if duration_sec - last_logged_duration >= 0.5:
                        logger.debug(f"Duración acumulada muy corta ({duration_sec:.2f}s), se espera a acumular más audio.")
                        last_logged_duration = duration_sec
                else:
                    process_audio_segment(translator, app_instance, threadpool, pre_roll_duration=0.5)
                    is_speaking = False
                    start_time = time.time()
                    last_logged_duration = 0
                    last_voice_index = 0  # Reinicia el índice
        elif is_speaking:
            silence_counter += 1
            # Si se supera el umbral de silencio definido por VOICE_WINDOW:
            if silence_counter > int(settings["RATE"] / cfg.CHUNK * settings["VOICE_WINDOW"]):
                # Solo procesar si se tiene la duración mínima de voz
                if len(audio_buffer.get_data()) >= int(settings["MIN_VOICE_DURATION"] * settings["RATE"] / cfg.CHUNK):
                    # Extrae el segmento hasta el último frame con voz detectado
                    segment = audio_buffer.get_data()[:last_voice_index+1]
                    process_audio_segment(translator, app_instance, threadpool, pre_roll_duration=0.0, data_to_process=segment)
                else:
                    audio_buffer.clear()
                is_speaking = False
                start_time = time.time()
                last_logged_duration = 0
                last_voice_index = 0  # Reinicia el índice al cortar
        else:
            silence_counter += 1
            if silence_counter > int(settings["RATE"] / cfg.CHUNK * settings["MAX_CONTINUOUS_SPEECH_TIME"]):
                silence_counter = 0
                start_time = time.time()
                last_logged_duration = 0


def stop_recording():
    global audio_buffer, stream
    cfg.recording_active = False
    audio_buffer.clear()
    logger.debug("Deteniendo la grabación...")
    stream.stop_stream()  # Detener el flujo de audio
    stream.close()  # Cerrar el flujo de audio