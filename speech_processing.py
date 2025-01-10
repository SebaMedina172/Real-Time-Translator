import whisper
from googletrans import Translator
import spacy
import os
import config
from obs_helper import OBSManager


# Crear una instancia de OBSManager
obs_manager = OBSManager()

# Conectar con OBS
obs_manager.connect()

# Cargar modelos
model = whisper.load_model(config.WHISPER_MODEL)
translator = Translator()
nlp = spacy.load(config.SPACY_MODEL)


def transcribe_and_translate(audio_file):
    try:
        # Realiza la transcripción con Whisper
        result = model.transcribe(audio_file)
        
        # Extrae el texto de la transcripción
        text = result.get('text', None)
        
        if not text:
            print("La transcripción está vacía.")
            return None
        
        # Detecta el idioma de la transcripción
        detected_language = result['language']
        
        # Segmentación del texto usando spaCy para identificar oraciones y pausas naturales
        doc = nlp(text)
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
        
        # Actualizar el texto en OBS con la traducción
        obs_manager.update_text(translated_text)
        
        return translated_text

    except Exception as e:
        print(f"Error al transcribir o traducir: {e}")
        return None

def process_audio(audio_file):
    translated_text = transcribe_and_translate(audio_file)
    if translated_text:
        print(f"Texto traducido: {translated_text}")
    try:
        os.remove(audio_file)
    except Exception as e:
        print(f"Error al eliminar archivo: {e}")
