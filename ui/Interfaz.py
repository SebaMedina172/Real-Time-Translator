import sys
import os
# Agregar la carpeta raíz al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
print(os.path.abspath(os.path.dirname(__file__)))

import threading
import time
import json
import pyaudio
import sounddevice as sd
import matplotlib.font_manager as fm
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal, QObject, QThread, QTimer  # Para manejar flags de maximizar/restaurar.
from PyQt5.QtGui import QMouseEvent, QCursor, QIcon, QTextCursor
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QColorDialog, QGraphicsDropShadowEffect
from config import config
from modules.audio_handler import record_audio, stop_recording
from modules.speech_processing import process_audio


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
        ui_file_path = os.path.join(os.path.dirname(__file__), 'RTT.ui')
        uic.loadUi(ui_file_path, self)  # Cargar el archivo .ui
        # uic.loadUi("../ui/RTT.ui", self)
        config_style_path = os.path.join(os.path.dirname(__file__), '../config/interface_config.json')
        self.config_style_file = config_style_path

        config_audio_path = os.path.join(os.path.dirname(__file__), '../config/audio_config.json')
        self.config_audio_file = config_audio_path

        self.whisper_model = "base"  # Atributo para almacenar el modelo en minúsculas
        self.font_type = "normal"  # Atributo para almacenar el tipo de fuente en minúsculas
        self.load_style_config()
        self.load_audio_config()
######################################################################################################################
        # Conectar señales de los campos de entrada de los estilos del texto a funciones
        self.findChild(QtWidgets.QComboBox, "style_msg_box").currentTextChanged.connect(self.update_text_style)
        self.findChild(QtWidgets.QSpinBox, "size_msg_spin").valueChanged.connect(self.update_text_size)
        self.findChild(QtWidgets.QPushButton, "color_msg_btn").clicked.connect(self.select_text_color)
        self.findChild(QtWidgets.QComboBox, "type_font_msg").currentTextChanged.connect(self.update_text_type)
        self.findChild(QtWidgets.QSpinBox, "stroke_border_msg").valueChanged.connect(self.update_border_thickness)
        self.findChild(QtWidgets.QPushButton, "color_border_msg").clicked.connect(self.select_border_color_msg)
        self.findChild(QtWidgets.QPushButton, "color_bg_msg").clicked.connect(self.select_background_color_msg)
        self.findChild(QtWidgets.QDoubleSpinBox, "opacity_bg_console").valueChanged.connect(self.update_opacity_bg)
        self.findChild(QtWidgets.QPushButton, "bg_color_console").clicked.connect(self.select_bg_color_console)

        # Conectar señales de los campos de entrada de audio a funciones
        self.findChild(QtWidgets.QSpinBox, "rate").valueChanged.connect(self.update_rate)
        self.findChild(QtWidgets.QSpinBox, "chunk_duration").valueChanged.connect(self.update_chunk_duration)
        self.findChild(QtWidgets.QDoubleSpinBox, "voice_window").valueChanged.connect(self.update_voice_window)
        self.findChild(QtWidgets.QDoubleSpinBox, "min_voice_duration").valueChanged.connect(self.update_min_voice_duration)
        self.findChild(QtWidgets.QDoubleSpinBox, "max_continuous_speech_time").valueChanged.connect(self.update_max_continuous_speech_time)
        self.findChild(QtWidgets.QDoubleSpinBox, "cut_time").valueChanged.connect(self.update_cut_time)
        self.findChild(QtWidgets.QSpinBox, "threshold").valueChanged.connect(self.update_threshold)
        self.findChild(QtWidgets.QSpinBox, "vad").valueChanged.connect(self.update_vad)
        self.findChild(QtWidgets.QLineEdit, "temp_dir").editingFinished.connect(self.update_temp_dir)
        self.findChild(QtWidgets.QComboBox, "whisper_model").currentTextChanged.connect(self.update_whisper_model)
############################################################################################################################

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

        # Llenar el QComboBox con las fuentes instaladas
        self.populate_font_styles()

        # # Agregar un mensaje de prueba
        self.update_text_edit("Mensaje de prueba: Esto debería aparecer en la interfaz.")

    #funcion para cargar los mics detectados
    def populate_microphone_list(self):
        """Llena el QComboBox con los micrófonos disponibles y funcionales."""
        p = pyaudio.PyAudio()
        microphone_combo_box = self.findChild(QtWidgets.QComboBox, "microphoneComboBox")
        microphone_combo_box.clear()
        self.microphone_mapping = {}

        latency_threshold = 0.2  # Relajar umbral de latencia

        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            name = device_info['name']
            max_input_channels = device_info['maxInputChannels']
            default_sample_rate = device_info['defaultSampleRate']
            default_low_input_latency = device_info['defaultLowInputLatency']
            default_high_input_latency = device_info['defaultHighInputLatency']

            if max_input_channels > 0:  # Solo dispositivos de entrada
                try:
                    # Intentar abrir un flujo y grabar datos para validar el micrófono
                    stream = p.open(format=pyaudio.paInt16,
                                    channels=1,
                                    rate=int(default_sample_rate),
                                    input=True,
                                    input_device_index=i)
                    frames = stream.read(1024, exception_on_overflow=False)
                    stream.close()
                    
                    # Verificar criterios adicionales
                    if 0.005 <= default_low_input_latency <= latency_threshold and \
                        0.005 <= default_high_input_latency <= latency_threshold:
                        microphone_combo_box.addItem(name)
                        microphone_combo_box.setItemData(microphone_combo_box.count() - 1,name, Qt.ToolTipRole)
                        self.microphone_mapping[name] = i
                        print(f"Micrófono válido añadido: {name}")
                    else:
                        print(f"Micrófono omitido por alta latencia: {name}")
                except Exception as e:
                    print(f"Error al probar el micrófono ({name}): {e}")

        # Si no hay micrófonos válidos, añadir un mensaje al QComboBox
        if microphone_combo_box.count() == 0:
            microphone_combo_box.addItem("No se encontraron micrófonos válidos")

        p.terminate()

    def populate_font_styles(self):
        """Llena el QComboBox con las fuentes instaladas en el sistema."""
        font_combo_box = self.findChild(QtWidgets.QComboBox, "style_msg_box")
        font_combo_box.clear()  # Limpiar elementos anteriores

        # Obtener todas las fuentes instaladas
        font_list = fm.findSystemFonts(fontpaths=None, fontext='ttf')
        font_names = [fm.FontProperties(fname=font).get_name() for font in font_list]

        # Agregar las fuentes al QComboBox
        for font_name in sorted(set(font_names)):  # Usar set para evitar duplicados
            font_combo_box.addItem(font_name)


    def init_ui(self):
        # Ejemplo: Conectar un botón (ajusta los nombres de los objetos según tu diseño).
        self.findChild(QtWidgets.QPushButton, "play").clicked.connect(self.start_translation)
        self.findChild(QtWidgets.QPushButton, "pause").clicked.connect(self.stop_translation)
        self.findChild(QtWidgets.QPushButton, "config").clicked.connect(self.save_all_config) 


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
        self.play.setIcon(QIcon("../ui/imgs/play_white.svg"))
        self.pause.setIcon(QIcon("../ui/imgs/stop_white.svg"))
        self.config.setIcon(QIcon("../ui/imgs/config_white.svg"))

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

######################################################################################################

    #Iniciar Traduccion
    def start_translation(self):
        if not config.recording_active:
            print("Iniciando traducción...")
            config.recording_active = True 
            print(config.recording_active) 

            # Obtener el índice del micrófono seleccionado
            microphone_combo_box = self.findChild(QtWidgets.QComboBox, "microphoneComboBox")
            selected_microphone_name = microphone_combo_box.currentText()  # Obtener el nombre seleccionado
            mic_index = self.microphone_mapping.get(selected_microphone_name)  # Obtener el índice real del dispositivo

            try:
                # Intentar iniciar la grabación con el micrófono seleccionado
                self.recording_thread = AudioRecordingThread(self.translator, self, mic_index)
                self.recording_thread.start()

                # Actualizar la interfaz
                self.success_msg("Traduccion iniciada, prueba hablar")
            except Exception as e:
                print(f"Error al intentar grabar con el micrófono: {e}")

                # Si ocurre un error, eliminar el dispositivo del QComboBox
                microphone_combo_box = self.findChild(QtWidgets.QComboBox, "microphoneComboBox")
                current_item = microphone_combo_box.currentText()
                print(f"Error con el micrófono: {current_item}")

                # Eliminar el micrófono problemático de la lista
                microphone_combo_box.removeItem(microphone_combo_box.currentIndex())

                # Mostrar un mensaje al usuario para que seleccione otro dispositivo
                self.error_msg(f"El micrófono '{current_item}' causó un error. Por favor, elige otro.")

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
        self.info_msg("Traduccion detenida")


########################################################################################################
    #Plantilla para mensajes de error
    def error_msg(self, new_text):
        print(f"Actualizando texto: {new_text}")  # Mensaje de depuración

        # Crear un nuevo mensaje con estilo fijo
        if new_text:
            new_message = QLabel(new_text)
            new_message.setFixedHeight(50)  # Establecer una altura fija para cada etiqueta
            new_message.setWordWrap(True)  # Permitir el ajuste de línea

            # Aplicar estilos
            new_message.setStyleSheet(f"""
                background-color: #ffffff;  /* Color de fondo por defecto */
                border: 2px solid #d30000;
                border-radius: 5px;
                padding: 2px;
                color: #ff0000;  /* Aplicar el color del texto */
                font-family: "Arial";  /* Aplicar el estilo de fuente */
                font-size: 12px;  /* Aplicar el tamaño de fuente */
            """)

            # Crear y aplicar el efecto de sombra
            shadow_effect = QGraphicsDropShadowEffect()
            shadow_effect.setBlurRadius(10)  # Radio de desenfoque
            shadow_effect.setXOffset(2)  # Desplazamiento en el eje X
            shadow_effect.setYOffset(2)  # Desplazamiento en el eje Y
            shadow_effect.setColor(QtGui.QColor(0, 0, 0, 160))  # Color de la sombra (RGBA)

            new_message.setGraphicsEffect(shadow_effect)  # Aplicar el efecto de sombra

            new_message.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Ancho expansible, altura fija

            # Añadir mensaje al layout
            self.messages_layout.addWidget(new_message)

            # Desplazar automáticamente hacia el mensaje más nuevo
            QTimer.singleShot(10, self.scroll_to_bottom)
    
    #Plantilla para mensajes de informacion
    def info_msg(self, new_text):
        print(f"Actualizando texto: {new_text}")  # Mensaje de depuración

        # Crear un nuevo mensaje con estilo fijo
        if new_text:
            new_message = QLabel(new_text)
            new_message.setFixedHeight(50)  # Establecer una altura fija para cada etiqueta
            new_message.setWordWrap(True)  # Permitir el ajuste de línea

            # Aplicar estilos
            new_message.setStyleSheet(f"""
                background-color: #ffffff;  /* Color de fondo por defecto */
                border: 2px solid #0000c6;
                border-radius: 5px;
                padding: 2px;
                color: #00009f;  /* Aplicar el color del texto */
                font-family: "Arial";  /* Aplicar el estilo de fuente */
                font-size: 12px;  /* Aplicar el tamaño de fuente */
            """)

            # Crear y aplicar el efecto de sombra
            shadow_effect = QGraphicsDropShadowEffect()
            shadow_effect.setBlurRadius(10)  # Radio de desenfoque
            shadow_effect.setXOffset(2)  # Desplazamiento en el eje X
            shadow_effect.setYOffset(2)  # Desplazamiento en el eje Y
            shadow_effect.setColor(QtGui.QColor(0, 0, 0, 160))  # Color de la sombra (RGBA)

            new_message.setGraphicsEffect(shadow_effect)  # Aplicar el efecto de sombra

            new_message.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Ancho expansible, altura fija

            # Añadir mensaje al layout
            self.messages_layout.addWidget(new_message)

            # Desplazar automáticamente hacia el mensaje más nuevo
            QTimer.singleShot(10, self.scroll_to_bottom)
    
    #Plantilla para mensajes de exito
    def success_msg(self, new_text):
        print(f"Actualizando texto: {new_text}")  # Mensaje de depuración

        # Crear un nuevo mensaje con estilo fijo
        if new_text:
            new_message = QLabel(new_text)
            new_message.setFixedHeight(50)  # Establecer una altura fija para cada etiqueta
            new_message.setWordWrap(True)  # Permitir el ajuste de línea

            # Aplicar estilos
            new_message.setStyleSheet(f"""
                background-color: #ffffff;  /* Color de fondo por defecto */
                border: 2px solid #00b200;
                border-radius: 5px;
                padding: 2px;
                color: #00ac00;  /* Aplicar el color del texto */
                font-family: "Arial";  /* Aplicar el estilo de fuente */
                font-size: 12px;  /* Aplicar el tamaño de fuente */
            """)

            # Crear y aplicar el efecto de sombra
            shadow_effect = QGraphicsDropShadowEffect()
            shadow_effect.setBlurRadius(10)  # Radio de desenfoque
            shadow_effect.setXOffset(2)  # Desplazamiento en el eje X
            shadow_effect.setYOffset(2)  # Desplazamiento en el eje Y
            shadow_effect.setColor(QtGui.QColor(0, 0, 0, 160))  # Color de la sombra (RGBA)

            new_message.setGraphicsEffect(shadow_effect)  # Aplicar el efecto de sombra

            new_message.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Ancho expansible, altura fija

            # Añadir mensaje al layout
            self.messages_layout.addWidget(new_message)

            # Desplazar automáticamente hacia el mensaje más nuevo
            QTimer.singleShot(10, self.scroll_to_bottom)

    # Plantilla para mensajes de configuracion
    def config_msg(self, new_text):
        print(f"Actualizando texto: {new_text}")  # Mensaje de depuración

        # Crear un nuevo mensaje con estilo fijo
        if new_text:
            new_message = QLabel(new_text)
            new_message.setFixedHeight(50)  # Establecer una altura fija para cada etiqueta
            new_message.setWordWrap(True)  # Permitir el ajuste de línea

            # Aplicar estilos
            new_message.setStyleSheet(f"""
                background-color: #ffffff;  /* Color de fondo por defecto */
                border: 2px solid #ff8c00;  /* Color de borde naranja */
                border-radius: 5px;
                padding: 2px;
                color: #ff8c00;  /* Aplicar el color del texto en naranja */
                font-family: "Arial";  /* Aplicar el estilo de fuente */
                font-size: 12px;  /* Aplicar el tamaño de fuente */
            """)

            # Crear y aplicar el efecto de sombra
            shadow_effect = QGraphicsDropShadowEffect()
            shadow_effect.setBlurRadius(10)  # Radio de desenfoque
            shadow_effect.setXOffset(2)  # Desplazamiento en el eje X
            shadow_effect.setYOffset(2)  # Desplazamiento en el eje Y
            shadow_effect.setColor(QtGui.QColor(0, 0, 0, 160))  # Color de la sombra (RGBA)

            new_message.setGraphicsEffect(shadow_effect)  # Aplicar el efecto de sombra

            new_message.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Ancho expansible, altura fija

            # Añadir mensaje al layout
            self.messages_layout.addWidget(new_message)

            # Desplazar automáticamente hacia el mensaje más nuevo
            QTimer.singleShot(10, self.scroll_to_bottom)

###########################################################################################################

    #Actualizar mensajes
    def update_text_edit(self, new_text):
        print(f"Actualizando texto: {new_text}")  # Mensaje de depuración

        # Crear un nuevo mensaje con estilo fijo
        if new_text:
            new_message = QLabel(new_text)
            new_message.setFixedHeight(50)  # Establecer una altura fija para cada etiqueta
            new_message.setWordWrap(True)  # Permitir el ajuste de línea

            # Obtener los valores de configuración
            font_style = self.findChild(QtWidgets.QComboBox, "style_msg_box").currentText()
            font_size = self.findChild(QtWidgets.QSpinBox, "size_msg_spin").value()
            text_color = self.findChild(QtWidgets.QPushButton, "color_msg_btn").styleSheet().split(":")[-1].strip()  # Obtener el color del texto
            font_type = self.findChild(QtWidgets.QComboBox, "type_font_msg").currentText()
            stroke_border = self.findChild(QtWidgets.QSpinBox, "stroke_border_msg").value()
            color_border_msg = self.findChild(QtWidgets.QPushButton, "color_border_msg").styleSheet().split(":")[-1].strip()
            color_bg_msg = self.findChild(QtWidgets.QPushButton, "color_bg_msg").styleSheet().split(":")[-1].strip()

            # Aplicar estilos
            new_message.setStyleSheet(f"""
                background-color: {color_bg_msg};  /* Color de fondo por defecto */
                border: {stroke_border} solid {color_border_msg};
                font-weight: {font_type};
                border-radius: 5px;
                padding: 2px;
                color: {text_color};  /* Aplicar el color del texto */
                font-family: {font_style};  /* Aplicar el estilo de fuente */
                font-size: {font_size}px;  /* Aplicar el tamaño de fuente */
            """)

            # Crear y aplicar el efecto de sombra
            shadow_effect = QGraphicsDropShadowEffect()
            shadow_effect.setBlurRadius(10)  # Radio de desenfoque
            shadow_effect.setXOffset(2)  # Desplazamiento en el eje X
            shadow_effect.setYOffset(2)  # Desplazamiento en el eje Y
            shadow_effect.setColor(QtGui.QColor(0, 0, 0, 160))  # Color de la sombra (RGBA)

            new_message.setGraphicsEffect(shadow_effect)  # Aplicar el efecto de sombra

            new_message.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Ancho expansible, altura fija

            # Añadir mensaje al layout
            self.messages_layout.addWidget(new_message)

            # Desplazar automáticamente hacia el mensaje más nuevo
            QTimer.singleShot(10, self.scroll_to_bottom)
    
    #Funcion para siempre mostrar el ultimo texto impreso
    def scroll_to_bottom(self):
        """Posiciona el scroll en la parte inferior."""
        scrollbar = self.Consola.verticalScrollBar()  # Accede a la barra de desplazamiento del QScrollArea
        scrollbar.setValue(scrollbar.maximum())  # Desplaza hacia el final
    
#####################################################################################################
    #Cargar la configuracion de los estilos guardada en el json
    def load_style_config(self):
        """Carga la configuración desde el archivo JSON."""
        if os.path.exists(self.config_style_file):
            with open(self.config_style_file, 'r') as f:
                config = json.load(f)
                # Aplicar configuración a la interfaz
                self.findChild(QtWidgets.QComboBox, "style_msg_box").setCurrentText(config.get("font_style", "Arial"))
                self.findChild(QtWidgets.QSpinBox, "size_msg_spin").setValue(config.get("font_size", 12))
                self.findChild(QtWidgets.QComboBox, "type_font_msg").setCurrentText(config.get("font_type", "Normal"))
                self.findChild(QtWidgets.QPushButton, "color_msg_btn").setStyleSheet(f"color: {config.get('color_msg', '#000000')};")
                self.findChild(QtWidgets.QSpinBox, "stroke_border_msg").setValue(config.get("stroke_border", 2))
                self.findChild(QtWidgets.QPushButton, "color_border_msg").setStyleSheet(f"border-color: {config.get('color_border_msg', '#000000')};")
                self.findChild(QtWidgets.QPushButton, "color_bg_msg").setStyleSheet(f"background-color: {config.get('color_bg_msg', '#e7e7e7')};")
                self.findChild(QtWidgets.QDoubleSpinBox, "opacity_bg_console").setValue(config.get("opacity_bg_console", 1.0))
                self.findChild(QtWidgets.QPushButton, "bg_color_console").setStyleSheet(f"background-color: {config.get('bg_color_console', '#464d5f')};")

                # Aplicar color de fondo y opacidad al messages_container
                self.apply_messages_container_style(config)

    def load_audio_config(self):
        """Carga la configuración de audio desde el archivo JSON."""
        if os.path.exists(self.config_audio_file):
            with open(self.config_audio_file, 'r') as f:
                audio_config = json.load(f)
                # Aplicar configuración a las variables de la interfaz
                self.findChild(QtWidgets.QSpinBox, "rate").setValue(audio_config.get("RATE", 16000))
                self.findChild(QtWidgets.QSpinBox, "chunk_duration").setValue(audio_config.get("CHUNK_DURATION_MS", 30))
                self.findChild(QtWidgets.QDoubleSpinBox, "voice_window").setValue(audio_config.get("VOICE_WINDOW", 0.4))
                self.findChild(QtWidgets.QDoubleSpinBox, "min_voice_duration").setValue(audio_config.get("MIN_VOICE_DURATION", 0.3))
                self.findChild(QtWidgets.QDoubleSpinBox, "max_continuous_speech_time").setValue(audio_config.get("MAX_CONTINUOUS_SPEECH_TIME", 3))
                self.findChild(QtWidgets.QDoubleSpinBox, "cut_time").setValue(audio_config.get("CUT_TIME", 2))
                self.findChild(QtWidgets.QSpinBox, "vad").setValue(audio_config.get("VAD", 2))
                self.findChild(QtWidgets.QLineEdit, "temp_dir").setText(audio_config.get("TEMP_DIR", './temp'))
                self.findChild(QtWidgets.QSpinBox, "threshold").setValue(audio_config.get("THRESHOLD", 500))
                self.findChild(QtWidgets.QComboBox, "whisper_model").setCurrentText(audio_config.get("WHISPER_MODEL", "tiny"))

#####################################################################################################
    #Guardar ambas configuraciones
    def save_all_config(self):
        """Guarda tanto la configuración de estilos de texto como la de audio."""
        print("Guardando configuración...")

        # Guardar configuración de estilos de texto
        self.save_style_config()  # Esta es la función que ya tienes para guardar estilos

        # Guardar configuración de audio
        self.save_audio_config()  # Esta es la función que implementaste para guardar audio

        self.config_msg("Configuracion guardada exitosamente")
    
    #Guardar configuracion de audio
    def save_audio_config(self):
        """Guarda la configuración de audio en el archivo JSON."""
        print("Guardando configuración de audio...")

        # Recoger los valores de los inputs
        audio_config = {
            "RATE": self.findChild(QtWidgets.QSpinBox, "rate").value(),
            "CHUNK_DURATION_MS": self.findChild(QtWidgets.QSpinBox, "chunk_duration").value(),
            "VOICE_WINDOW": self.findChild(QtWidgets.QDoubleSpinBox, "voice_window").value(),
            "MIN_VOICE_DURATION": self.findChild(QtWidgets.QDoubleSpinBox, "min_voice_duration").value(),
            "MAX_CONTINUOUS_SPEECH_TIME": self.findChild(QtWidgets.QDoubleSpinBox, "max_continuous_speech_time").value(),
            "CUT_TIME": self.findChild(QtWidgets.QDoubleSpinBox, "cut_time").value(),
            "VAD": self.findChild(QtWidgets.QSpinBox, "vad").value(),
            "TEMP_DIR": self.findChild(QtWidgets.QLineEdit, "temp_dir").text(),
            "THRESHOLD": self.findChild(QtWidgets.QSpinBox, "threshold").value(),
            "WHISPER_MODEL": self.whisper_model
        }

        # Guardar en el archivo JSON
        with open(self.config_audio_file, 'w') as f:
            json.dump(audio_config, f, indent=4)  # Usar indent=4 para mejorar la legibilidad

        print("Configuración de audio guardada correctamente.")
        # Opcional: Mostrar un mensaje al usuario
        #Infor MSG para despues
    
    #Guardar configuracion de estilos
    def save_style_config(self):
        print("Guardando configuración de estilos...")
        """Guarda la configuración en el archivo JSON."""
        config = {
            "font_style": self.findChild(QtWidgets.QComboBox, "style_msg_box").currentText(),
            "font_size": self.findChild(QtWidgets.QSpinBox, "size_msg_spin").value(),
            "font_type": self.font_type,
            "color_msg": self.extract_color(self.findChild(QtWidgets.QPushButton, "color_msg_btn").styleSheet()),  # Obtener el color del texto
            "stroke_border": self.findChild(QtWidgets.QSpinBox, "stroke_border_msg").value(),
            "color_border_msg": self.extract_color(self.findChild(QtWidgets.QPushButton, "color_border_msg").styleSheet()),  # Obtener el color del borde
            "color_bg_msg": self.extract_color(self.findChild(QtWidgets.QPushButton, "color_bg_msg").styleSheet()),  # Obtener el color de fondo
            "opacity_bg_console": self.findChild(QtWidgets.QDoubleSpinBox, "opacity_bg_console").value(),
            "color_bg_console": self.extract_color(self.findChild(QtWidgets.QPushButton, "bg_color_console").styleSheet()),  # Obtener el color de fondo de la consola
        }
        with open(self.config_style_file, 'w') as f:
            json.dump(config, f, indent=4)  # Usar indent=4 para mejorar la legibilidad

#####################################################################################################
    def apply_messages_container_style(self, config):
        """Aplica el color de fondo y la opacidad al messages_container."""
        bg_color = config.get("color_bg_console", "#464d5f")  # Color de fondo por defecto
        opacity = config.get("opacity_bg_console", 1.0)  # Opacidad por defecto

        # Aplicar el color de fondo
        self.messages_container.setStyleSheet(f"background-color: {bg_color};")

        # Eliminar cualquier efecto gráfico existente
        self.messages_container.setGraphicsEffect(None)

        # Aplicar opacidad usando un efecto de sombra
        if opacity < 1.0:  # Solo aplicar si la opacidad es menor que 1
            shadow_effect = QtWidgets.QGraphicsOpacityEffect()
            shadow_effect.setOpacity(opacity)  # Establecer la opacidad
            self.messages_container.setGraphicsEffect(shadow_effect)  # Aplicar el efecto al contenedor
        elif opacity == 1.0:
            # Si la opacidad es 1.0, asegurarse de que no haya efecto gráfico
            self.messages_container.setGraphicsEffect(None)

    #Funcion para extraer el color correctamente
    def extract_color(self, style):
        """Extrae el color de un estilo CSS."""
        if "color:" in style:
            return style.split("color:")[-1].strip().split(";")[0]  # Obtener solo el valor del color
        elif "background-color:" in style:
            return style.split("background-color:")[-1].strip().split(";")[0]  # Obtener solo el valor del color de fondo
        return "#000000"  # Valor por defecto si no se encuentra

##################################################################################################################
    #Funciones para tomar correctamente los valores de los inputs de audio
    def update_rate(self):
        """Actualiza la tasa de muestreo basada en el input del usuario."""
        rate = self.findChild(QtWidgets.QSpinBox, "rate").value()
        print(f"Tasa de muestreo actualizada a: {rate} HZ")  # Mensaje de depuración
    
    def update_chunk_duration(self):
        """Actualiza la duración del chunk basada en el input del usuario."""
        chunk_duration = self.findChild(QtWidgets.QSpinBox, "chunk_duration").value()
        print(f"Duración del chunk actualizada a: {chunk_duration} ms")  # Mensaje de depuración

    def update_voice_window(self):
        """Actualiza la ventana de voz basada en el input del usuario."""
        voice_window = self.findChild(QtWidgets.QDoubleSpinBox, "voice_window").value()
        print(f"Ventana de voz actualizada a: {voice_window} seg")  # Mensaje de depuración
    
    def update_min_voice_duration(self):
        """Actualiza la duracion minima de la voz basada en el input del usuario."""
        min_voice_duration = self.findChild(QtWidgets.QDoubleSpinBox, "min_voice_duration").value()
        print(f"Duración mínima de voz actualizada a: {min_voice_duration} seg")  # Mensaje de depuración

    def update_max_continuous_speech_time(self):
        """Actualiza la ventana de voz basada en el input del usuario."""
        max_continuous_speech_time = self.findChild(QtWidgets.QDoubleSpinBox, "max_continuous_speech_time").value()
        print(f"Tiempo máximo de habla continua actualizado a: {max_continuous_speech_time} seg")  # Mensaje de depuración

    def update_cut_time(self):
        """Actualiza la ventana de voz basada en el input del usuario."""
        cut_time = self.findChild(QtWidgets.QDoubleSpinBox, "cut_time").value()
        print(f"Tiempo de corte actualizado a: {cut_time} seg")  # Mensaje de depuración

    def update_threshold(self):
        """Actualiza la ventana de voz basada en el input del usuario."""
        threshold = self.findChild(QtWidgets.QSpinBox, "threshold").value()
        print(f"Umbral actualizado a: {threshold}")  # Mensaje de depuración

    def update_vad(self):
        """Actualiza la ventana de voz basada en el input del usuario."""
        vad = self.findChild(QtWidgets.QSpinBox, "vad").value()
        print(f"VAD actualizado a: {vad}")  # Mensaje de depuración
    
    def update_temp_dir(self):
        """Actualiza la ruta temporal basada en el input del usuario."""
        temp_dir = self.findChild(QtWidgets.QLineEdit, "temp_dir").text()
        print(f"Ruta temporal ingresada: {temp_dir}")  # Mensaje de depuración

        # Validar la ruta solo al perder el foco o al hacer clic en un botón
        if not os.path.exists(temp_dir) and temp_dir != "":
            print("La ruta temporal no es válida. Por favor, ingresa una ruta existente.")
            self.error_msg("La ruta temporal no es válida. Por favor, ingresa una ruta existente.")
            # Aquí puedes limpiar el campo o establecer un valor predeterminado
            self.findChild(QtWidgets.QLineEdit, "temp_dir").clear()  # Limpiar el campo

    def update_whisper_model(self):
        """Actualiza el modelo Whisper basado en el input del usuario."""
        model = self.findChild(QtWidgets.QComboBox, "whisper_model").currentText()
        print(f"Modelo Whisper seleccionado: {model}")  # Mensaje de depuración

        # Diccionario para mapear modelos a sus versiones en minúsculas
        model_mapping = {
            "Tiny": "tiny",
            "Base": "base",
            "Small": "small",
            "Medium": "medium",
            "Large": "large"
        }

        # Obtener el modelo en minúsculas usando el diccionario
        self.whisper_model = model_mapping.get(model, "base")  # Valor por defecto es "base"
        print(f"Modelo Whisper en minúsculas: {self.whisper_model}")  # Mensaje de depuración

##################################################################################################################
    #Funciones para tomar correctamente los valores de los inputs de estilos de texto
    def update_text_style(self):
        """Actualiza el estilo de texto basado en el input del usuario."""
        style = self.findChild(QtWidgets.QComboBox, "style_msg_box").currentText()
        print(f"Estilo de texto actualizado a: {style}")  # Mensaje de depuración
        # Aplicar el estilo a todas las etiquetas que desees
        for label in self.messages_layout.findChildren(QtWidgets.QLabel):
            label.setStyleSheet(f"font-family: {style};")

    def update_text_size(self):
        """Actualiza el tamaño de texto basado en el input del usuario."""
        size = self.findChild(QtWidgets.QSpinBox, "size_msg_spin").value()
        print(f"Tamaño de texto actualizado a: {size}")  # Mensaje de depuración
        # Aplicar el tamaño a todas las etiquetas que desees
        for label in self.messages_layout.findChildren(QtWidgets.QLabel):
            label.setStyleSheet(f"font-size: {size}px;")

    def update_text_type(self):
        """Actualiza el tipo de texto basado en el input del usuario."""
        text_type = self.findChild(QtWidgets.QComboBox, "type_font_msg").currentText()
        print(f"Tipo de texto actualizado a: {text_type}")  # Mensaje de depuración

        # Convertir el tipo de fuente a minúsculas
        self.font_type = text_type.lower()  # Almacenar en minúsculas
        print(f"Tipo de fuente en minúsculas: {self.font_type}")  # Mensaje de depuración
        
        # Aplicar el tipo a todas las etiquetas que desees
        for label in self.messages_layout.findChildren(QtWidgets.QLabel):
            label.setStyleSheet(f"font-weight: {font_weight};")

    def select_text_color(self):
        """Selecciona el color del texto."""
        color = QColorDialog.getColor()
        if color.isValid():
            # Aplicar el color al botón y a las etiquetas
            self.findChild(QtWidgets.QPushButton, "color_msg_btn").setStyleSheet(f"color: {color.name()};")
            print(f"Color de texto seleccionado: {color.name()}")  # Mensaje de depuración

    def update_border_thickness(self):
        """Actualiza el grosor del borde basado en el input del usuario."""
        thickness = self.findChild(QtWidgets.QSpinBox, "stroke_border_msg").value()
        print(f"Grosor del borde actualizado a: {thickness}")  # Mensaje de depuración

    def select_border_color_msg(self):
        """Selecciona el color del texto."""
        color = QColorDialog.getColor()
        if color.isValid():
            # Aplicar el color al botón y a las etiquetas
            self.findChild(QtWidgets.QPushButton, "color_border_msg").setStyleSheet(f"color: {color.name()};")
            print(f"Color de texto seleccionado: {color.name()}")  # Mensaje de depuración

    def select_background_color_msg(self):
        """Selecciona el color del texto."""
        color = QColorDialog.getColor()
        if color.isValid():
            # Aplicar el color al botón y a las etiquetas
            self.findChild(QtWidgets.QPushButton, "color_bg_msg").setStyleSheet(f"color: {color.name()};")
            print(f"Color de texto seleccionado: {color.name()}")  # Mensaje de depuración
    
    def update_opacity_bg(self):
        """Actualiza la opacidad del fondo de la consola."""
        opacity = self.findChild(QtWidgets.QDoubleSpinBox, "opacity_bg_console").value()
        print(f"Opacidad del fondo de la consola actualizada a: {opacity}")  # Mensaje de depuración

        # Eliminar cualquier efecto gráfico existente
        self.messages_container.setGraphicsEffect(None)

        # Aplicar opacidad usando un efecto de sombra
        if opacity < 1.0:
            shadow_effect = QtWidgets.QGraphicsOpacityEffect()
            shadow_effect.setOpacity(opacity)  # Establecer la opacidad
            self.messages_container.setGraphicsEffect(shadow_effect)  # Aplicar el efecto al contenedor
        else:
            # Si la opacidad es 1.0, asegurarse de que no haya efecto gráfico
            self.messages_container.setGraphicsEffect(None)

    def select_bg_color_console(self):
        """Selecciona el color del fondo de la consola."""
        color = QColorDialog.getColor()
        if color.isValid():
            # Aplicar el color al botón
            self.findChild(QtWidgets.QPushButton, "bg_color_console").setStyleSheet(f"background-color: {color.name()};")
            print(f"Color de fondo de la consola seleccionado: {color.name()}")  # Mensaje de depuración
            
            # Aplicar el color de fondo al messages_container
            self.messages_container.setStyleSheet(f"background-color: {color.name()};")

##################################################################################################################

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())
