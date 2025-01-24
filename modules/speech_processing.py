import sys
import os
# Agregar la carpeta raíz del proyecto al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import whisper
from googletrans import Translator
import spacy
import config.configuracion as cfg
from config.configuracion import settings, load_settings
import asyncio

load_settings()

# Cargar modelos
model = whisper.load_model(settings["WHISPER_MODEL"])
translator = Translator()
nlp_es = spacy.load(cfg.SPACY_MODEL_ES)
nlp_en = spacy.load(cfg.SPACY_MODEL_EN)


async def transcribe_and_translate(audio_file):
    try:
        # Realiza la transcripción con Whisper
        result = await asyncio.to_thread(model.transcribe, audio_file)
        
        # Extrae el texto de la transcripción
        text = result.get('text', None)
        print(f"Texto transcripto: {text}")
        
        if not text:
            print("La transcripción está vacía.")
            return None
        
        # Detecta el idioma de la transcripción
        detected_language = result['language']
        print(f"Idioma detectado: {detected_language}")

        # Segmentación del texto usando spaCy según el idioma detectado
        if detected_language == "es":
            doc = nlp_es(text)
        elif detected_language == "en":
            doc = nlp_en(text)
        else:
            print("Idioma no soportado.")
            return None
        
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        # Dividir el texto en partes más pequeñas basadas en las pausas naturales
        translated_sentences = []
        for sentence in sentences:
            # Traducir de forma bidireccional según el idioma detectado
            if detected_language == "es":
                translated_result = await asyncio.to_thread(translator.translate, sentence, src='es', dest='en')
                translated_sentences.append(translated_result.text)  # Accede al atributo text
            elif detected_language == "en":
                translated_result = await asyncio.to_thread(translator.translate, sentence, src='en', dest='es')
                translated_sentences.append(translated_result.text)  # Accede al atributo text
            else:
                translated_sentences.append(sentence)
        
        translated_text = " ".join(translated_sentences)
        
        return translated_text

    except Exception as e:
        print(f"Error al transcribir o traducir: {e}")
        return None

async def process_audio(audio_file, translator):
    try:
        translated_text = await transcribe_and_translate(audio_file)
        if translated_text:  # Solo actualiza si hay texto traducido
            cfg.translated_text = translated_text
            print(f"Texto traducido: {cfg.translated_text}")
            translator.update_translated_text()
        else:
            print("No se actualiza el texto traducido porque está vacío.")
    except Exception as e:
        print(f"Error en el procesamiento de audio: {e}")
    finally:
        try:
            os.remove(audio_file)
        except Exception as e:
            print(f"Error al eliminar archivo: {e}")



