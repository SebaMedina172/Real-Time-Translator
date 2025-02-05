import sys
import os
# Agregar la carpeta raíz del proyecto al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging

# Configurar el logger
logging.basicConfig(filename='app.log', level=logging.DEBUG)

import whisper
from transformers import MarianMTModel, MarianTokenizer
from pysbd import Segmenter  
import config.configuracion as cfg
from config.configuracion import settings, load_settings
import asyncio

load_settings()

semaphore = asyncio.Semaphore(3)  # Permite un máximo de 3 hilos simultáneos

# Cargar modelos
model = whisper.load_model(settings["WHISPER_MODEL"]).eval()

model_es_en = MarianMTModel.from_pretrained(cfg.MARIAN_MODEL_ES).eval()
tokenizer_es_en = MarianTokenizer.from_pretrained(cfg.MARIAN_MODEL_ES)

model_en_es = MarianMTModel.from_pretrained(cfg.MARIAN_MODEL_EN).eval()
tokenizer_en_es = MarianTokenizer.from_pretrained(cfg.MARIAN_MODEL_EN)

if getattr(sys, 'frozen', False):
    # Ruta del archivo empaquetado
    base_path = sys._MEIPASS
else:
    # Ruta durante el desarrollo
    base_path = os.path.dirname(__file__)

# nlp_es = spacy.load(cfg.SPACY_MODEL_ES, disable=["parser", "ner", "lemmatizer"])
# nlp_es.add_pipe("sentencizer")  # Añade el sentencizer al pipeline
# nlp_en = spacy.load(cfg.SPACY_MODEL_EN, disable=["parser", "ner", "lemmatizer"])
# nlp_en.add_pipe("sentencizer")  # Añade el sentencizer al pipeline

def cleanup_memory():
    """Limpieza optimizada sin spaCy"""
    import gc, torch
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logging.debug("Limpieza de memoria realizada.")

async def transcribe_and_translate_limited(audio_file):
    async with semaphore:
        return await transcribe_and_translate(audio_file)


async def translate_marian(text, tokenizer, model):
    try:
        # Tokenizar el texto
        encoded_text = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        # Generar traducción
        translated_tokens = model.generate(**encoded_text)
        # Decodificar la traducción
        translated_text = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
        return translated_text
    finally:
        # Liberar tensores y memoria
        del encoded_text, translated_tokens
        import torch
        torch.cuda.empty_cache() if torch.cuda.is_available() else None


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
        # Limpieza de memoria al finalizar la transcripcion
        cleanup_memory()
        
        if not text:
            logging.debug("La transcripción está vacía.")
            return None
        
        # Detecta el idioma de la transcripción
        detected_language = result['language']
        logging.debug(f"Idioma detectado: {detected_language}")

        # Segmentación con PySBD
        lang_code = 'es' if detected_language == 'es' else 'en'
        segmenter = Segmenter(language=lang_code, clean=False)
        sentences = segmenter.segment(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Dividir el texto en partes más pequeñas basadas en las pausas naturales
        translated_sentences = []
        for sentence in sentences:
            # Definir 'translated' en todos los casos
            if detected_language == "es":
                translated = await translate_marian(sentence, tokenizer_es_en, model_es_en)
            elif detected_language == "en":
                translated = await translate_marian(sentence, tokenizer_en_es, model_en_es)
            else:
                translated = sentence  # Para otros idiomas
            
            # Ahora 'translated' siempre está definido
            if translated not in translated_sentences:
                translated_sentences.append(translated)
        
        translated_text = " ".join(translated_sentences)
        logging.debug(f"Texto final traducido: {translated_text}")
        # Limpieza de memoria tras la traducción
        cleanup_memory()
        return translated_text
    
    except FileNotFoundError as e:
        logging.debug(f"FileNotFoundError: {e}")
    except Exception as e:
        logging.debug(f"Error al transcribir o traducir: {e}")
        return None

async def process_audio(audio_file, translator):
    try:
        translated_text = await transcribe_and_translate_limited(audio_file)
        if translated_text:  # Solo actualiza si hay texto traducido
            cfg.translated_text = translated_text
            logging.debug(f"Texto traducido del process: {cfg.translated_text}")
            translator.update_translated_text()
        else:
            logging.debug("No se actualiza el texto traducido porque está vacío.")
    except Exception as e:
        logging.debug(f"Error en el procesamiento de audio: {e}")
    finally:
        try:
            os.remove(audio_file)
        except Exception as e:
            logging.debug(f"Error al eliminar archivo: {e}")
        # Limpieza de memoria al finalizar el proceso
        cleanup_memory()



