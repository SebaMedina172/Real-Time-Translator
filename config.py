# obs_helper.py
HOST = "localhost"
PORT = 4455
PASSWORD = ""
SCENE_NAME = "Escena 2" #Por ahora irrelevante, pero puede que si futuras actualizaciones
TARGET_SOURCE_NAME = "destraduccion"


# Configuración de audio
RATE = 16000
CHUNK_DURATION_MS = 30
CHUNK = int(RATE * CHUNK_DURATION_MS / 1000)
VOICE_WINDOW = 0.4
MIN_VOICE_DURATION = 0.3
MAX_CONTINUOUS_SPEECH_TIME = 5  # Máximo tiempo de grabación continua en segundos

TEMP_DIR = './temp' #Ruta de la carpeta donde se guardan los archivos temporales
THRESHOLD = 500 #umbral de silencio minimo para detectarlo como audio

# Configuración de idiomas y modelos
WHISPER_MODEL = "base"  # Puedes cambiar el modelo si prefieres mayor precisión
SPACY_MODEL = "es_core_news_sm"  # Modelo spaCy para segmentación de oraciones 
