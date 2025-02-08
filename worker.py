# workers.py
from PyQt5.QtCore import QRunnable, QObject, pyqtSignal
import asyncio
import os
from modules.speech_processing import process_audio, cleanup_memory  # Asegúrate de que las rutas sean correctas
import logging
from logging.handlers import RotatingFileHandler

# Configuración del logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('app.log', maxBytes=5 * 1024 * 1024, backupCount=5)  # 5 MB por archivo, hasta 5 backups
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
            # Ejecutamos la función asíncrona usando asyncio.run, lo que crea y cierra un event loop
            translated_text = asyncio.run(process_audio(self.audio_file, self.translator))
            self.signals.finished.emit(translated_text)
        except Exception as e:
            logger.debug(f"Error en el AudioProcessingWorker: {e}")
        finally:
            try:
                os.remove(self.audio_file)
            except Exception as e:
                logger.debug(f"Error al eliminar el archivo temporal: {e}")
            cleanup_memory()
