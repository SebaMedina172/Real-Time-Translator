import sys
import os
# Agregar la carpeta raíz del proyecto al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from logging.handlers import RotatingFileHandler

# Configuración del logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('app.log', maxBytes=5 * 1024 * 1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

import whisper
from pysbd import Segmenter  
import config.configuracion as cfg
from config.configuracion import settings, load_settings
import asyncio
import torch
# -------------------------------------------------
# importamos los pipelines centralizados
from modules.load_models import translator_en_es, translator_es_en
import modules.postprocessor as postprocessor

# ------------------ GPU SUPPORT ------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.debug(f"Usando dispositivo para inferencia: {device}")
if torch.cuda.is_available():
    logger.debug(f"Torch CUDA version: {torch.version.cuda}")
    logger.debug(f"CUDA device count: {torch.cuda.device_count()}")
    logger.debug(f"GPU name: {torch.cuda.get_device_name(0)}")
else:
    logger.warning("CUDA no está disponible: la inferencia caerá en CPU.")
# -------------------------------------------------

load_settings()

semaphore = asyncio.Semaphore(3)  # Permite un máximo de 3 hilos simultáneos
whisper_id = settings["WHISPER_MODEL"].lower()
# --- Carga de Whisper y modo ASR ---
trans_direction = settings.get("TRANS_DIRECTION", "Automatico")
if trans_direction in ("Automatico", "En -> Spa", "Spa -> En"):  
    model = whisper.load_model(whisper_id).to(device).eval()
    if trans_direction == "En -> Spa" or trans_direction == "Spa -> En":
        asr_mode = "whisper_forced"
        forced_language = "en" if trans_direction == "En -> Spa" else "es"
    else:
        asr_mode = "whisper"
logger.debug(f"Modo ASR: {asr_mode}")

SEGMENTERS = {
    'es': Segmenter(language='es', clean=False),
    'en': Segmenter(language='en', clean=False)
}

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)


def cleanup_memory():
    import gc
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.debug("Limpieza de memoria realizada.")

async def transcribe_and_translate_limited(audio_file):
    async with semaphore:
        return await transcribe_and_translate(audio_file)

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

# Función para transcribir forzando el idioma con Whisper
async def transcribe_with_whisper_forced(audio_file, forced_language):
    logger.debug(f'Archivo pasado al Transcribe (Whisper forzado): {audio_file}')
    audio_file_abs = os.path.abspath(audio_file)
    with torch.inference_mode():
        result = await asyncio.to_thread(model.transcribe, audio_file_abs, language=forced_language)
    transcription_text = result.get('text', '').strip()
    cleanup_memory()
    return result, transcription_text


def is_transcription_valid(text: str, min_alpha=10, max_repetition_ratio=0.6) -> bool:
    text = text.strip()
    if not text:
        return False
    alpha_chars = sum(1 for c in text if c.isalpha())
    if alpha_chars < min_alpha:
        return False
    words = text.split()
    if not words:
        return False
    counts = {}
    for w in words:
        lw = w.lower()
        counts[lw] = counts.get(lw, 0) + 1
    if max(counts.values()) / len(words) > max_repetition_ratio:
        return False
    return True

async def transcribe_and_translate(audio_file):
    audio_file_abs = os.path.abspath(audio_file)
    if not os.access(audio_file_abs, os.R_OK) or os.path.getsize(audio_file_abs) < 1024:
        logger.debug("Audio demasiado pequeño o no accesible.")
        return None
    try:
        if asr_mode == "whisper":
            result, transcription_text = await transcribe_with_whisper(audio_file)
        else:
            result, transcription_text = await transcribe_with_whisper_forced(audio_file, forced_language)
        logger.debug(f"Texto transcripto: {transcription_text}")
        cleanup_memory()
        if not transcription_text or not is_transcription_valid(transcription_text):
            return None
        language_used = forced_language if asr_mode == "whisper_forced" else result.get('language')
        if not language_used:
            return None
        logger.debug(f"Idioma para segmentación: {language_used}")
        seg = SEGMENTERS['es' if language_used=='es' else 'en']
        sentences = [s.strip() for s in seg.segment(transcription_text) if s.strip()]
        if not sentences:
            return None
        translated_sentences = []
        for s in sentences:
            try:
                if language_used == 'en' and translator_en_es:
                    out = translator_en_es(s, max_length=s.count(' ')+50, num_beams=4, early_stopping=True)
                elif language_used == 'es' and translator_es_en:
                    out = translator_es_en(s, max_length=s.count(' ')+50, num_beams=4, early_stopping=True)
                else:
                    continue
                translated = out[0]['translation_text']
                if translated and translated not in translated_sentences:
                    translated_sentences.append(translated)
            except Exception as e:
                logger.error(f"Error traduciendo '{s}': {e}")
        final = " ".join(translated_sentences)
        logger.debug(f"Texto final traducido: {final}")
        cleanup_memory()
        return (final, transcription_text, language_used) if final else None
    except Exception as e:
        logger.debug(f"Error en transcribe_and_translate: {e}")
        return None

async def process_audio(audio_file, ui_object):
    try:
        res = await transcribe_and_translate_limited(audio_file)
        if res:
            translation_text, transcription_text, language_used = res
            cfg.translated_text = translation_text
            logger.debug(f"Texto traducido del process: {translation_text}")
            msg_id = ui_object.add_message(translation_text, transcription_text, language_used)
            logger.debug(f"Mensaje agregado: {msg_id}")
            await postprocessor.handle_new_transcription(transcription_text, msg_id, ui_object, language_used)
    finally:
        try: os.remove(audio_file)
        except: pass
        cleanup_memory()
