import wave
import pyaudio
import webrtcvad
import os
import numpy as np
import whisper
import time
import threading
from googletrans import Translator
import spacy
from obs_helper import OBSManager  # Asegúrate de tener esta importación

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

# Cargar el modelo de spaCy para segmentación de oraciones
nlp = spacy.load("es_core_news_sm")  # Puedes cambiar esto por el modelo adecuado (español o inglés)

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

# Configurar OBS
obs_manager = OBSManager(host="localhost", port=4455, password="your_password_here")
obs_manager.connect()  # Conectar con OBS

# Flag para manejar la detención del hilo de grabación
recording_active = True

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
        # Verifica si el archivo es válido
        if audio_file is None:
            print("Archivo de audio no válido.")
            return None
        
        # Realiza la transcripción con Whisper
        result = model.transcribe(audio_file)
        
        # Extrae el texto de la transcripción
        text = result.get('text', None)
        
        # Verifica si la transcripción está vacía
        if not text:
            print("La transcripción está vacía.")
            return None
        
        # Detecta el idioma
        detected_language = result['language']
        
        # Segmentación del texto usando spaCy para identificar oraciones
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        # Traducción bidireccional
        translated_sentences = []
        if detected_language == "es":
            for sentence in sentences:
                translated_text = translator.translate(sentence, src='es', dest='en').text
                translated_sentences.append(translated_text)
        elif detected_language == "en":
            for sentence in sentences:
                translated_text = translator.translate(sentence, src='en', dest='es').text
                translated_sentences.append(translated_text)
        else:
            translated_sentences = sentences
        
        return " ".join(translated_sentences)
    
    except Exception as e:
        print(f"Error al transcribir o traducir: {e}")
        return None

def process_audio(audio_file):
    translated_text = transcribe_and_translate(audio_file)
    if translated_text:
        print(f"Texto transcrito y traducido: {translated_text}")
        
        # Actualizamos el texto en OBS
        obs_manager.update_text(translated_text)
    else:
        print("No se pudo procesar el audio correctamente.")
    
    try:
        os.remove(audio_file)
    except Exception as e:
        print(f"Error al eliminar el archivo {audio_file}: {e}")

def record_audio():
    global audio_buffer, is_speaking, silence_counter, start_time, recording_active

    while recording_active:
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
                silence_counter = 0
                start_time = time.time()  # Reinicia el tiempo para una nueva grabación

def stop_recording():
    global recording_active
    recording_active = False
    print("Deteniendo la grabación...")

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
    stop_recording()
    print("\nDetenido por el usuario.")
finally:
    stream.stop_stream()
    stream.close()
    audio.terminate()
