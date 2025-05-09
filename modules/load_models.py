# modules/load_models.py
import torch
from transformers import pipeline
import config.configuracion as cfg
from config.configuracion import settings, load_settings

# Asegúrate de cargar la configuración
load_settings()
mode = settings.get("TRANS_DIRECTION", "Automatico")

DEVICE = 0 if torch.cuda.is_available() else -1

translator_en_es = None
translator_es_en = None

if mode in ("Automatico", "En -> Spa"):
    translator_en_es = pipeline(
        "translation_en_to_es",
        model="Helsinki-NLP/opus-mt-en-es",
        tokenizer="Helsinki-NLP/opus-mt-en-es",
        device=DEVICE
    )

if mode in ("Automatico", "Spa -> En"):
    translator_es_en = pipeline(
        "translation_es_to_en",
        model="Helsinki-NLP/opus-mt-es-en",
        tokenizer="Helsinki-NLP/opus-mt-es-en",
        device=DEVICE
    )
