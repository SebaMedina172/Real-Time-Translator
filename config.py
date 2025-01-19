translated_text = "Texto Default"
recording_active = False  # Inicializa en False

# Configuración de audio
RATE = 16000
CHUNK_DURATION_MS = 30
CHUNK = int(RATE * CHUNK_DURATION_MS / 1000)
VOICE_WINDOW = 0.4
MIN_VOICE_DURATION = 0.3
MAX_CONTINUOUS_SPEECH_TIME = 3  # Máximo tiempo de grabación continua en segundos
CUT_TIME = 2  # Segundos para el corte de audio
VAD = 2


TEMP_DIR = './temp' #Ruta de la carpeta donde se guardan los archivos temporales
THRESHOLD = 500 #umbral de silencio minimo para detectarlo como audio

# Configuración de idiomas y modelos
WHISPER_MODEL = "base"  # Puedes cambiar el modelo si prefieres mayor precisión
SPACY_MODEL_ES = "es_core_news_md"  # Modelo spaCy para segmentación de oraciones en español
SPACY_MODEL_EN = "en_core_web_md"  # Modelo spaCy para segmentación de oraciones en ingles


