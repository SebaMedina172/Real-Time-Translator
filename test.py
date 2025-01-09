import pyaudio
import wave
import threading
import queue
import time
import io
import whisper
import requests
import os
import signal
import sys

# Configuración de audio
CHUNK = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
SILENCE_THRESHOLD = 1000
SILENCE_DURATION = 0.3

# Inicializar Whisper
model = whisper.load_model("small")

# Cola para grabaciones y transcripciones
audio_queue = queue.Queue()
transcription_queue = queue.Queue()

# Bandera para detener los hilos
stop_flag = False

# Configuración de Azure Translation API
AZURE_API_KEY = "1rbGKESKAuLgW5d6JQ7JZYPbvsuqBp5hjxcDtEqTEgChufyrTvD6JQQJ99AKACZoyfiXJ3w3AAAbACOGc0YD"
AZURE_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
AZURE_REGION = "brazilsouth"  # Cambia esto a la región de tu recurso

def translate_text(text, from_lang="es", to_lang="en"):
    """Función para traducir texto usando la API de Microsoft Azure."""
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_API_KEY,
        "Ocp-Apim-Subscription-Region": AZURE_REGION,
        "Content-Type": "application/json"
    }
    params = {
        "api-version": "3.0",
        "from": from_lang,
        "to": [to_lang]
    }
    body = [{"text": text}]
    response = requests.post(f"{AZURE_ENDPOINT}/translate", headers=headers, params=params, json=body)
    
    if response.status_code == 200:
        translations = response.json()
        return translations[0]["translations"][0]["text"]
    else:
        print(f"Error en la traducción: {response.status_code} - {response.text}")
        return None

def record_audio():
    """Graba el audio y detecta el silencio para dividir en frases."""
    global stop_flag
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []
    silence_start = None

    print("Grabando...")

    try:
        while not stop_flag:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            # Detección de silencio
            volume = max(int.from_bytes(data, "little") for data in frames[-1:])
            if volume < SILENCE_THRESHOLD:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > SILENCE_DURATION:
                    audio_queue.put(b''.join(frames))
                    frames = []
                    silence_start = None
            else:
                silence_start = None
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()
        print("Grabación detenida.")

def transcribe_audio():
    """Transcribe el audio en tiempo real."""
    global stop_flag
    while not stop_flag:
        if not audio_queue.empty():
            audio_data = audio_queue.get()
            
            # Convertir audio a formato compatible con Whisper
            audio_buffer = io.BytesIO(audio_data)
            with wave.open(audio_buffer, 'rb') as wf:
                audio_bytes = wf.readframes(wf.getnframes())
            
            result = model.transcribe(audio_bytes)
            transcription_queue.put(result['text'])
            print(f"Transcripción: {result['text']}")

def translate_and_print():
    """Traduce las transcripciones y las imprime en tiempo real."""
    global stop_flag
    while not stop_flag:
        if not transcription_queue.empty():
            text = transcription_queue.get()
            translation = translate_text(text, from_lang="es", to_lang="en")
            if translation:
                print(f"Traducción: {translation}")

def stop_all_threads(signal, frame):
    """Manejador para detener los hilos con Ctrl+C."""
    global stop_flag
    stop_flag = True
    print("\nDeteniendo todos los hilos...")

# Configurar señal para Ctrl+C
signal.signal(signal.SIGINT, stop_all_threads)

# Crear y ejecutar hilos
record_thread = threading.Thread(target=record_audio)
transcribe_thread = threading.Thread(target=transcribe_audio)
translate_thread = threading.Thread(target=translate_and_print)

record_thread.start()
transcribe_thread.start()
translate_thread.start()

record_thread.join()
transcribe_thread.join()
translate_thread.join()

print("Programa terminado.")
