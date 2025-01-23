import sys
import os
# Agregar la carpeta raíz del proyecto al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import whisper
from googletrans import Translator
import spacy
from config import config

# Cargar modelos
model = whisper.load_model(config.WHISPER_MODEL)
translator = Translator()
nlp_es = spacy.load(config.SPACY_MODEL_ES)
nlp_en = spacy.load(config.SPACY_MODEL_EN)


def transcribe_and_translate(audio_file):
    try:
        # Realiza la transcripción con Whisper
        result = model.transcribe(audio_file)
        
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
                translated_sentences.append(translator.translate(sentence, src='es', dest='en').text)
            elif detected_language == "en":
                translated_sentences.append(translator.translate(sentence, src='en', dest='es').text)
            else:
                translated_sentences.append(sentence)
        
        translated_text = " ".join(translated_sentences)
        
        return translated_text

    except Exception as e:
        print(f"Error al transcribir o traducir: {e}")
        return None

def process_audio(audio_file, translator):
    try:
        translated_text = transcribe_and_translate(audio_file)
        if translated_text:  # Solo actualiza si hay texto traducido
            config.translated_text = translated_text
            print(f"Texto traducido: {config.translated_text}")
            translator.update_translated_text()
        else:
            print("No se actualiza el texto traducido porque está vacío.")
    except Exception as e:
        print(f"Error en el procesamiento de audio: {e}")
    # finally:
    #     try:
    #         os.remove(audio_file)
    #     except Exception as e:
    #         print(f"Error al eliminar archivo: {e}")



