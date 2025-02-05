# # # test_imports.py
# # import sys
# # import os

# # # Agregar la carpeta raíz del proyecto al PYTHONPATH
# # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# # try:
# #     from modules.audio_handler import record_audio, stop_recording
# #     from modules.speech_processing import process_audio
# #     print("Importaciones exitosas.")
# # except ImportError as e:
# #     print(f"Error al importar: {e}")

# # import os
# # print("Directorio de trabajo actual:", os.getcwd())

# # import ffmpeg

# # input_file = "./audio_test/pilin_test_audio.wav"  # Archivo grabado desde tu micrófono
# # output_file = "./audio_test/pilin_16k.wav"

# # ffmpeg.input(input_file).output(output_file, ar=16000).run()


# import pyaudio
# import wave

# def list_valid_microphones(latency_threshold=0.10, sample_rates=(44100, 16000)):
#     """Lista los micrófonos válidos según los criterios especificados."""
#     audio = pyaudio.PyAudio()
#     valid_microphones = []  # Lista para almacenar micrófonos válidos

#     for i in range(audio.get_device_count()):
#         device_info = audio.get_device_info_by_index(i)
#         name = device_info['name']
#         max_input_channels = device_info['maxInputChannels']
#         default_sample_rate = device_info['defaultSampleRate']
#         default_low_input_latency = device_info['defaultLowInputLatency']
#         default_high_input_latency = device_info['defaultHighInputLatency']

#         # Solo considerar dispositivos de entrada con al menos 1 canal
#         if max_input_channels > 0:
#             try:
#                 # Intentar abrir un flujo de prueba
#                 stream = audio.open(format=pyaudio.paInt16,
#                                     channels=1,
#                                     rate=int(default_sample_rate),
#                                     input=True,
#                                     input_device_index=i)
#                 stream.close()  # Si funciona, lo cerramos inmediatamente
#                 print(f"Dispositivo válido: {name}, Canales: {max_input_channels}, "
#                       f"Tasa de muestreo: {default_sample_rate}, "
#                       f"Latencia baja: {default_low_input_latency}, "
#                       f"Latencia alta: {default_high_input_latency}")
                
#                 valid_microphones.append((i, name))  # Agregar a la lista de micrófonos válidos
#             except Exception as e:
#                 print(f"Error al abrir el dispositivo ({name}): {e}")

#     audio.terminate()  # Terminar PyAudio
#     return valid_microphones

# def record_audio(filename, duration=5, mic_index=0):
#     """Graba audio desde el micrófono especificado."""
#     # Configuración de audio
#     FORMAT = pyaudio.paInt16  # Formato de audio
#     CHANNELS = 1  # Número de canales
#     RATE = 44100  # Frecuencia de muestreo
#     CHUNK = 1024  # Tamaño del buffer

#     # Inicializar PyAudio
#     audio = pyaudio.PyAudio()

#     # Abrir el flujo de audio usando el micrófono especificado
#     stream = audio.open(format=FORMAT,
#                         channels=CHANNELS,
#                         rate=RATE,
#                         input=True,
#                         frames_per_buffer=CHUNK,
#                         input_device_index=mic_index)

#     print("Grabando...")

#     frames = []  # Lista para almacenar los frames de audio

#     # Grabar durante el tiempo especificado
#     for _ in range(0, int(RATE / CHUNK * duration)):
#         data = stream.read(CHUNK)
#         frames.append(data)

#     print("Grabación finalizada.")

#     # Detener y cerrar el flujo de audio
#     stream.stop_stream()
#     stream.close()
#     audio.terminate()

#     # Guardar el audio grabado en un archivo WAV
#     with wave.open(filename, 'wb') as wf:
#         wf.setnchannels(CHANNELS)
#         wf.setsampwidth(audio.get_sample_size(FORMAT))
#         wf.setframerate(RATE)
#         wf.writeframes(b''.join(frames))

# if __name__ == "__main__":
#     # Listar micrófonos válidos
#     valid_microphones = list_valid_microphones()
    
#     if valid_microphones:
#         print("Micrófonos válidos encontrados:")
#         for index, name in valid_microphones:
#             print(f"ID: {index}, Nombre: {name}")

#         # Solicitar al usuario que ingrese el índice del micrófono
#         mic_index = int(input("Ingrese el ID del micrófono que desea usar: "))
        
#         # Grabar audio desde el micrófono seleccionado
#         record_audio("grabacion.wav", duration=5, mic_index=mic_index)
#     else:
#         print("No se encontraron micrófonos válidos.")









#Filtro Perfecto
# def populate_microphone_list(self):
#         """Llena el QComboBox con los micrófonos disponibles y funcionales."""
#         p = pyaudio.PyAudio()
#         microphone_combo_box = self.findChild(QtWidgets.QComboBox, "microphoneComboBox")
#         microphone_combo_box.clear()
#         self.microphone_mapping = {}

#         latency_threshold = 0.2  # Relajar umbral de latencia

#         for i in range(p.get_device_count()):
#             device_info = p.get_device_info_by_index(i)
#             name = device_info['name']
#             max_input_channels = device_info['maxInputChannels']
#             default_sample_rate = device_info['defaultSampleRate']
#             default_low_input_latency = device_info['defaultLowInputLatency']
#             default_high_input_latency = device_info['defaultHighInputLatency']

#             if max_input_channels > 0:  # Solo dispositivos de entrada
#                 try:
#                     # Intentar abrir un flujo y grabar datos para validar el micrófono
#                     stream = p.open(format=pyaudio.paInt16,
#                                     channels=1,
#                                     rate=int(default_sample_rate),
#                                     input=True,
#                                     input_device_index=i)
#                     frames = stream.read(1024, exception_on_overflow=False)
#                     stream.close()
                    
#                     # Verificar criterios adicionales
#                     if 0.005 <= default_low_input_latency <= latency_threshold and \
#                         0.005 <= default_high_input_latency <= latency_threshold:
#                         microphone_combo_box.addItem(name)
#                         microphone_combo_box.setItemData(microphone_combo_box.count() - 1,name, Qt.ToolTipRole)
#                         self.microphone_mapping[name] = i
#                         print(f"Micrófono válido añadido: {name}")
#                     else:
#                         print(f"Micrófono omitido por alta latencia: {name}")
#                 except Exception as e:
#                     print(f"Error al probar el micrófono ({name}): {e}")

#         # Si no hay micrófonos válidos, añadir un mensaje al QComboBox
#         if microphone_combo_box.count() == 0:
#             microphone_combo_box.addItem("No se encontraron micrófonos válidos")

#         p.terminate()


        # def start_translation(self):
        # if not config.recording_active:
        #     print("Iniciando traducción...")
        #     config.recording_active = True 
        #     print(config.recording_active) 

        #     # Obtener el índice del micrófono seleccionado
        #     microphone_combo_box = self.findChild(QtWidgets.QComboBox, "microphoneComboBox")
        #     selected_microphone_name = microphone_combo_box.currentText()  # Obtener el nombre seleccionado
        #     mic_index = self.microphone_mapping.get(selected_microphone_name)  # Obtener el índice real del dispositivo

        #     try:
        #         # Intentar iniciar la grabación con el micrófono seleccionado
        #         self.recording_thread = AudioRecordingThread(self.translator, self, mic_index)
        #         self.recording_thread.start()

        #         # Actualizar la interfaz
        #         self.success_msg("Traduccion iniciada, prueba hablar")
        #     except Exception as e:
        #         print(f"Error al intentar grabar con el micrófono: {e}")

        #         # Si ocurre un error, eliminar el dispositivo del QComboBox
        #         microphone_combo_box = self.findChild(QtWidgets.QComboBox, "microphoneComboBox")
        #         current_item = microphone_combo_box.currentText()
        #         print(f"Error con el micrófono: {current_item}")

        #         # Eliminar el micrófono problemático de la lista
        #         microphone_combo_box.removeItem(microphone_combo_box.currentIndex())

        #         # Mostrar un mensaje al usuario para que seleccione otro dispositivo
        #         self.error_msg(f"El micrófono '{current_item}' causó un error. Por favor, elige otro.")

        #         # Establecer recording_active como False para evitar bloqueos
        #         config.recording_active = False
        # else:
        #     print("La grabación ya está activa.")

# import os
# ruta = "../ui/imgs/play_white.svg"

# if os.path.exists(ruta):
#     print("El archivo existe.")
# else:
#     print("El archivo no existe.")

# from PIL import Image

# # Ruta de tu archivo PNG (debe estar en el mismo directorio o indicar su ruta completa)
# png_file = "tu_icono.png"  # Cambia esto por el nombre de tu archivo PNG
# ico_file = "output_icon.ico"  # Nombre del archivo final .ico

# # Lista de resoluciones que queremos incluir en el .ico
# sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

# # Abrir el archivo PNG
# img = Image.open(png_file)

# # Asegurarse de que la imagen sea cuadrada (si no lo es, se ajusta)
# if img.width != img.height:
#     # Crear un fondo cuadrado transparente
#     size = max(img.width, img.height)
#     square_img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
#     square_img.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
#     img = square_img

# # Crear el archivo .ico con las diferentes resoluciones
# img.save(ico_file, format="ICO", sizes=sizes)

# print(f"Archivo .ico creado con éxito: {ico_file}")



# import spacy

# # Cargar el modelo
# nlp_es = spacy.load('es_core_news_md')
# nlp_en = spacy.load('en_core_web_md')


# # Obtener la ruta del modelo cargado
# print(nlp_es.meta['name'], "model path:", nlp_es.path)
# print(nlp_en.meta['name'], "model path:", nlp_en.path)

# import spacy
# import os

# model_es = ".//venv/lib/site-packages/es_core_news_md/es_core_news_md-3.8.0"
# model_en = ".//venv/Lib/site-packages/en_core_web_md/en_core_web_md-3.8.0"

# # Verificar si las rutas existen antes de cargar los modelos
# print("Rutas de modelos:")
# print(os.path.exists(model_es))
# print(os.path.exists(model_en))

# nlp_es = spacy.load(model_es)
# nlp_en = spacy.load(model_en)

# import shutil

# ffmpeg_path = shutil.which("ffmpeg")
# print(f"FFMPEG encontrado en: {ffmpeg_path}")


# import whisper

# # Ruta del archivo original y archivo convertido
# audio_path = "C:\\Users\\usuario\\OneDrive\\Escritorio\\Mis_Proyectos\\Translator\\audio_test\\pilin_test_audio.wav"

# # Cargar modelo y transcribir el archivo convertido
# model = whisper.load_model("base")
# result = model.transcribe(audio_path, verbose=False)

# # Mostrar resultados
# print("Transcripción:", result["text"])



# from google.cloud import speech
# import os

# def transcribir_audio(audio_path):
#     # Ruta a la carpeta donde están las credenciales
#     credentials_path = os.path.join(os.getcwd(), "Credentials", "Both_APIs.json")
#     os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

#     # Crear un cliente de la API de Speech-to-Text
#     client = speech.SpeechClient()

#     # Leer el archivo de audio
#     with open(audio_path, "rb") as audio_file:
#         audio_content = audio_file.read()

#     # Configurar el reconocimiento
#     audio = speech.RecognitionAudio(content=audio_content)
#     config = speech.RecognitionConfig(
#         encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
#         audio_channel_count=2,
#         sample_rate_hertz=48000,
#         language_code="en-US",
#         alternative_language_codes=["es-US"],  # Detectar inglés y español
#         enable_automatic_punctuation=True
#     )

#     # Enviar la solicitud a la API
#     response = client.recognize(config=config, audio=audio)

#     # Procesar la respuesta
#     transcripcion = ""
#     idioma_detectado = None

#     for result in response.results:
#         transcripcion += result.alternatives[0].transcript
#         idioma_detectado = result.language_code  # Obtener el idioma detectado (si está disponible)

#     return transcripcion, idioma_detectado

# # Ejemplo de uso
# audio_path = "./audio_test/pilin_test_audio.wav"
# transcripcion, idioma = transcribir_audio(audio_path)

# print("Transcripción:", transcripcion)
# if idioma:
#     print("Idioma detectado:", idioma)
# else:
#     print("No se pudo detectar el idioma.")


# from google.cloud import translate_v2 as translate
# import os

# # Establece la variable de entorno para usar el archivo JSON como credencial
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./credentials/Both_APIs.json"

# def translate_text(text, target_language="es"):
#     translate_client = translate.Client()
#     result = translate_client.translate(text, target_language=target_language)
#     print(f"Texto original: {text}")
#     print(f"Texto traducido: {result['translatedText']}")

# # Traduce un texto de prueba
# translate_text("Hello, how are you?", "es")



# from transformers import MarianMTModel, MarianTokenizer

# # Define los idiomas: source (idioma de origen) y target (idioma de destino)
# src_lang = "es"  # Cambia este al idioma de origen (por ejemplo, "es" para español)
# tgt_lang = "en"  # Cambia este al idioma de destino (por ejemplo, "en" para inglés)

# # Carga el modelo y el tokenizador correspondientes
# model_name = f"Helsinki-NLP/opus-mt-{src_lang}-{tgt_lang}"
# tokenizer = MarianTokenizer.from_pretrained(model_name)
# model = MarianMTModel.from_pretrained(model_name)

# # Texto a traducir
# text = "Hola, ¿cómo estás?"

# # Traducción
# inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
# translated = model.generate(**inputs)
# translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)

# print("Texto original:", text)
# print("Texto traducido:", translated_text)



# from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer

# # Carga el modelo y el tokenizador
# model_name = "facebook/m2m100_418M"  # Tamaño base; hay versiones más grandes si necesitas mayor calidad
# tokenizer = M2M100Tokenizer.from_pretrained(model_name)
# model = M2M100ForConditionalGeneration.from_pretrained(model_name)

# # Función para traducir
# def translate(text, src_lang, tgt_lang):
#     tokenizer.src_lang = src_lang  # Idioma de origen
#     encoded_text = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
#     generated_tokens = model.generate(**encoded_text, forced_bos_token_id=tokenizer.get_lang_id(tgt_lang))
#     return tokenizer.decode(generated_tokens[0], skip_special_tokens=True)

# # Pruebas
# text_es = "Hola, ¿cómo estás?"  # Español a Inglés
# text_en = "Hello, how are you?"  # Inglés a Español

# translated_to_en = translate(text_es, "es", "en")
# translated_to_es = translate(text_en, "en", "es")

# print("Texto original (ES):", text_es)
# print("Traducido al Inglés:", translated_to_en)
# print("Texto original (EN):", text_en)
# print("Traducido al Español:", translated_to_es)




####################################################################################
# import threading
# import time
# import numpy as np
# import sounddevice as sd
# import whisper
# from collections import deque

# # ----------------------------
# # Configuraciones generales
# # ----------------------------
# SAMPLERATE = 16000                     # Tasa de muestreo en Hz
# PARTIAL_WINDOW_DURATION = 2.0          # Duración de la ventana para transcripción parcial (en segundos)
# PARTIAL_WINDOW_SAMPLES = int(SAMPLERATE * PARTIAL_WINDOW_DURATION)
# PARTIAL_UPDATE_INTERVAL = 0.7          # Intervalo de actualización (en segundos)

# # ----------------------------
# # Buffer compartido para el audio
# # ----------------------------
# audio_buffer = deque()     # Almacenamos las muestras de audio
# buffer_lock = threading.Lock()

# # ----------------------------
# # Cargar modelos de Whisper
# # ----------------------------
# # Modelo rápido para transcripción parcial (ventana deslizante)
# partial_model = whisper.load_model("tiny")
# # Modelo más robusto para la transcripción completa (al detectar pausa)
# full_model = whisper.load_model("base")

# # ----------------------------
# # Callback de captura de audio
# # ----------------------------
# def audio_callback(indata, frames, time_info, status):
#     if status:
#         print("Status:", status)
#     with buffer_lock:
#         # Se toma el canal 0 y se añade al buffer
#         audio_buffer.extend(indata[:, 0].tolist())

# # ----------------------------
# # Hilo para transcripción parcial (ventana deslizante)
# # ----------------------------
# def partial_transcription_thread():
#     last_partial = ""
#     while True:
#         time.sleep(PARTIAL_UPDATE_INTERVAL)
#         with buffer_lock:
#             # Esperar hasta tener suficiente audio para la ventana
#             if len(audio_buffer) < PARTIAL_WINDOW_SAMPLES:
#                 continue
#             # Se toma la ventana de los últimos PARTIAL_WINDOW_SAMPLES
#             window_audio = list(audio_buffer)[-PARTIAL_WINDOW_SAMPLES:]
#         audio_chunk = np.array(window_audio, dtype=np.float32)
#         try:
#             result = partial_model.transcribe(audio_chunk, fp16=False, language="es", task="transcribe")
#             partial_text = result["text"].strip()
#             if partial_text:
#                 # Si el nuevo resultado es una extensión del anterior, imprimir solo la parte agregada
#                 if partial_text.startswith(last_partial) and len(partial_text) > len(last_partial):
#                     added = partial_text[len(last_partial):]
#                     print(added, end="", flush=True)
#                 # Si el resultado es diferente (por correcciones, por ejemplo), imprimir en una nueva línea
#                 elif partial_text != last_partial:
#                     print("\n[Parcial] " + partial_text)
#                 last_partial = partial_text
#         except Exception as e:
#             print("\nError en transcripción parcial:", e)

# # ----------------------------
# # Hilo para detección de silencio y transcripción completa
# # ----------------------------
# def full_transcription_thread():
#     SILENCE_THRESHOLD = 0.01  # Umbral de silencio (ajustable)
#     SILENCE_DURATION = 1.0    # Duración (en segundos) que se considera silencio para disparar la transcripción completa
#     silence_counter = 0.0
#     check_interval = 0.1      # Intervalo para comprobar el nivel de audio

#     while True:
#         time.sleep(check_interval)
#         with buffer_lock:
#             if len(audio_buffer) < int(SAMPLERATE * check_interval):
#                 continue
#             # Se extrae el fragmento correspondiente al intervalo de comprobación
#             recent_samples = list(audio_buffer)[-int(SAMPLERATE * check_interval):]
#         amplitude = np.abs(np.array(recent_samples)).mean()
#         if amplitude < SILENCE_THRESHOLD:
#             silence_counter += check_interval
#         else:
#             silence_counter = 0.0

#         if silence_counter >= SILENCE_DURATION:
#             with buffer_lock:
#                 if not audio_buffer:
#                     continue
#                 # Se toma todo el audio acumulado para la transcripción completa
#                 full_audio = np.array(audio_buffer, dtype=np.float32)
#                 audio_buffer.clear()  # Se limpia el buffer para la siguiente oración
#             if full_audio.size > 0:
#                 try:
#                     result = full_model.transcribe(full_audio, fp16=False, language="es", task="transcribe")
#                     full_text = result["text"].strip()
#                     print("\n[Completa] " + full_text)
#                 except Exception as e:
#                     print("\nError en transcripción completa:", e)
#             silence_counter = 0.0

# # ----------------------------
# # Función principal
# # ----------------------------
# def main():
#     stream = sd.InputStream(callback=audio_callback, channels=1, samplerate=SAMPLERATE)
#     with stream:
#         t_partial = threading.Thread(target=partial_transcription_thread, daemon=True)
#         t_full = threading.Thread(target=full_transcription_thread, daemon=True)
#         t_partial.start()
#         t_full.start()
#         print("Grabando... Presiona Ctrl+C para detener.")
#         try:
#             while True:
#                 time.sleep(1)
#         except KeyboardInterrupt:
#             print("\nDetenido.")

# if __name__ == "__main__":
#     main()

####################################################################################

import os
import time
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
import whisper
import sys

# Variables globales para la transcripción parcial acumulada
final_transcription = ""
current_sentence = ""

# ================================
# CONFIGURACIONES
# ================================
SAMPLERATE = 16000         # Tasa de muestreo (Hz)
CHANNELS = 1
# Configuraciones nuevas
DETECTION_THRESHOLD = 0.01      # Para detectar voz en el callback (no modificar este valor a menos que sepas calibrar)
TRIM_THRESHOLD = 0.01           # Para recortar silencios al guardar el segmento
MAX_SEGMENT_DURATION = 7.0     # Máximo de segundos que se permite acumular en el buffer   
SILENCE_DURATION = 0.5          # Duración de silencio (en segundos) para considerar que se terminó de hablar
PARTIAL_WINDOW_DURATION = 2.0   # Duración de la ventana para transcripción parcial (en segundos)
PARTIAL_UPDATE_INTERVAL = 0.5   # Intervalo para actualizar la transcripción parcial (en segundos)

# Directorio donde se guardarán los segmentos con voz
SEGMENTS_DIR = "segments"
os.makedirs(SEGMENTS_DIR, exist_ok=True)

# Cargar el modelo rápido para transcripción parcial (por ejemplo, "tiny")
partial_model = whisper.load_model("tiny")

# ================================
# VARIABLES COMPARTIDAS
# ================================
current_buffer = []      # Acumula muestras del segmento en curso
buffer_lock = threading.Lock()
last_voice_time = None   # Guarda la marca de tiempo de la última detección de voz
segment_start_time = None  # Marca el inicio del segmento actual

# ================================
# FUNCION PARA RECORTAR SILENCIOS
# ================================
def trim_silence(audio, threshold=TRIM_THRESHOLD):
    audio = np.array(audio)
    indices = np.where(np.abs(audio) > threshold)[0]
    if indices.size:
        start = indices[0]
        end = indices[-1] + 1
        return audio[start:end]
    else:
        return np.array([], dtype=audio.dtype)

# ================================
# VERIFICAR SI HAY CONTENIDO EN LOS AUDIOS
# ================================
def is_significant(audio, min_duration=0.3, min_peak=0.02):
    duration = len(audio) / SAMPLERATE
    peak = np.max(np.abs(audio)) if len(audio) > 0 else 0
    return duration >= min_duration and peak >= min_peak


# ================================
# CALLBACK DE CAPTURA DE AUDIO
# ================================
def audio_callback(indata, frames, time_info, status):
    global last_voice_time, segment_start_time
    if status:
        print("Status:", status)
    data = indata[:, 0].tolist()
    with buffer_lock:
        current_buffer.extend(data)
        # Si la amplitud supera el umbral de detección, actualizamos la marca de voz
        if np.abs(np.array(data)).mean() > DETECTION_THRESHOLD:
            last_voice_time = time.time()
            # Si es el comienzo de un segmento, se guarda el timestamp
            if segment_start_time is None:
                segment_start_time = time.time()

# ================================
# HILO DE TRANSCRIPCIÓN PARCIAL
# ================================
def partial_transcription_thread():
    global current_sentence, final_transcription
    while True:
        time.sleep(PARTIAL_UPDATE_INTERVAL)
        with buffer_lock:
            if len(current_buffer) < int(SAMPLERATE * PARTIAL_WINDOW_DURATION):
                continue
            window = current_buffer[-int(SAMPLERATE * PARTIAL_WINDOW_DURATION):]
        audio_chunk = np.array(window, dtype=np.float32)
        try:
            result = partial_model.transcribe(audio_chunk, fp16=False, language="es", task="transcribe")
            new_partial = result["text"].strip()

            # Si el nuevo parcial extiende el current_sentence, acumulamos
            if new_partial.startswith(current_sentence):
                # Se extrae la parte nueva
                appended = new_partial[len(current_sentence):]
                current_sentence += appended
            else:
                # Si no es extensión, consideramos que la frase anterior se terminó
                if current_sentence:
                    final_transcription += current_sentence + " "
                current_sentence = new_partial

            # Para efectos de visualización, se muestra la transcripción acumulada hasta el momento:
            full_text = final_transcription + current_sentence
            sys.stdout.write("\r[Parcial] " + full_text + " " * 10)
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write("\rError en transcripción parcial: " + str(e) + " " * 10)
            sys.stdout.flush()

# ================================
# HILO DE DETECCIÓN DE SILENCIO Y GUARDADO DEL SEGMENTO
# ================================
def segment_writer_thread():
    global current_buffer, last_voice_time, segment_start_time, current_sentence, final_transcription
    while True:
        time.sleep(0.1)
        now = time.time()
        with buffer_lock:
            # Condición para finalizar el segmento: ha pasado SILENCE_DURATION o se excede el máximo
            if last_voice_time is not None and (now - last_voice_time) >= SILENCE_DURATION:
                flush_segment = True
            elif segment_start_time is not None and (now - segment_start_time) >= MAX_SEGMENT_DURATION:
                flush_segment = True
            else:
                flush_segment = False

            if flush_segment and current_buffer:
                # Convertir buffer a numpy array y recortar silencios
                segment = np.array(current_buffer, dtype=np.float32)
                trimmed_segment = trim_silence(segment, threshold=TRIM_THRESHOLD)
                
                if is_significant(trimmed_segment):
                    # Guardar el segmento como un archivo .wav
                    timestamp = int(time.time() * 1000)
                    filename = os.path.join(SEGMENTS_DIR, f"segment_{timestamp}.wav")
                    sf.write(filename, trimmed_segment, SAMPLERATE)
                    print(f"\n[Segmento guardado] {filename}")
                    
                    # Reiniciar transcripciones parciales y acumuladas
                    current_sentence = ""
                    final_transcription = ""
                    #print("\n[Transcripción reiniciada]")
                else:
                    print("\n[Segmento descartado por falta de contenido significativo]")
                
                # Reiniciar buffer y variables
                current_buffer = []
                last_voice_time = None
                segment_start_time = None

# ================================
# FUNCIÓN PRINCIPAL
# ================================
def main():
    # Iniciar hilos de transcripción parcial y escritura de segmento
    t_partial = threading.Thread(target=partial_transcription_thread, daemon=True)
    t_writer = threading.Thread(target=segment_writer_thread, daemon=True)
    t_partial.start()
    t_writer.start()
    
    # Iniciar el stream de audio
    stream = sd.InputStream(callback=audio_callback, channels=CHANNELS, samplerate=SAMPLERATE)
    with stream:
        print("Grabando.\nHabla para iniciar el registro y, cuando pauses, se guardará el segmento.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nDetenido.")

if __name__ == "__main__":
    main()

