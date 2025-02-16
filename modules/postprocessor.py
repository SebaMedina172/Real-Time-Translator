# postprocessor.py

import logging
import asyncio
import torch
import re
from transformers import T5ForConditionalGeneration, T5Tokenizer
from PyQt5.QtCore import pyqtSignal
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Cargar el modelo de post-edición.
POSTEDIT_MODEL_NAME = "t5-small"  # Ejemplo; se recomienda fine-tunear para APE.
postedit_model = T5ForConditionalGeneration.from_pretrained(POSTEDIT_MODEL_NAME).eval()
postedit_tokenizer = T5Tokenizer.from_pretrained(POSTEDIT_MODEL_NAME)

def strip_html(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text()

def remove_repeated_phrases(text: str) -> str:
    sentences = text.split(". ")
    seen = set()
    refined_sentences = []
    for sentence in sentences:
        if sentence not in seen:
            refined_sentences.append(sentence)
            seen.add(sentence)
    return ". ".join(refined_sentences)

def refine_translation(initial_translation: str, context: str) -> str:
    """
    Refina la traducción inicial utilizando el contexto dado.
    El prompt se construye de forma minimalista para que el modelo devuelva únicamente el refinamiento.
    """
    # Formulamos un prompt sencillo:
    prompt = f"{context}\n{initial_translation}\nRefina:"  # Nota: sin etiquetas adicionales.
    inputs = postedit_tokenizer.encode(prompt, return_tensors="pt", truncation=True, max_length=512)
    
    with torch.no_grad():
        outputs = postedit_model.generate(inputs, max_length=512, num_beams=4, early_stopping=True)
    
    refined = postedit_tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Eliminar cualquier parte del prompt que pudiera aparecer:
    refined = re.sub(r"^(.*?Refina:\s*)", "", refined).strip()
    
    # Eliminar repeticiones, si aparecen:
    refined = remove_repeated_phrases(refined)
    
    return refined

async def refine_translation_async(initial_translation: str, context: str) -> str:
    """
    Ejecuta refine_translation de forma asíncrona.
    """
    loop = asyncio.get_event_loop()
    refined = await loop.run_in_executor(None, refine_translation, initial_translation, context)
    return refined

async def process_postediting(msg_id: str, initial_translation: str, context: str, ui_object):
    """
    Refina la traducción y actualiza el mensaje en la interfaz.
    """
    try:
        refined_text = await refine_translation_async(initial_translation, context)
        # Opcional: eliminar cualquier HTML residual si es necesario:
        refined_text = strip_html(refined_text)
        # Limpieza adicional de repeticiones:
        refined_text = remove_repeated_phrases(refined_text)
        logger.debug(f"Post-edited translation for {msg_id}: {refined_text}")
        ui_object.update_message_signal.emit(refined_text, msg_id)
    except Exception as e:
        logger.error(f"Error during post-editing for {msg_id}: {e}")
