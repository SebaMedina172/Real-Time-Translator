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
        result = model.transcribe(audio_file)
        text = result.get('text', None)
        if not text:
            return None

        detected_language = result['language']
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

        translated_sentences = []
        for sentence in sentences:
            if detected_language == "es":
                translated_sentences.append(translator.translate(sentence, src='es', dest='en').text)
            elif detected_language == "en":
                translated_sentences.append(translator.translate(sentence, src='en', dest='es').text)
            else:
                translated_sentences.append(sentence)

        translated_text = " ".join(translated_sentences)
        
        # Actualizar el texto en OBS
        obs_manager.update_text(translated_text)

        return " ".join(translated_sentences)
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
