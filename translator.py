from transformers import pipeline

# Cargar los pipelines de traducción una sola vez al importar este módulo
translator_es_en = pipeline("translation", model="Helsinki-NLP/opus-mt-es-en")
translator_en_es = pipeline("translation", model="Helsinki-NLP/opus-mt-en-es")

def translate_text(text, detected_lang):
    """
    Traduce el texto dependiendo del idioma detectado:
      - Si detected_lang es "es", traduce de español a inglés.
      - Si detected_lang es "en", traduce de inglés a español.
      - En caso contrario, retorna el texto sin traducir.
    """
    if detected_lang == "es":
        result = translator_es_en(text, max_length=512)
        return result[0]["translation_text"]
    elif detected_lang == "en":
        result = translator_en_es(text, max_length=512)
        return result[0]["translation_text"]
    else:
        return text