import sys
import os
# Agregar la carpeta raíz del proyecto al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging

# Configurar el logger
logging.basicConfig(filename='app.log', level=logging.DEBUG)

import wave
import pyaudio
import webrtcvad
import numpy as np
import threading
import time
from modules.speech_processing import process_audio
from PyQt5.QtCore import QThread, pyqtSignal
from modules.circular_buffer import CircularBuffer
import asyncio

import config.configuracion as cfg
from config.configuracion import settings, load_settings, calcular_valores_dinamicos

load_settings()
calcular_valores_dinamicos()

# Configuración de audio
audio = pyaudio.PyAudio()
stream = audio.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=settings["RATE"],
                    input=True,
                    frames_per_buffer=cfg.CHUNK)
vad = webrtcvad.Vad(settings["VAD"])  # Sensibilidad del mic

# Variables globales
audio_buffer = CircularBuffer(size=settings["BUFFER_SIZE"])
is_speaking = False
silence_counter = 0
lock = threading.Lock()

class AudioProcessingThread(QThread):
    finished_processing = pyqtSignal(str)  # Señal para indicar que el procesamiento ha terminado

    def __init__(self, audio_file, translator):
        super().__init__()
        self.audio_file = audio_file
        self.translator = translator

    def run(self):
        # Llama a la función de procesamiento de audio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        translated_text = loop.run_until_complete(process_audio(self.audio_file, self.translator))
        self.finished_processing.emit(translated_text)  # Emitir la señal con el texto traducido

def save_temp_audio(frames, file_suffix=""):
    temp_dir = os.path.abspath('./temp')
    os.makedirs(temp_dir, exist_ok=True)
    timestamp = int(time.time())
    temp_file_path = os.path.join(temp_dir, f"temp_audio_{timestamp}{file_suffix}.wav")

    try:
        logging.debug(f"Abriendo archivo WAV para escritura: {temp_file_path}")
        with wave.open(temp_file_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(settings["RATE"])
            wf.writeframes(b''.join(frames))
            logging.debug(f"Archivo WAV guardado correctamente en: {temp_file_path}")
    except Exception as e:
        logging.debug(f"Error al guardar el archivo de audio: {e}")

    return temp_file_path

def is_loud_enough(frame, threshold=settings["THRESHOLD"]):
    audio_data = np.frombuffer(frame, dtype=np.int16)
    avg_volume = np.abs(audio_data).mean()
    return avg_volume > threshold

def record_audio(translator, app_instance, mic_index):
    global audio_buffer, is_speaking, silence_counter

    # Reiniciar el flujo de audio
    global stream
    stream.stop_stream()
    stream.close()

    # Obtener información del dispositivo
    p = pyaudio.PyAudio()
    device_info = p.get_device_info_by_index(mic_index)
    logging.debug(f"Dispositivo seleccionado: {device_info['name']}, Info completa: {device_info}")

    stream = audio.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=settings["RATE"],
                        input=True,
                        frames_per_buffer=cfg.CHUNK,
                        input_device_index=mic_index)

    logging.debug("Iniciando grabación...")  # Mensaje de depuración
    start_time = time.time()  # Inicializa start_time al principio de la función

    while cfg.recording_active:
        #logging.debug("Grabando...")  # Mensaje de depuración
        frame = stream.read(cfg.CHUNK, exception_on_overflow=False)
        try:
            # Detecta si es voz o si el volumen es lo suficientemente alto
            is_voice = vad.is_speech(frame, settings["RATE"]) or is_loud_enough(frame)
            #\logging.debug(f"¿Es voz? {is_voice}")  # Mensaje de depuración
        except Exception as e:
            logging.debug(f"Error en VAD: {e}")
            continue

        if is_voice:
            silence_counter = 0
            audio_buffer.append(frame)
            is_speaking = True

            if time.time() - start_time > settings["MAX_CONTINUOUS_SPEECH_TIME"]:
                # Cortes inteligentes
                cut_index = int(settings["CUT_TIME"] * settings["RATE"] / cfg.CHUNK)
                temp_audio = audio_buffer.get_data()[-cut_index:]
                temp_file = save_temp_audio(temp_audio)
                #logging.debug(f'Valor actualizado del save_temp_audio: {temp_file}')
                audio_thread = AudioProcessingThread(temp_file, translator)
                audio_thread.finished_processing.connect(app_instance.update_text_edit)
                audio_thread.start()
                audio_buffer.clear()
                is_speaking = False
                start_time = time.time()

        elif is_speaking:
            # Si hay silencio después de haber hablado, aumenta el contador
            silence_counter += 1
            if silence_counter > int(settings["RATE"] / cfg.CHUNK * settings["VOICE_WINDOW"]):
                # Si el buffer tiene suficiente duración, lo guarda
                if len(audio_buffer.get_data()) >= int(settings["MIN_VOICE_DURATION"] * settings["RATE"] / cfg.CHUNK):
                    cut_index = int(settings["CUT_TIME"] * settings["RATE"] / cfg.CHUNK)
                    temp_audio = audio_buffer.get_data()[-cut_index:]  # Toma solo los últimos 2 segundos
                    temp_file = save_temp_audio(temp_audio)
                    #logging.debug(f'Valor actualizado del save_temp_audio: {temp_file}')
                    # Usar QThread para el procesamiento de audio
                    audio_thread = AudioProcessingThread(temp_file, translator)
                    audio_thread.finished_processing.connect(app_instance.update_text_edit)  # Conectar a la función de actualización
                    audio_thread.start()

                # Resetea el buffer y el estado de grabación
                audio_buffer.clear()  # Resetea el buffer
                is_speaking = False
                start_time = time.time()  # Reinicia el temporizador

        else:
            # Si no hay voz detectada, incrementa el contador de silencio
            silence_counter += 1
            if silence_counter > int(settings["RATE"] / cfg.CHUNK * settings["MAX_CONTINUOUS_SPEECH_TIME"]):
                # Si ha pasado el tiempo máximo sin voz, resetea el contador
                silence_counter = 0
                start_time = time.time()  # Reinicia el tiempo para una nueva grabación
        #logging.debug("Grabación detenida.")  # Mensaje de depuración al finalizar

def stop_recording():
    global audio_buffer
    cfg.recording_active = False
    audio_buffer.clear()
    logging.debug("Deteniendo la grabación...")
    stream.stop_stream()  # Detener el flujo de audio
    stream.close()  # Cerrar el flujo de audio
