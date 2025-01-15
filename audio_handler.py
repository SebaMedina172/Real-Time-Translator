import wave
import pyaudio
import webrtcvad
import os
import numpy as np
import threading
import config
import time
from speech_processing import process_audio  # Asegúrate de importar process_audio

audio = pyaudio.PyAudio()
stream = audio.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=config.RATE,
                    input=True,
                    frames_per_buffer=config.CHUNK)
vad = webrtcvad.Vad(config.VAD)  # Sensibilidad del mic

# Variables globales para grabación
audio_buffer = []
is_speaking = False
silence_counter = 0
lock = threading.Lock()
recording_active = True

def save_temp_audio(frames):
    temp_dir = config.TEMP_DIR
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, "temp_audio.wav")

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

def record_audio():
    global audio_buffer, is_speaking, silence_counter
    global start_time, recording_active

    start_time = time.time()  # Inicializa start_time al principio de la función

    while recording_active:
        frame = stream.read(config.CHUNK, exception_on_overflow=False)
        try:
            # Detecta si es voz o si el volumen es lo suficientemente alto
            is_voice = vad.is_speech(frame, config.RATE) or is_loud_enough(frame)
        except webrtcvad.Error as e:
            print(f"Error en VAD: {e}")
            continue

        if is_voice:
            # Si detecta voz, reinicia el contador de silencio
            silence_counter = 0
            with lock:
                audio_buffer.append(frame)  # Agrega el frame al buffer
            is_speaking = True

            # Si lleva más de X segundos hablando, realiza un corte inteligente
            if time.time() - start_time > config.MAX_CONTINUOUS_SPEECH_TIME:
                with lock:
                    cut_index = int(config.CUT_TIME * config.RATE / config.CHUNK)
                    temp_audio = audio_buffer[-cut_index:]  # Toma solo los últimos 2 segundos
                    temp_file = save_temp_audio(temp_audio)
                    threading.Thread(target=process_audio, args=(temp_file,)).start()
                    audio_buffer = []  # Resetea el buffer
                is_speaking = False
                start_time = time.time()  # Reinicia el temporizador

        elif is_speaking:
            # Si hay silencio después de haber hablado, aumenta el contador
            silence_counter += 1
            if silence_counter > int(config.RATE / config.CHUNK * config.VOICE_WINDOW):
                # Si el buffer tiene suficiente duración, lo guarda
                if len(audio_buffer) >= int(config.MIN_VOICE_DURATION * config.RATE / config.CHUNK):
                    with lock:
                        cut_index = int(config.CUT_TIME * config.RATE / config.CHUNK)
                        temp_audio = audio_buffer[-cut_index:]  # Toma solo los últimos 2 segundos
                        temp_file = save_temp_audio(temp_audio)
                    threading.Thread(target=process_audio, args=(temp_file,)).start()

                # Resetea el buffer y el estado de grabación
                with lock:
                    audio_buffer = []  # Resetea el buffer
                is_speaking = False
                start_time = time.time()  # Reinicia el temporizador

        else:
            # Si no hay voz detectada, incrementa el contador de silencio
            silence_counter += 1
            if silence_counter > int(config.RATE / config.CHUNK * config.MAX_CONTINUOUS_SPEECH_TIME):
                # Si ha pasado el tiempo máximo sin voz, resetea el contador
                silence_counter = 0
                start_time = time.time()  # Reinicia el tiempo para una nueva grabación

def stop_recording():
    global recording_active
    recording_active = False
    print("Deteniendo la grabación...")
