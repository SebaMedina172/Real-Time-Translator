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
import modules.postprocessor as postprocessor

load_settings()

semaphore = asyncio.Semaphore(3)  # Permite un máximo de 3 hilos simultáneos

# Cargar modelos
model = whisper.load_model(settings["WHISPER_MODEL"]).eval()

# Cargar modelos de traducción según la dirección configurada
trans_direction = settings.get("TRANS_DIRECTION", "Automatico")

if trans_direction == "Automatico":
    # Cargar ambos modelos
    model_es_en = MarianMTModel.from_pretrained(cfg.MARIAN_MODEL_ES).eval()
    tokenizer_es_en = MarianTokenizer.from_pretrained(cfg.MARIAN_MODEL_ES)
    
    model_en_es = MarianMTModel.from_pretrained(cfg.MARIAN_MODEL_EN).eval()
    tokenizer_en_es = MarianTokenizer.from_pretrained(cfg.MARIAN_MODEL_EN)
    
    logger.debug("Modo de traducción: Automatico (se cargan ambos modelos)")
    
elif trans_direction == "En -> Spa":
    # Solo cargar el modelo para traducir de inglés a español
    model_en_es = MarianMTModel.from_pretrained(cfg.MARIAN_MODEL_EN).eval()
    tokenizer_en_es = MarianTokenizer.from_pretrained(cfg.MARIAN_MODEL_EN)
    
    # No se requiere el modelo de Spa -> En
    model_es_en = None
    tokenizer_es_en = None
    
    logger.debug("Modo de traducción: En -> Spa (se carga únicamente el modelo de inglés a español)")
    
elif trans_direction == "Spa -> En":
    # Solo cargar el modelo para traducir de español a inglés
    model_es_en = MarianMTModel.from_pretrained(cfg.MARIAN_MODEL_ES).eval()
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

#Evaluar si utilizar postprocesado
def should_postprocess(text: str, context: str) -> bool:
    logger.debug(f"[should_postprocess] Longitud del texto: {len(text)}; Contexto: '{context}'")
    
    # Reducir el umbral de longitud para mensajes cortos
    if len(text) < 15:
        logger.debug("[should_postprocess] Texto demasiado corto, no se activa postprocesado")
        return False
    
    # Si el contexto (texto plano) es muy corto, no se activa
    if not context.strip() or len(context.strip()) < 10:
        logger.debug("[should_postprocess] Contexto vacío o muy corto, no se activa postprocesado")
        return False

    text_lower = text.lower()

    # Verificar la presencia de pronombres ambiguos
    pronouns = [' he ', ' she ', ' it ', ' they ', ' él ', ' ella ', ' eso ', ' ellos ', ' ellas ']
    if any(pronoun in text_lower for pronoun in pronouns):
        logger.debug("[should_postprocess] Se detectaron pronombres ambiguos, se activa postprocesado")
        return True

    # Verificar la presencia de signos de interrogación, exclamación o puntos suspensivos
    extra_keywords = ['?', '!', '...']
    if any(keyword in text for keyword in extra_keywords):
        logger.debug("[should_postprocess] Se detectaron signos de interrogación/exclamación, se activa postprocesado")
        return True

    # Opcionalmente, para pruebas, puedes forzar la activación:
    # logger.debug("[should_postprocess] Forzando activación del postprocesado para pruebas")
    # return True

    logger.debug("[should_postprocess] Criterio no cumplido, no se activa postprocesado")
    return False

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

    # Verificar permisos y tamaño del archivo (por ejemplo, mínimo 1 KB)
    if not os.access(audio_file_abs, os.R_OK):
        raise PermissionError(f"No se puede leer el archivo: {audio_file_abs}")

    file_size = os.path.getsize(audio_file_abs)
    if file_size < 1024:  # Umbral mínimo (puedes ajustar este valor)
        logger.debug("El archivo de audio es demasiado pequeño, se omite el procesamiento.")
        return None
    
    try:
        
        #logger.debug(f"Verificando existencia antes de transcribir: {os.path.exists(audio_file_abs)}")
        #logger.debug(f"Permisos de lectura antes de transcribir: {os.access(audio_file_abs, os.R_OK)}")
        
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

        # Obtener la configuración de dirección de traducción
        trans_direction = settings.get("TRANS_DIRECTION", "Automatico")
        logger.debug(f"Modo de traducción configurado: {trans_direction}")

        # En modo fijo se omite la detección de idioma y se fuerza el valor:
        if trans_direction == "En -> Spa":
            # Se asume que el audio es inglés, sin importar lo que diga Whisper
            forced_language = "en"
            logger.debug("Forzando dirección: se asume inglés (En -> Spa)")
        elif trans_direction == "Spa -> En":
            # Se asume que el audio es español
            forced_language = "es"
            logger.debug("Forzando dirección: se asume español (Spa -> En)")
        else:
            # En modo automático se usa lo detectado
            forced_language = result.get('language')
            if not forced_language:
                logger.debug("No se detectó idioma en la transcripción.")
                return None
            logger.debug(f"Idioma detectado: {forced_language}")

        # Realizar la segmentación utilizando pysbd con el idioma forzado
        lang_code = 'es' if forced_language == 'es' else 'en'
        segmenter = SEGMENTERS[lang_code]
        sentences = segmenter.segment(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            logger.debug("No se obtuvieron oraciones después de la segmentación.")
            return None
        
        # Procesar y traducir cada oración usando el modelo adecuado
        translated_sentences = []
        for sentence in sentences:
            if not sentence:
                continue
            try:
                if forced_language == "es":
                    # En modo fijo Spa -> En se asume que el audio es español,
                    # por lo que se traduce de español a inglés
                    if model_es_en is None:
                        logger.error("El modelo para Spa -> En no está cargado.")
                        continue
                    translated = await translate_marian(sentence, tokenizer_es_en, model_es_en)
                else:
                    # En modo fijo En -> Spa se asume que el audio es inglés,
                    # por lo que se traduce de inglés a español
                    if model_en_es is None:
                        logger.error("El modelo para En -> Spa no está cargado.")
                        continue
                    translated = await translate_marian(sentence, tokenizer_en_es, model_en_es)
            except Exception as trans_e:
                logger.error(f"Error al traducir la oración '{sentence}': {trans_e}")
                continue

            if translated and translated not in translated_sentences:
                translated_sentences.append(translated)

        translated_text = " ".join(translated_sentences)
        logger.debug(f"Texto final traducido: {translated_text}")

        # Limpieza de memoria tras la traducción
        cleanup_memory()
        return translated_text if translated_text else None

    except Exception as e:
        logger.debug(f"Error al transcribir o traducir: {e}")
        return None

async def process_audio(audio_file, ui_object):
    try:
        translated_text = await transcribe_and_translate_limited(audio_file)
        if translated_text:
            cfg.translated_text = translated_text
            logger.debug(f"Texto traducido del process: {cfg.translated_text}")
            # Emite la señal para agregar el mensaje en la interfaz
            ui_object.new_message_signal.emit(cfg.translated_text)
            # # Obtén el contexto (por ejemplo, los últimos 2 mensajes)
            # context = ui_object.get_context()
            # if should_postprocess(cfg.translated_text, context):
            #     logger.debug("Se activa el postprocesado automáticamente.")
            #     # Supongamos que el último mensaje agregado tiene el ID almacenado en ui_object.last_msg_id
            #     msg_id = ui_object.last_msg_id
            #     await postprocessor.process_postediting(msg_id, cfg.translated_text, context, ui_object)
            # else:
            #     logger.debug("No se activa el postprocesado (criterio no cumplido).")
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



