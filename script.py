import wave
import pyaudio
import webrtcvad
import os
import numpy as np
import whisper
import time
import threading
from googletrans import Translator

# Configuración básica
RATE = 16000
CHUNK_DURATION_MS = 30
CHUNK = int(RATE * CHUNK_DURATION_MS / 1000)
VOICE_WINDOW = 0.4
MIN_VOICE_DURATION = 0.3
MAX_CONTINUOUS_SPEECH_TIME = 5  # Máximo tiempo de grabación continua en segundos

# Cargar el modelo de Whisper
model = whisper.load_model("base")  # Puedes cambiar "base" por otro modelo si prefieres mayor precisión

# Inicializar el traductor de Google
translator = Translator()

audio = pyaudio.PyAudio()
stream = audio.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
vad = webrtcvad.Vad(2)

audio_buffer = []
is_speaking = False
silence_counter = 0
start_time = time.time()

# Variables de sincronización
lock = threading.Lock()

def save_temp_audio(frames):
    temp_dir = "./temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, "temp_audio.wav")
    
    with wave.open(temp_file_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    
    return temp_file_path

def is_loud_enough(frame, threshold=500):
    audio_data = np.frombuffer(frame, dtype=np.int16)
    return np.abs(audio_data).mean() > threshold

def transcribe_and_translate(audio_file):
    try:
        # Realiza la transcripción con Whisper
        result = model.transcribe(audio_file)
        text = result['text']
        
        # Detecta el idioma
        detected_language = result['language']
        #print(f"Idioma detectado: {detected_language}")
        
        # Traducción bidireccional
        if detected_language == "es":
            #print(f"Texto en español: {text}")
            translated_text = translator.translate(text, src='es', dest='en').text
            #print(f"Texto traducido al inglés: {translated_text}")
        elif detected_language == "en":
            #print(f"Texto en inglés: {text}")
            translated_text = translator.translate(text, src='en', dest='es').text
            #print(f"Texto traducido al español: {translated_text}")
        else:
            translated_text = text
        
        return translated_text
    except Exception as e:
        print(f"Error al transcribir o traducir: {e}")
        return None

def record_audio():
    global audio_buffer, is_speaking, silence_counter, start_time

    while True:
        frame = stream.read(CHUNK, exception_on_overflow=False)
        try:
            is_voice = vad.is_speech(frame, RATE) or is_loud_enough(frame)
        except webrtcvad.Error as e:
            print(f"Error en VAD: {e}")
            continue

        if is_voice:
            silence_counter = 0  # Reinicia el contador de silencio cuando se detecta voz
            with lock:
                audio_buffer.append(frame)
            is_speaking = True
            # Si lleva más de X segundos hablando, corta la grabación
            if time.time() - start_time > MAX_CONTINUOUS_SPEECH_TIME:
                print("Tiempo de habla continua excedido, procesando...")
                with lock:
                    temp_file = save_temp_audio(audio_buffer)
                threading.Thread(target=process_audio, args=(temp_file,)).start()
                with lock:
                    audio_buffer = []  # Resetea el buffer
                is_speaking = False
                start_time = time.time()  # Reinicia el temporizador
        elif is_speaking:
            silence_counter += 1
            if silence_counter > int(RATE / CHUNK * VOICE_WINDOW):
                if len(audio_buffer) >= int(MIN_VOICE_DURATION * RATE / CHUNK):
                    with lock:
                        temp_file = save_temp_audio(audio_buffer)
                    threading.Thread(target=process_audio, args=(temp_file,)).start()
                with lock:
                    audio_buffer = []  # Resetea el buffer
                is_speaking = False
                start_time = time.time()  # Reinicia el temporizador después del silencio
        else:
            silence_counter += 1  # Incrementa el contador de silencio cuando no se detecta voz
            if silence_counter > int(RATE / CHUNK * MAX_CONTINUOUS_SPEECH_TIME):  # Si supera el límite de silencio
                # Si hay un largo periodo de silencio, reinicia el temporizador
                silence_counter = 0
                start_time = time.time()  # Reinicia el tiempo para una nueva grabación

def process_audio(audio_file):
    translated_text = transcribe_and_translate(audio_file)
    if translated_text:
        print(f"Traducción: {translated_text}")
    else:
        print("No se pudo procesar el audio correctamente.")
    
    try:
        os.remove(audio_file)
        print(f"Archivo {audio_file} eliminado exitosamente.")
    except PermissionError:
        print(f"Error al intentar eliminar el archivo {audio_file}: Permiso denegado.")
    except Exception as e:
        print(f"Error inesperado al eliminar el archivo {audio_file}: {e}")

print("Escuchando... Presiona Ctrl+C para detener.")
try:
    # Iniciar hilo de grabación
    recording_thread = threading.Thread(target=record_audio)
    recording_thread.daemon = True
    recording_thread.start()

    # Mantener el programa en ejecución
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nDetenido por el usuario.")
finally:
    stream.stop_stream()
    stream.close()
    audio.terminate()
