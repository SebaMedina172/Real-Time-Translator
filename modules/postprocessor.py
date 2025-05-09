import asyncio
import re
from bs4 import BeautifulSoup
from PyQt5.QtCore import QTimer
import difflib
import logging
from logging.handlers import RotatingFileHandler
from modules.load_models import translator_en_es, translator_es_en
import torch

# Configuración del logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('app.log', maxBytes=5 * 1024 * 1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Dispositivo
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Variable global para almacenar el candidato a fusión.
_candidate = None  # Diccionario: {'id': <msg_id>, 'text': <transcription>}
# Variable global para el timer del candidato.
_candidate_timer = None  # Será un objeto QTimer

def start_candidate_timer(ui_object, timeout_ms=6000):
    """Inicia o reinicia el timer para expirar el candidato tras timeout_ms milisegundos."""
    global _candidate_timer
    # Si ya existe, detenerlo y eliminarlo
    if _candidate_timer is not None:
        _candidate_timer.stop()
        _candidate_timer.deleteLater()
    _candidate_timer = QTimer()
    _candidate_timer.setSingleShot(True)
    # Cuando el timer expira, finalizamos el candidato
    _candidate_timer.timeout.connect(lambda: finalize_candidate(ui_object))
    _candidate_timer.start(timeout_ms)

def cancel_candidate_timer():
    """Cancela el timer del candidato si existe."""
    global _candidate_timer
    if _candidate_timer is not None:
        _candidate_timer.stop()
        _candidate_timer.deleteLater()
        _candidate_timer = None

def finalize_candidate(ui_object):
    """
    Finaliza el candidato actual, actualizando la UI con la versión final (si corresponde)
    y descartando el candidato para que el próximo mensaje se trate de forma independiente.
    """
    global _candidate
    if _candidate is not None:
        candidate_id = _candidate['id']
        candidate_text = _candidate['text']
        # Solo se actualiza la UI si se fusionaron al menos dos mensajes.
        if _candidate.get('count', 1) >= 2:
            final_translation = retranslate_text(candidate_text, _candidate["lang"])
            logger.debug(f"Timeout: finalizando candidato {candidate_id} con: {final_translation}")
            QTimer.singleShot(10, lambda: ui_object.update_text_edit(final_translation, candidate_id))
        else:
            logger.debug(f"Timeout: candidato {candidate_id} con count == 1, sin actualización de UI")
        _candidate = None
        cancel_candidate_timer()

def strip_html(html: str) -> str:
    """Extrae el texto plano eliminando etiquetas HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text()

def is_message_incomplete(text: str) -> bool:
    """
    Determina si un mensaje transcripto es potencialmente incompleto.
    Se considera incompleto si no termina en '.', '?' o '!', o si termina en puntos suspensivos.
    """
    text = text.strip()
    if not text:
        return False
    # Si termina en "..." o en elipsis Unicode, o si no termina en un signo fuerte.
    if text.endswith("...") or text.endswith("…") or text[-1] not in ".?!":
        return True
    return False

def is_continuation(prev_text: str, new_text: str) -> bool:
    """
    Determina si el nuevo mensaje parece ser continuación del anterior.
    Ahora:
     - Si prev_text acaba en '...' o '…', lo consideramos incompleto (continúa).
     - Si acaba en ., ?, ! (単), lo consideramos fuerte (no continúa) a menos que
       haya solapamiento de palabras.
    """
    prev = prev_text.strip()
    new = new_text.strip()
    if not prev or not new:
        return False

    # 1) Si hay sufijo de elipsis, tratamos como continuación si arranca en minúscula
    if (prev.endswith("...") or prev.endswith("…")) and new[0].islower():
        return True

    # 2) Si NO acaba en signo fuerte (., ?, !) y empieza en minúscula
    if prev[-1] not in ".?!" and new[0].islower():
        return True

    # 3) Solapamiento de palabras (ignorando puntuación final)
    def tokenize(s):
        return [w.strip(".,?!…") for w in s.split()]

    w1 = tokenize(prev)[-2:]
    w2 = tokenize(new)[:2]
    if w1 and w1 == w2:
        return True

    return False

def token_similarity(word1: str, word2: str) -> float:
    """Calcula la similitud entre dos tokens usando difflib."""
    return difflib.SequenceMatcher(None, word1.lower(), word2.lower()).ratio()

def common_overlap_sequence(words1, words2):
    """
    Busca la mayor secuencia de tokens en común entre el final de words1 y el inicio de words2.
    Retorna el número de tokens en la superposición.
    """
    max_overlap = 0
    for i in range(1, min(len(words1), len(words2)) + 1):
        if " ".join(words1[-i:]).lower() == " ".join(words2[:i]).lower():
            max_overlap = i
    return max_overlap

def smart_fuse_texts(text1: str, text2: str, sim_threshold=0.7, max_removals=2) -> str:
    """
    Fusiona dos textos de forma inteligente:
      - Elimina elipsis ("..." o "…") al final de text1.
      - Divide cada texto en palabras.
      - Si la última palabra de text1 (lw) comienza con la primera de text2 (fw) y la diferencia en longitud es < 3,
        se reemplaza lw por fw y se elimina fw del segundo texto.
      - Si no se cumple lo anterior, se intenta eliminar hasta max_removals tokens del inicio de text2
        si la similitud entre lw y ese token es baja.
      - Luego, se busca la mayor superposición exacta en tokens entre el final de text1 y el inicio de text2,
        eliminando la duplicación.
      - Finalmente, se unen los textos resultantes.
    """
    text1_clean = text1.strip()
    if text1_clean.endswith("...") or text1_clean.endswith("…"):
        text1_clean = text1_clean.rstrip(".…").strip()
    text2_clean = text2.strip()
    
    words1 = text1_clean.split()
    words2 = text2_clean.split()
    
    if not words1:
        return text2_clean
    if not words2:
        return text1_clean

    lw = words1[-1]
    fw = words2[0]
    lw_norm = lw.lower().strip()
    fw_norm = fw.lower().strip()
    
    # Heurística explícita: si lw empieza con fw y la diferencia es menor a 3, reemplazamos.
    if lw_norm.startswith(fw_norm) and (len(lw_norm) - len(fw_norm)) < 3:
        words1[-1] = fw
        words2 = words2[1:]
    else:
        removals = 0
        while words2 and removals < max_removals:
            sim = token_similarity(lw, words2[0])
            if sim < sim_threshold:
                words2.pop(0)
                removals += 1
            else:
                break

    overlap_len = common_overlap_sequence(words1, words2)
    if overlap_len > 0:
        words2 = words2[overlap_len:]
    
    fused_text = " ".join(words1 + words2)
    fused_text = re.sub(r'\s+', ' ', fused_text).strip()
    return fused_text

def fuse_texts(text1: str, text2: str) -> str:
    return smart_fuse_texts(text1, text2)

def retranslate_text(text: str, src_lang: str) -> str:
    if src_lang == "en":
        out = translator_en_es(text, max_length=text.count(" ")+50, num_beams=4, early_stopping=True)
    else:
        out = translator_es_en(text, max_length=text.count(" ")+50, num_beams=4, early_stopping=True)
    return out[0]["translation_text"]

##################### ---- Procesamiento iterativo del candidato ---- ##############################
async def process_candidate(new_text: str, new_msg_id: str, ui_object, lang: str):
    """
    Procesa el nuevo mensaje (transcripción cruda) junto con el candidato acumulado de forma iterativa.
    
    Flujo:
      - Si no hay candidato y el mensaje es incompleto, se guarda como candidato.
      - Si ya hay candidato y el nuevo mensaje es continuación, se fusiona con el candidato y se actualiza:
            * Se actualiza el candidato internamente con la fusión acumulada.
            * Se actualiza la UI (con la retraducción provisional) usando el ID y se pasa como grupo el ID del candidato.
            * Se llama a la función removeFusedMessages para limpiar los mensajes del grupo.
      - Si el nuevo mensaje no es continuación, se descarta el candidato actual y se evalúa el nuevo mensaje de forma independiente.
    """
    global _candidate
    new_plain = strip_html(new_text)
    
    if not new_plain:
        return
    
    # Si hay candidato previo con distinto idioma, descartar inmediatamente.
    if _candidate is not None and _candidate.get('lang') != lang:
        logger.debug(f"Idioma cambiado de {_candidate.get('lang')} a {lang}, descartando candidato {_candidate['id']}")
        finalize_candidate(ui_object)
        _candidate = None

    # Si no hay candidato, evaluamos el mensaje actual:
    if _candidate is None:
        if is_message_incomplete(new_plain):
            _candidate = {"id": new_msg_id, "text": new_plain, "lang": lang, "count": 1}
            logger.debug(f"Guardado candidato: ID {_candidate['id']} con texto: {_candidate['text']}, lang: {lang}")
            start_candidate_timer(ui_object)
        return
    # Existe candidato con mismo idioma: reiniciar timer.
    start_candidate_timer(ui_object)
    # Si continúa según heurística
    if is_continuation(_candidate['text'], new_plain):
        fused = fuse_texts(_candidate['text'], new_plain)
        _candidate['text'] = fused
        _candidate['count'] += 1
        logger.debug(f"Candidato actualizado (fusionada): {_candidate['text']}, lang: {lang}")
        provisional_translation = retranslate_text(fused, _candidate["lang"])
        QTimer.singleShot(0, lambda: ui_object.update_text_edit(provisional_translation, _candidate['id']))
        ui_object.remove_message(new_msg_id)
        if hasattr(ui_object, "removeFusedMessages"):
            QTimer.singleShot(0, lambda: ui_object.removeFusedMessages(_candidate['id']))
    else:
        logger.debug(f"El mensaje {new_msg_id} no continúa al candidato {_candidate['id']}, lang: {lang}; descartando candidato.")
        finalize_candidate(ui_object)
        # Evaluar nuevo mensaje como posible nuevo candidato
        if is_message_incomplete(new_plain):
            _candidate = {"id": new_msg_id, "text": new_plain, "lang": lang, "count": 1}
            logger.debug(f"Guardado nuevo candidato: ID {_candidate['id']} con texto: {_candidate['text']}, lang: {lang}")
            start_candidate_timer(ui_object)

async def handle_new_transcription(new_text: str, new_msg_id: str, ui_object, lang: str):
    """
    Esta función se llama cada vez que se agrega un mensaje a la UI, utilizando la transcripción cruda.
    """
    await process_candidate(new_text, new_msg_id, ui_object, lang)
