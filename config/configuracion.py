import json
import os

# Variables de estado
translated_text = "Texto Default"
recording_active = False  # Inicializa en False

# Modelos Traduccion: MarianMT
MARIAN_MODEL_ES = "Helsinki-NLP/opus-mt-es-en" 
MARIAN_MODEL_EN = "Helsinki-NLP/opus-mt-en-es"  

# Obtener la ruta absoluta del archivo JSON
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "../config/audio_config.json")

# Configuración predeterminada
settings = {}  # Se carga dinámicamente
CHUNK = None  # Inicialmente sin valor

# Función para cargar configuraciones desde el JSON
def load_settings():
    global settings
    try:
        with open(JSON_PATH, "r") as f:
            # Sobrescribir el contenido de settings con los datos del archivo
            settings.clear()  # Limpia el diccionario existente
            settings.update(json.load(f))
    except Exception as e:
        print(f"Error al cargar la configuración: {e}")
    # print(f"Archivo JSON cargado correctamente: {settings}")

# Calculo dinámico basado en configuraciones cargadas
def calcular_valores_dinamicos():
    global CHUNK
    CHUNK = int(settings["RATE"] * settings["CHUNK_DURATION_MS"] / 1000)
    # print(f"Chunk calculado es: {CHUNK}")

# # Inicializar configuraciones al cargar el módulo
load_settings()  # Carga inicial
calcular_valores_dinamicos()  # Realiza cálculos dinámicos
# print(f"valor de chunk: {CHUNK}")


# # Configuración de audio
# RATE = 16000
# CHUNK_DURATION_MS = 30
# CHUNK = int(RATE * CHUNK_DURATION_MS / 1000)
# VOICE_WINDOW = 0.5 #Tiempo maximo luego de detectar un silencio
# MIN_VOICE_DURATION = 0.3 #Duracion minima para considerarse voz
# MAX_CONTINUOUS_SPEECH_TIME = 5  # Máximo tiempo de grabación continua en segundos
# CUT_TIME = 3  # Segundos para el corte de audio
# THRESHOLD = 500 #umbral de silencio minimo para detectarlo como audio
# VAD = 1  #Sensibilidad
# TEMP_DIR = './temp' #Ruta de la carpeta donde se guardan los archivos temporales
# WHISPER_MODEL = "base"  # Puedes cambiar el modelo si prefieres mayor precisión
# BUFFER_SIZE = 200 # Tamaño del buffer


