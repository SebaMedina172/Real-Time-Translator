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
# ------------------ GPU SUPPORT ------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.debug(f"Usando dispositivo para inferencia: {device}")
# Check extra de CUDA
if torch.cuda.is_available():
    logger.debug(f"Torch CUDA version: {torch.version.cuda}")
    logger.debug(f"CUDA device count: {torch.cuda.device_count()}")
    logger.debug(f"GPU name: {torch.cuda.get_device_name(0)}")
else:
    logger.warning("CUDA no está disponible: la inferencia caerá en CPU.")
# -------------------------------------------------
import modules.postprocessor as postprocessor

load_settings()

semaphore = asyncio.Semaphore(3)  # Permite un máximo de 3 hilos simultáneos

# --- Carga de modelos según modo ---
trans_direction = settings.get("TRANS_DIRECTION", "Automatico")

if trans_direction == "Automatico":
    # En modo automático se usa Whisper con detección de idioma
    model = whisper.load_model(settings["WHISPER_MODEL"]).to(device).eval()
    # Cargar ambos modelos de traducción
    model_es_en = MarianMTModel.from_pretrained(cfg.MARIAN_MODEL_ES).to(device).eval()
    tokenizer_es_en = MarianTokenizer.from_pretrained(cfg.MARIAN_MODEL_ES)
    
    model_en_es = MarianMTModel.from_pretrained(cfg.MARIAN_MODEL_EN).to(device).eval()
    tokenizer_en_es = MarianTokenizer.from_pretrained(cfg.MARIAN_MODEL_EN)
    
    logger.debug("Modo de traducción: Automatico (se carga Whisper y ambos modelos de traducción)")
    asr_mode = "whisper"
elif trans_direction == "En -> Spa":
    # En modo unidireccional, forzamos el idioma a inglés para ASR con Whisper
    model = whisper.load_model(settings["WHISPER_MODEL"]).to(device).eval()
    logger.debug("Modo de traducción: En -> Spa (Se usa Whisper forzado a inglés)")
    asr_mode = "whisper_forced"
    forced_language = "en"
    # Cargar únicamente el modelo de traducción de inglés a español
    model_en_es = MarianMTModel.from_pretrained(cfg.MARIAN_MODEL_EN).to(device).eval()
    tokenizer_en_es = MarianTokenizer.from_pretrained(cfg.MARIAN_MODEL_EN)
    
    # No se requiere el modelo de Spa -> En
    model_es_en = None
    tokenizer_es_en = None
    
    logger.debug("Modo de traducción: En -> Spa (se carga únicamente el modelo de inglés a español)") 
elif trans_direction == "Spa -> En":
    # En modo unidireccional, forzamos el idioma a español para ASR con Whisper
    model = whisper.load_model(settings["WHISPER_MODEL"]).to(device).eval()
    logger.debug("Modo de traducción: Spa -> En (Se usa Whisper forzado a español)")
    asr_mode = "whisper_forced"
    forced_language = "es"
    # Cargar únicamente el modelo de traducción de español a inglés
    model_es_en = MarianMTModel.from_pretrained(cfg.MARIAN_MODEL_ES).to(device).eval()
    tokenizer_es_en = MarianTokenizer.from_pretrained(cfg.MARIAN_MODEL_ES)
    
    # No se requiere el modelo de En -> Spa
    model_en_es = None
    tokenizer_en_es = None
    
    logger.debug("Modo de traducción: Spa -> En (se carga únicamente el modelo de español a inglés)")

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
        # Tokenizamos...
        encoded_text = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        # Enviar tensores al mismo dispositivo que el modelo:
        encoded_text = {k: v.to(device) for k, v in encoded_text.items()}
        with torch.no_grad():  # Deshabilita el cálculo de gradientes
            translated_tokens = model.generate(**encoded_text)
        return tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
    finally:
        del encoded_text, translated_tokens

# Función para transcribir usando Whisper (modo automático)
async def transcribe_with_whisper(audio_file):
    logger.debug(f'Archivo pasado al Transcribe (Whisper): {audio_file}')
    audio_file_abs = os.path.abspath(audio_file)
    try:
        with torch.inference_mode():
            result = await asyncio.to_thread(model.transcribe, audio_file_abs)
        transcription_text = result.get('text', '').strip()
    except Exception as e:
        logger.error(f"Error en transcribe_with_whisper: {e}")
        transcription_text = ""
        result = {}
    cleanup_memory()
    return result, transcription_text

# Función para transcribir forzando el idioma con Whisper (modo unidireccional)
async def transcribe_with_whisper_forced(audio_file, forced_language):
    logger.debug(f'Archivo pasado al Transcribe (Whisper forzado): {audio_file}')
    audio_file_abs = os.path.abspath(audio_file)
    with torch.inference_mode():
        result = await asyncio.to_thread(model.transcribe, audio_file_abs, language=forced_language)
    transcription_text = result.get('text', '').strip()
    cleanup_memory()
    return result, transcription_text

def is_transcription_valid(text: str, min_alpha=10, max_repetition_ratio=0.6) -> bool:
    """
    Valida la transcripción:
      - Debe tener al menos min_alpha caracteres alfabéticos.
      - No debe tener una palabra que se repita en más del max_repetition_ratio del total.
    """
    text = text.strip()
    if not text:
        return False
    # Contar caracteres alfabéticos
    alpha_chars = sum(1 for c in text if c.isalpha())
    if alpha_chars < min_alpha:
        return False
    # Dividir en palabras y contar repeticiones
    words = text.split()
    if not words:
        return False
    word_counts = {}
    for word in words:
        w = word.lower()
        word_counts[w] = word_counts.get(w, 0) + 1
    max_freq = max(word_counts.values())
    repetition_ratio = max_freq / len(words)
    # Si alguna palabra ocupa más de un cierto porcentaje, descarta la transcripción
    if repetition_ratio > max_repetition_ratio:
        return False
    return True

async def transcribe_and_translate(audio_file):
    # logger.debug(f'Archivo pasado al Transcribe: {audio_file}')
    audio_file_abs = os.path.abspath(audio_file)
    # logger.debug(f"Ruta absoluta del archivo: {audio_file_abs}")

    # Verificar permisos y tamaño del archivo (por ejemplo, mínimo 1 KB)
    if not os.access(audio_file_abs, os.R_OK):
        raise PermissionError(f"No se puede leer el archivo: {audio_file_abs}")
    if os.path.getsize(audio_file_abs) < 1024:
        logger.debug("El archivo de audio es demasiado pequeño, se omite el procesamiento.")
        return None
    try:
        # Seleccionar ruta según el modo configurado:
        if asr_mode == "whisper":
            result, transcription_text = await transcribe_with_whisper(audio_file)
        elif asr_mode == "whisper_forced":
            result, transcription_text = await transcribe_with_whisper_forced(audio_file, forced_language)
        else:
            raise ValueError("Modo ASR desconocido.")
        
        logger.debug(f"Texto transcripto: {transcription_text}")
        cleanup_memory()
        
        if not transcription_text:
            logger.debug("La transcripción está vacía.")
            return None
        
        # Filtrar transcripciones ruidosas o repetitivas.
        if not is_transcription_valid(transcription_text):
            logger.debug("La transcripción no es válida (ruido o repeticiones excesivas). Se descarta.")
            return None

        # Determinar el idioma para segmentación:
        language_used = forced_language if asr_mode == "whisper_forced" else result.get('language')
        if not language_used:
            logger.debug("No se detectó idioma en la transcripción.")
            return None
        logger.debug(f"Idioma a usar para segmentación: {language_used}")

        lang_code = 'es' if language_used == 'es' else 'en'
        segmenter = SEGMENTERS[lang_code]
        sentences = segmenter.segment(transcription_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            logger.debug("No se obtuvieron oraciones después de la segmentación.")
            return None
        
        # Traducir cada oración usando el modelo de traducción correspondiente:
        translated_sentences = []
        for sentence in sentences:
            if not sentence:
                continue
            try:
                if language_used == "en":
                    # En En -> Spa, traducir de inglés a español.
                    if tokenizer_en_es is None or model_en_es is None:
                        logger.error("El modelo para En -> Spa no está cargado.")
                        continue
                    translated = await translate_marian(sentence, tokenizer_en_es, model_en_es)
                elif language_used == "es":
                    # En Spa -> En, traducir de español a inglés.
                    if tokenizer_es_en is None or model_es_en is None:
                        logger.error("El modelo para Spa -> En no está cargado.")
                        continue
                    translated = await translate_marian(sentence, tokenizer_es_en, model_es_en)
                else:
                    logger.debug("Idioma no soportado para traducción.")
                    continue
            except Exception as trans_e:
                logger.error(f"Error al traducir la oración '{sentence}': {trans_e}")
                continue

            if translated and translated not in translated_sentences:
                translated_sentences.append(translated)

        translated_text = " ".join(translated_sentences)
        logger.debug(f"Texto final traducido: {translated_text}")

        # Limpieza de memoria tras la traducción
        cleanup_memory()
        return (translated_text, transcription_text) if translated_text else None

    except Exception as e:
        logger.debug(f"Error al transcribir o traducir: {e}")
        return None

async def process_audio(audio_file, ui_object):
    try:
        result = await transcribe_and_translate_limited(audio_file)
        if result:
            translation_text, transcription_text = result
            cfg.translated_text = translation_text
            logger.debug(f"Texto traducido del process: {cfg.translated_text}")
            # Agregar el mensaje a la UI y almacenar la transcripción cruda
            msg_id = ui_object.add_message(translation_text, transcription_text)
            logger.debug(f"Mensaje agregado con ID: {msg_id}")
            # Llamar al postprocesado, usando la transcripción cruda
            await postprocessor.handle_new_transcription(transcription_text, msg_id, ui_object)
        else:
            logger.debug("No se actualiza el texto traducido porque está vacío.")
    except Exception as e:
        logger.debug(f"Error en el procesamiento de audio: {e}")
    finally:
        try:
            os.remove(audio_file)
        except Exception as e:
            logger.debug(f"Error al eliminar archivo: {e}")
        cleanup_memory()



