import sys
import os
# Agregar la carpeta raíz del proyecto al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging

# Configurar el logger
logging.basicConfig(filename='app.log', level=logging.DEBUG)

import whisper
#from googletrans import Translator
from google.cloud import translate_v2 as translate
import html
import spacy
import config.configuracion as cfg
from config.configuracion import settings, load_settings
import asyncio

load_settings()

# Cargar modelos
model = whisper.load_model(settings["WHISPER_MODEL"])
# translator = Translator()

if getattr(sys, 'frozen', False):
    # Ruta del archivo empaquetado
    base_path = sys._MEIPASS
else:
    # Ruta durante el desarrollo
    base_path = os.path.dirname(__file__)
    
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        # Ruta en caso de estar empaquetado
        base_path = sys._MEIPASS
    else:
        # Ruta en modo desarrollo
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

json_path = get_resource_path("credentials/service_account.json")
translator = translate.Client.from_service_account_json(json_path)

nlp_es = spacy.load(cfg.SPACY_MODEL_ES)
nlp_en = spacy.load(cfg.SPACY_MODEL_EN)


def translate_text(text, target_language):
    result = translator.translate(text, target_language=target_language)
    #html.unescape para poder imprimir caracteres especiales
    translated_text = html.unescape(result['translatedText'])
    return translated_text

async def transcribe_and_translate(audio_file):
    logging.debug(f'Archivo pasado al Transcribe: {audio_file}')
    audio_file_abs = os.path.abspath(audio_file)
    logging.debug(f"Ruta absoluta del archivo: {audio_file}")
    if not os.access(audio_file, os.R_OK):
        raise PermissionError(f"No se puede leer el archivo: {audio_file}")
    
    try:
        logging.debug(f"Verificando existencia antes de transcribir: {os.path.exists(audio_file_abs)}")
        logging.debug(f"Permisos de lectura antes de transcribir: {os.access(audio_file_abs, os.R_OK)}")
        # Realiza la transcripción con Whisper
        result = await asyncio.to_thread(model.transcribe, audio_file_abs)
        
        # Extrae el texto de la transcripción
        text = result.get('text', None)
        logging.debug(f"Texto transcripto: {text}")
        
        if not text:
            logging.debug("La transcripción está vacía.")
            return None
        
        # Detecta el idioma de la transcripción
        detected_language = result['language']
        logging.debug(f"Idioma detectado: {detected_language}")

        # Segmentación del texto usando spaCy según el idioma detectado
        if detected_language == "es":
            doc = nlp_es(text)
            target_language = 'en'
        elif detected_language == "en":
            doc = nlp_en(text)
            target_language = 'es'
        else:
            logging.debug("Idioma no soportado.")
            return None
        
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        # Dividir el texto en partes más pequeñas basadas en las pausas naturales
        translated_sentences = []
        for sentence in sentences:
            translated_result = await asyncio.to_thread(translate_text, sentence, target_language)
            translated_sentences.append(translated_result)
        
        translated_text = " ".join(translated_sentences)
        
        return translated_text
    
    except FileNotFoundError as e:
        logging.debug(f"FileNotFoundError: {e}")
    except Exception as e:
        logging.debug(f"Error al transcribir o traducir: {e}")
        return None

async def process_audio(audio_file, translator):
    try:
        translated_text = await transcribe_and_translate(audio_file)
        if translated_text:  # Solo actualiza si hay texto traducido
            cfg.translated_text = translated_text
            logging.debug(f"Texto traducido: {cfg.translated_text}")
            translator.update_translated_text()
        else:
            logging.debug("No se actualiza el texto traducido porque está vacío.")
    except Exception as e:
        logging.debug(f"Error en el procesamiento de audio: {e}")
    # finally:
    #     try:
    #         os.remove(audio_file)
    #     except Exception as e:
    #         logging.debug(f"Error al eliminar archivo: {e}")



