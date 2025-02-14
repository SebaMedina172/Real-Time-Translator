import sys
import os
# Agregar la carpeta raíz del proyecto al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from logging.handlers import RotatingFileHandler

# Configuración del logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('app.log', maxBytes=5 * 1024 * 1024, backupCount=5)  # 5 MB por archivo, hasta 5 backups
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

import whisper
from transformers import MarianMTModel, MarianTokenizer
from pysbd import Segmenter  
import config.configuracion as cfg
from config.configuracion import settings, load_settings
import asyncio
import torch

load_settings()

semaphore = asyncio.Semaphore(3)  # Permite un máximo de 3 hilos simultáneos

# Cargar modelos
model = whisper.load_model(settings["WHISPER_MODEL"]).eval()

model_es_en = MarianMTModel.from_pretrained(cfg.MARIAN_MODEL_ES).eval()
tokenizer_es_en = MarianTokenizer.from_pretrained(cfg.MARIAN_MODEL_ES)

model_en_es = MarianMTModel.from_pretrained(cfg.MARIAN_MODEL_EN).eval()
tokenizer_en_es = MarianTokenizer.from_pretrained(cfg.MARIAN_MODEL_EN)

SEGMENTERS = {
    'es': Segmenter(language='es', clean=False),
    'en': Segmenter(language='en', clean=False)
}

if getattr(sys, 'frozen', False):
    # Ruta del archivo empaquetado
    base_path = sys._MEIPASS
else:
    # Ruta durante el desarrollo
    base_path = os.path.dirname(__file__)

def cleanup_memory():
    """Limpieza optimizada sin spaCy"""
    import gc, torch
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.debug("Limpieza de memoria realizada.")

async def transcribe_and_translate_limited(audio_file):
    async with semaphore:
        return await transcribe_and_translate(audio_file)


async def translate_marian(text, tokenizer, model):
    try:
        encoded_text = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():  # Deshabilita el cálculo de gradientes
            translated_tokens = model.generate(**encoded_text)
        return tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
    finally:
        del encoded_text, translated_tokens


async def transcribe_and_translate(audio_file):
    logger.debug(f'Archivo pasado al Transcribe: {audio_file}')
    audio_file_abs = os.path.abspath(audio_file)
    logger.debug(f"Ruta absoluta del archivo: {audio_file_abs}")
    
    # Verificar permisos de lectura
    if not os.access(audio_file_abs, os.R_OK):
        raise PermissionError(f"No se puede leer el archivo: {audio_file_abs}")
    
    # Verificar que el archivo no esté vacío
    file_size = os.path.getsize(audio_file_abs)
    if file_size == 0:
        logger.debug("El archivo de audio está vacío, se omite el procesamiento.")
        return None
    
    try:
        
        logger.debug(f"Verificando existencia antes de transcribir: {os.path.exists(audio_file_abs)}")
        logger.debug(f"Permisos de lectura antes de transcribir: {os.access(audio_file_abs, os.R_OK)}")
        
        # Realiza la transcripción con Whisper
        with torch.inference_mode():
            result = await asyncio.to_thread(model.transcribe, audio_file_abs)
        
        # Extrae y limpia el texto de la transcripción
        text = result.get('text', '').strip()
        logger.debug(f"Texto transcripto: {text}")

        # Limpieza de memoria al finalizar la transcripcion
        cleanup_memory()
        
        # Verificar que el texto obtenido no esté vacío
        if not text:
            logger.debug("La transcripción está vacía.")
            return None
        
        # Detecta el idioma de la transcripción
        detected_language = result.get('language')
        if not detected_language:
            logger.debug("No se detectó idioma en la transcripción.")
            return None
        logger.debug(f"Idioma detectado: {detected_language}")

        # Segmentación con PySBD
        lang_code = 'es' if detected_language == 'es' else 'en'
        segmenter = SEGMENTERS[lang_code]
        sentences = segmenter.segment(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            logger.debug("No se obtuvieron oraciones después de la segmentación.")
            return None
        
        # Traducir cada oración
        translated_sentences = []
        for sentence in sentences:
            if not sentence:
                continue  # Omitir oraciones vacías
            try:
                if detected_language == "es":
                    translated = await translate_marian(sentence, tokenizer_es_en, model_es_en)
                elif detected_language == "en":
                    translated = await translate_marian(sentence, tokenizer_en_es, model_en_es)
                else:
                    logger.debug(f"Idioma {detected_language} no soportado para traducción.")
                    continue
            except Exception as trans_e:
                logger.error(f"Error al traducir la oración '{sentence}': {trans_e}")
                continue  # Salta esta oración y continúa con la siguiente
            
            if translated not in translated_sentences:
                translated_sentences.append(translated)
        
        translated_text = " ".join(translated_sentences)
        logger.debug(f"Texto final traducido: {translated_text}")

        # Limpieza de memoria tras la traducción
        cleanup_memory()
        return translated_text if translated_text else None
    
    except FileNotFoundError as e:
        logger.debug(f"FileNotFoundError: {e}")
        return None
    except Exception as e:
        logger.debug(f"Error al transcribir o traducir: {e}")
        return None

async def process_audio(audio_file, translator):
    try:
        translated_text = await transcribe_and_translate_limited(audio_file)
        if translated_text:  # Solo actualiza si hay texto traducido
            cfg.translated_text = translated_text
            logger.debug(f"Texto traducido del process: {cfg.translated_text}")
            translator.update_translated_text()
        else:
            logger.debug("No se actualiza el texto traducido porque está vacío.")
    except Exception as e:
        logger.debug(f"Error en el procesamiento de audio: {e}")
    finally:
        try:
            os.remove(audio_file)
        except Exception as e:
            logger.debug(f"Error al eliminar archivo: {e}")
        # Limpieza de memoria al finalizar el proceso
        cleanup_memory()



