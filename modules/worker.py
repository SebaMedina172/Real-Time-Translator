from PyQt5.QtCore import QRunnable, QObject, pyqtSignal
import asyncio
import os
from modules.speech_processing import process_audio, cleanup_memory
import logging
from logging.handlers import RotatingFileHandler
from modules.persistent_loop import get_event_loop  # Importamos nuestro event loop persistente

# Configuración del logger (igual que antes)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('app.log', maxBytes=5 * 1024 * 1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class WorkerSignals(QObject):
    # Señal que enviará el resultado del procesamiento (texto traducido)
    finished = pyqtSignal(str)

class AudioProcessingWorker(QRunnable):
    def __init__(self, audio_file, translator):
        super().__init__()
        self.audio_file = audio_file
        self.translator = translator
        self.signals = WorkerSignals()

    def run(self):
        try:
            # Obtenemos el event loop persistente
            loop = get_event_loop()
            # Enviamos la tarea asíncrona al event loop y obtenemos un Future
            future = asyncio.run_coroutine_threadsafe(
                process_audio(self.audio_file, self.translator), loop
            )
            # Bloqueamos hasta que la tarea termine y obtenemos el resultado
            translated_text = future.result()
            self.signals.finished.emit(translated_text)
        except Exception as e:
            logger.debug(f"Error en el AudioProcessingWorker: {e}")