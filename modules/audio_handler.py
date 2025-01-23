import sys
import os
# Agregar la carpeta raíz del proyecto al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import wave
import pyaudio
import webrtcvad
import numpy as np
import threading
from config import config
import time
from modules.speech_processing import process_audio  # Asegúrate de importar process_audio
from PyQt5.QtCore import QThread, pyqtSignal
from modules.circular_buffer import CircularBuffer


audio = pyaudio.PyAudio()
stream = audio.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=config.RATE,
                    input=True,
                    frames_per_buffer=config.CHUNK)
vad = webrtcvad.Vad(config.VAD)  # Sensibilidad del mic

# Variables globales para grabación
audio_buffer = CircularBuffer(size=config.BUFFER_SIZE) 
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
        translated_text = process_audio(self.audio_file, self.translator)
        self.finished_processing.emit(translated_text)  # Emitir la señal con el texto traducido

def save_temp_audio(frames, file_suffix=""):
    temp_dir = config.TEMP_DIR
    os.makedirs(temp_dir, exist_ok=True)
    timestamp = int(time.time())
    temp_file_path = os.path.join(temp_dir, f"temp_audio_{timestamp}{file_suffix}.wav")

    with wave.open(temp_file_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(config.RATE)
        wf.writeframes(b''.join(frames))

    return temp_file_path

def is_loud_enough(frame, threshold=config.THRESHOLD):
    audio_data = np.frombuffer(frame, dtype=np.int16)
    avg_volume = np.abs(audio_data).mean()
    return avg_volume > threshold

def record_audio(translator,app_instance,mic_index):
    global audio_buffer, is_speaking, silence_counter
    global start_time

    # Reiniciar el flujo de audio
    global stream
    stream.stop_stream()  # Detener el flujo de audio si está activo
    stream.close()  # Cerrar el flujo de audio

    # Obtener información del dispositivo
    p = pyaudio.PyAudio()
    device_info = p.get_device_info_by_index(mic_index)
    print(f"Dispositivo seleccionado: {device_info['name']}, Canales: {device_info['maxInputChannels']}")

    stream = audio.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=config.RATE,
                        input=True,
                        frames_per_buffer=config.CHUNK,
                        input_device_index=mic_index)

    print("Iniciando grabación...")  # Mensaje de depuración
    start_time = time.time()  # Inicializa start_time al principio de la función

    while config.recording_active:
        #print("Grabando...")  # Mensaje de depuración
        frame = stream.read(config.CHUNK, exception_on_overflow=False)
        try:
            # Detecta si es voz o si el volumen es lo suficientemente alto
            is_voice = vad.is_speech(frame, config.RATE) or is_loud_enough(frame)
            #\print(f"¿Es voz? {is_voice}")  # Mensaje de depuración
        except webrtcvad.Error as e:
            print(f"Error en VAD: {e}")
            continue

        if is_voice:
            silence_counter = 0
            audio_buffer.append(frame)  # Agrega el frame al buffer circular
            is_speaking = True

            if time.time() - start_time > config.MAX_CONTINUOUS_SPEECH_TIME:
                cut_index = int(config.CUT_TIME * config.RATE / config.CHUNK)
                temp_audio = audio_buffer.get_data()[-cut_index:]  # Obtiene los últimos X frames
                temp_file = save_temp_audio(temp_audio)
                audio_thread = AudioProcessingThread(temp_file, translator)
                audio_thread.finished_processing.connect(app_instance.update_text_edit)
                audio_thread.start()
                audio_buffer.clear()  # Limpia el buffer circular
                is_speaking = False
                start_time = time.time()

        elif is_speaking:
            # Si hay silencio después de haber hablado, aumenta el contador
            silence_counter += 1
            if silence_counter > int(config.RATE / config.CHUNK * config.VOICE_WINDOW):
                # Si el buffer tiene suficiente duración, lo guarda
                if len(audio_buffer.get_data()) >= int(config.MIN_VOICE_DURATION * config.RATE / config.CHUNK):
                    
                    cut_index = int(config.CUT_TIME * config.RATE / config.CHUNK)
                    temp_audio = audio_buffer.get_data()[-cut_index:]  # Toma solo los últimos 2 segundos
                    temp_file = save_temp_audio(temp_audio)
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
            if silence_counter > int(config.RATE / config.CHUNK * config.MAX_CONTINUOUS_SPEECH_TIME):
                # Si ha pasado el tiempo máximo sin voz, resetea el contador
                silence_counter = 0
                start_time = time.time()  # Reinicia el tiempo para una nueva grabación
        #print("Grabación detenida.")  # Mensaje de depuración al finalizar

def stop_recording():
    global audio_buffer
    config.recording_active = False
    audio_buffer.clear()
    print("Deteniendo la grabación...")
    stream.stop_stream()  # Detener el flujo de audio
    stream.close()  # Cerrar el flujo de audio
