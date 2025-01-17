import sys
import os
# Agregar la carpeta raíz al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
print(os.path.abspath(os.path.dirname(__file__)))

import threading
import time
from PyQt5 import QtWidgets, uic, QtCore, QtGui  # Cambia a PyQt6 si lo estás usando.
from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal, QObject, QThread  # Para manejar flags de maximizar/restaurar.
from PyQt5.QtGui import QMouseEvent, QCursor, QIcon
import config
from audio_handler import record_audio, stop_recording
from speech_processing import process_audio

class Translator(QObject):
    text_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def update_translated_text(self):
        self.text_changed.emit(config.translated_text)

class AudioRecordingThread(QThread):
    def __init__(self, translator, app_instance):
        super().__init__()
        self.translator = translator
        self.app_instance = app_instance

    def run(self):
        record_audio(self.translator, self.app_instance)

class MainApp(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainApp, self).__init__()
        # Carga el archivo .ui
        uic.loadUi("RTT.ui", self)

        # Ocultar Rarrow al inicio
        self.Rarrow.hide()
        #Sacarle los iconos a los botones
        self.play.setIcon(QIcon())
        self.pause.setIcon(QIcon())
        self.config.setIcon(QIcon())

        # Aquí puedes conectar señales y slots.
        self.init_ui()
        self.translator = Translator()
        self.translator.text_changed.connect(self.update_text_edit)

    def init_ui(self):
        # Ejemplo: Conectar un botón (ajusta los nombres de los objetos según tu diseño).
        self.findChild(QtWidgets.QPushButton, "play").clicked.connect(self.start_translation)
        self.findChild(QtWidgets.QPushButton, "pause").clicked.connect(self.stop_translation)
        self.findChild(QtWidgets.QPushButton, "config").clicked.connect(self.save_config)


        #Botones para la compresion de los botones
        self.findChild(QtWidgets.QPushButton, "Larrow").clicked.connect(self.shrink_frame)
        self.findChild(QtWidgets.QPushButton, "Rarrow").clicked.connect(self.expand_frame)
        # Guardar referencias a los frames y botones
        self.frame_with_buttons = self.findChild(QtWidgets.QFrame, "column_1")
        self.larrow_button = self.findChild(QtWidgets.QPushButton, "Larrow")
        self.rarrow_button = self.findChild(QtWidgets.QPushButton, "Rarrow")
        #Guardar el ancho original del frame y de los botones
        self.original_frame_width = 250
        self.shrunk_frame_width = 100  # Ancho reducido para el frame.
    
    #Colapsar los botones
    def shrink_frame(self):
         # Acceder al frame 'column_1' desde el botón
        frame = self.sender().parent().parent()  # Usamos .parent() dos veces, una para el frame del botón y otra para column_1
        frame.setFixedWidth(self.shrunk_frame_width)  # Reducir el ancho.

        # Ocultar el texto de los botones
        self.play.setText("") 
        self.pause.setText("")
        self.config.setText("")
        self.play.setIcon(QIcon("./imgs/play.svg"))
        self.pause.setIcon(QIcon("./imgs/stop.svg"))
        self.config.setIcon(QIcon("./imgs/config.svg"))

        self.Larrow.hide()  # Ocultar Larrow
        self.Rarrow.show()  # Mostrar Rarrow
    
    def expand_frame(self):
         # Acceder al frame 'column_1' desde el botón
        frame = self.sender().parent().parent()  # Usamos .parent() dos veces, una para el frame del botón y otra para column_1
        frame.setFixedWidth(self.original_frame_width)  # Reducir el ancho.

        # Restaurar el texto de los botones
        self.play.setText("Iniciar Traducciom")  # Ajusta según el texto que desees.
        self.pause.setText("Parar Traduccion")
        self.config.setText("Guardar Configuracion")
        self.play.setIcon(QIcon())
        self.pause.setIcon(QIcon())
        self.config.setIcon(QIcon())

        self.Larrow.show()  # Mostrar Larrow
        self.Rarrow.hide()  # Ocultar Rarrow
    
    #Iniciar Traduccion
    def start_translation(self):
        if not recording_active:
            print("Iniciando traducción...")
            config.recording_active = True 
            print(config.recording_active) 
            # Iniciar el hilo de grabación
            # self.recording_thread = threading.Thread(target=self.start_recording)
            # self.recording_thread.daemon = True
            self.recording_thread = AudioRecordingThread(self.translator, self)
            self.recording_thread.start()
        else:
            print("La grabación ya está activa.")

    
    #Frenar Traduccion
    def stop_translation(self):
        stop_recording()  # Detiene la grabación
        print("Parando traducción...")
        # Reiniciar el estado de las variables
        config.recording_active = False  # Asegúrate de que recording_active se establezca en False

    def update_text_edit(self, new_text):
        current_text = self.Consola.toPlainText()  # Obtiene el texto actual
        if current_text:
            self.Consola.setPlainText(current_text + "\n" + new_text)  # Agrega el nuevo texto
        else:
            self.Consola.setPlainText(new_text)  # Si está vacío, solo establece el nuevo texto

        # Desplazar el cursor al final del QTextEdit
        self.Consola.moveCursor(QtGui.QTextCursor.End)  

    #Guardar Configuracion
    def save_config(self):
        print("Guardando configuración...")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())
