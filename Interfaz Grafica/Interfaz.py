import sys
import os
# Agregar la carpeta raíz al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
print(os.path.abspath(os.path.dirname(__file__)))

import threading
import time
from PyQt5 import QtWidgets, uic, QtCore, QtGui  # Cambia a PyQt6 si lo estás usando.
from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal, QObject, QThread, QTimer  # Para manejar flags de maximizar/restaurar.
from PyQt5.QtGui import QMouseEvent, QCursor, QIcon, QTextCursor 
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy 
import config
from audio_handler import record_audio, stop_recording
from speech_processing import process_audio
import pyaudio
import sounddevice as sd


class Translator(QObject):
    text_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def update_translated_text(self):
        print(f"Emitiendo texto traducido: '{config.translated_text}'")  # Mensaje de depuración
        if config.translated_text:  # Solo emite si hay texto
            self.text_changed.emit(config.translated_text)

class AudioRecordingThread(QThread):
    def __init__(self, translator, app_instance, mic_index):
        super().__init__()
        self.translator = translator
        self.app_instance = app_instance
        self.mic_index = mic_index  # Guardar el índice del micrófono

    def run(self):
        record_audio(self.translator, self.app_instance,self.mic_index)

class MainApp(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainApp, self).__init__()
        # Carga el archivo .ui
        uic.loadUi("RTT.ui", self)

        # print(self.Consola)  # Esto debería imprimir información sobre el QScrollArea
        # Agregar un mensaje de prueba
        # self.update_text_edit("Mensaje de prueba: Esto debería aparecer en la interfaz.")

        # Ocultar Rarrow al inicio
        self.Rarrow.hide()
        #Sacarle los iconos a los botones
        self.play.setIcon(QIcon())
        self.pause.setIcon(QIcon())
        self.config.setIcon(QIcon())

        self.messages_layout = QVBoxLayout(self.messages_container)  # Usar layout en el contenedor
        self.messages_layout.setAlignment(Qt.AlignBottom)  # Alinear mensajes en la parte inferior
        self.messages_layout.setSpacing(10)  # Separación entre mensajes

        # Aquí puedes conectar señales y slots.
        self.init_ui()
        self.translator = Translator()
        self.translator.text_changed.connect(self.update_text_edit)

        # Llenar el QComboBox con los micrófonos disponibles
        self.populate_microphone_list()

        # # Agregar un mensaje de prueba
        # self.update_text_edit("Mensaje de prueba: Esto debería aparecer en la interfaz.")

    def populate_microphone_list(self):
        """Llena el QComboBox con los micrófonos disponibles."""
        p = pyaudio.PyAudio()
        microphone_combo_box = self.findChild(QtWidgets.QComboBox, "microphoneComboBox")
        microphone_combo_box.clear()  # Limpiar elementos anteriores

        valid_microphones = []  # Lista para almacenar micrófonos válidos
        latency_threshold = 0.1  # Umbral de latencia en segundos

        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            name = device_info['name']
            max_input_channels = device_info['maxInputChannels']
            default_sample_rate = device_info['defaultSampleRate']
            default_low_input_latency = device_info['defaultLowInputLatency']
            default_high_input_latency = device_info['defaultHighInputLatency']

            # Solo considerar dispositivos de entrada con al menos 1 canal
            if max_input_channels > 0:
                try:
                    # Intentar abrir un flujo de prueba
                    stream = p.open(format=pyaudio.paInt16,
                                    channels=1,
                                    rate=int(default_sample_rate),
                                    input=True,
                                    input_device_index=i)
                    stream.close()  # Si funciona, lo cerramos inmediatamente
                    print(f"Dispositivo válido: {name}, Canales: {max_input_channels}, "
                        f"Tasa de muestreo: {default_sample_rate}, "
                        f"Latencia baja: {default_low_input_latency}, "
                        f"Latencia alta: {default_high_input_latency}")

                    # Filtrar dispositivos por latencia
                    if default_low_input_latency <= latency_threshold and \
                    default_high_input_latency <= latency_threshold:
                        valid_microphones.append((i, name))  # Agregar a la lista de micrófonos válidos
                    else:
                        print(f"Dispositivo omitido por latencia: {name}")

                except Exception as e:
                    print(f"Error al abrir el dispositivo ({name}): {e}")
                    print(f"Detalles del dispositivo: {device_info}")  # Imprimir detalles del dispositivo

        # Agregar los micrófonos válidos al QComboBox
        for index, name in valid_microphones:
            microphone_combo_box.addItem(name)

        p.terminate()  # Terminar PyAudio



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
        self.play.setIcon(QIcon("./imgs/play_white.svg"))
        self.pause.setIcon(QIcon("./imgs/stop_white.svg"))
        self.config.setIcon(QIcon("./imgs/config_white.svg"))

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
        if not config.recording_active:
            print("Iniciando traducción...")
            config.recording_active = True 
            print(config.recording_active) 

            # Obtener el índice del micrófono seleccionado
            mic_index = self.findChild(QtWidgets.QComboBox, "microphoneComboBox").currentIndex()

            try:
                # Intentar iniciar la grabación con el micrófono seleccionado
                self.recording_thread = AudioRecordingThread(self.translator, self, mic_index)
                self.recording_thread.start()

                # Actualizar la interfaz
                self.update_text_edit("Mensaje de prueba: Esto debería aparecer en la interfaz.")
            except Exception as e:
                print(f"Error al intentar grabar con el micrófono: {e}")

                # Si ocurre un error, eliminar el dispositivo del QComboBox
                microphone_combo_box = self.findChild(QtWidgets.QComboBox, "microphoneComboBox")
                current_item = microphone_combo_box.currentText()
                print(f"Error con el micrófono: {current_item}")

                # Eliminar el micrófono problemático de la lista
                microphone_combo_box.removeItem(microphone_combo_box.currentIndex())

                # Mostrar un mensaje al usuario para que seleccione otro dispositivo
                self.update_text_edit(f"El micrófono '{current_item}' causó un error. Por favor, elige otro.")

                # Establecer recording_active como False para evitar bloqueos
                config.recording_active = False
        else:
            print("La grabación ya está activa.")

    
    #Frenar Traduccion
    def stop_translation(self):
        stop_recording()  # Detiene la grabación
        print("Parando traducción...")
        # Reiniciar el estado de las variables
        config.recording_active = False  # Asegúrate de que recording_active se establezca en False

    def update_text_edit(self, new_text):
        print(f"Actualizando texto: {new_text}")  # Mensaje de depuración

        # Crear un nuevo mensaje con estilo fijo
        if new_text:
            new_message = QLabel(new_text)
            new_message.setFixedHeight(50)  # Establecer una altura fija para cada etiqueta
            new_message.setWordWrap(True)  # Permitir el ajuste de línea
            new_message.setStyleSheet("""
                background-color: rgb(231, 231, 231);
                border: 2px solid black;
                border-radius: 5px;
                padding: 2px;
                color: black
            """)
            new_message.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Ancho expansible, altura fija

            # Añadir mensaje al layout
            self.messages_layout.addWidget(new_message)

            # Desplazar automáticamente hacia el mensaje más nuevo
            QTimer.singleShot(10, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        """Posiciona el scroll en la parte inferior."""
        scrollbar = self.Consola.verticalScrollBar()  # Accede a la barra de desplazamiento del QScrollArea
        scrollbar.setValue(scrollbar.maximum())  # Desplaza hacia el final

    #Guardar Configuracion
    def save_config(self):
        print("Guardando configuración...")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())
