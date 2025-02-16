import sys
import os
# Agregar la carpeta raíz al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#logger.debug(os.path.abspath(os.path.dirname(__file__)))

import logging
from logging.handlers import RotatingFileHandler

# Configuración del logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('app.log', maxBytes=5 * 1024 * 1024, backupCount=5)  # 5 MB por archivo, hasta 5 backups
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

import json
import pyaudio
import matplotlib.font_manager as fm
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal, QObject, QThread, QTimer  # Para manejar flags de maximizar/restaurar.
from PyQt5.QtGui import QMouseEvent, QCursor, QIcon, QTextCursor, QColor
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QColorDialog, QGraphicsDropShadowEffect
import config.configuracion as cfg
from config.configuracion import settings, load_settings, calcular_valores_dinamicos
from modules.audio_handler import record_audio, stop_recording
from modules.speech_processing import process_audio
import threading

class Translator(QObject):
    text_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def update_translated_text(self):
        #logger.debug(f"Emitiendo texto traducido: '{cfg.translated_text}'")  # Mensaje de depuración
        if cfg.translated_text:  # Solo emite si hay texto
            self.text_changed.emit(cfg.translated_text)

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
        # ui_file_path = os.path.join(os.path.dirname(__file__), 'RTT_dock.ui')
        uic.loadUi('.\\ui\\RTT_dock_Edit.ui', self)  # Cargar el archivo .ui
        # uic.loadUi("../ui/RTT.ui", self)
        config_style_path = os.path.join(os.path.dirname(__file__), '..\\config\\interface_config.json')
        self.config_style_file = config_style_path

        config_audio_path = os.path.join(os.path.dirname(__file__), '..\\config\\audio_config.json')
        self.config_audio_file = config_audio_path

        self.whisper_model = "base"  # Atributo para almacenar el modelo en minúsculas
        self.font_type = "normal"  # Atributo para almacenar el tipo de fuente en minúsculas
        self.load_style_config()
        self.load_audio_config()

        #Setear limite de mensajes
        self.Consola.document().setMaximumBlockCount(30)
######################################################################################################################
        # Conectar señales de los campos de entrada de los estilos del texto a funciones
        self.findChild(QtWidgets.QComboBox, "style_msg_box").currentTextChanged.connect(self.update_text_style)
        self.findChild(QtWidgets.QSpinBox, "size_msg_spin").valueChanged.connect(self.update_text_size)
        self.findChild(QtWidgets.QPushButton, "color_msg_btn").clicked.connect(self.select_text_color)
        self.findChild(QtWidgets.QComboBox, "type_font_msg").currentTextChanged.connect(self.update_text_type)
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
        self.findChild(QtWidgets.QSpinBox, "buffer_size").valueChanged.connect(self.update_buffer_size)
############################################################################################################################

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
                        logger.debug(f"Micrófono válido añadido: {name}")
                    #else:
                        logger.debug(f"Micrófono omitido por alta latencia: {name}")
                except Exception as e:
                    logger.debug(f"Error al probar el micrófono ({name}): {e}")

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
        self.play.setIcon(QIcon(".\\ui\\imgs\\play_white.svg"))
        self.pause.setIcon(QIcon(".\\ui\\imgs\\stop_white.svg"))
        self.config.setIcon(QIcon(".\\ui\\imgs\\config_white.svg"))

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
        if not cfg.recording_active:
            logger.debug("Iniciando traducción...")
            cfg.recording_active = True 
            logger.debug(cfg.recording_active) 

            # Obtener el índice del micrófono seleccionado
            microphone_combo_box = self.findChild(QtWidgets.QComboBox, "microphoneComboBox")
            selected_microphone_name = microphone_combo_box.currentText()  # Obtener el nombre seleccionado
            mic_index = self.microphone_mapping.get(selected_microphone_name)  # Obtener el índice real del dispositivo

            try:
                logger.debug(f"Valores pasados: {settings}")
                # Recargar valores desde el JSON
                load_settings()
                # Realizar cálculos dinámicos nuevamente
                calcular_valores_dinamicos()

                # Intentar iniciar la grabación con el micrófono seleccionado
                self.recording_thread = AudioRecordingThread(self.translator, self, mic_index)
                self.recording_thread.start()

                # Actualizar la interfaz
                self.sys_msg("success","Traduccion iniciada, prueba hablar")
                logger.debug(f"Valores nuevos: {settings}")
            except Exception as e:
                logger.debug(f"Error al intentar grabar con el micrófono: {e}")

                # Si ocurre un error, eliminar el dispositivo del QComboBox
                microphone_combo_box = self.findChild(QtWidgets.QComboBox, "microphoneComboBox")
                current_item = microphone_combo_box.currentText()
                logger.debug(f"Error con el micrófono: {current_item}")

                # Eliminar el micrófono problemático de la lista
                microphone_combo_box.removeItem(microphone_combo_box.currentIndex())

                # Mostrar un mensaje al usuario para que seleccione otro dispositivo
                self.sys_msg("error",f"El micrófono '{current_item}' causó un error. Por favor, elige otro.")

                # Establecer recording_active como False para evitar bloqueos
                cfg.recording_active = False
        else:
            logger.debug("La grabación ya está activa.")

    #Frenar Traduccion
    def stop_translation(self):
        stop_recording()  # Detiene la grabación
        logger.debug("Parando traducción...")
        # Reiniciar el estado de las variables
        cfg.recording_active = False  # Asegúrate de que recording_active se establezca en False
        self.sys_msg("info","Traduccion detenida")


########################################################################################################
    def sys_msg(self, message_type, new_text):
        """
        Agrega un mensaje al QTextEdit con un estilo específico.
        :param message_type: Tipo de mensaje ('error', 'info', 'success', 'config').
        :param new_text: Texto del mensaje.
        """
        logger.debug(f"Agregando mensaje de tipo '{message_type}': {new_text}")
        
        if not new_text:
            return

        # Define estilos CSS según el tipo de mensaje
        styles = {
            "error": "color: #ff0000; font-size: 16px ;background-color: transparent; border-radius: 5px; padding: 4px;",
            "info": "color: #00009f; font-size: 16px ;background-color: transparent; border-radius: 5px; padding: 4px;",
            "success": "color: #00ac00; font-size: 16px ;background-color: transparent; border-radius: 5px; padding: 4px;",
            "config": "color: #ff8c00; font-size: 16px ;background-color: transparent; border-radius: 5px; padding: 4px;",
        }

        # Selecciona el estilo según el tipo de mensaje
        style = styles.get(message_type, "color: #000000;")  # Estilo predeterminado (negro)

        # Construye el HTML para el mensaje
        formatted_message = f"""
            <div style="{style}">
                {new_text}
            </div>
        """

        # Agrega el mensaje al QTextEdit
        self.Consola.append(formatted_message)
        self.Consola.append("")

###########################################################################################################

    #Actualizar mensajes
    def update_text_edit(self, new_text):
        if not new_text:
            return

        logger.debug(f"Actualizando texto: {new_text}")

        # Comprobar si el checkbox está marcado para incluir el nombre
        include_name_checkbox = self.findChild(QtWidgets.QCheckBox, "include_name_checkbox")
        if include_name_checkbox and include_name_checkbox.isChecked():
            name_lineedit = self.findChild(QtWidgets.QLineEdit, "name_input")
            # Obtener el texto del QLineEdit
            name = name_lineedit.text().strip() if name_lineedit else ""
            if name:
                # Prependemos el nombre en negrita seguido de dos puntos al mensaje
                new_text = f"<b>{name}:</b> {new_text}"

        # Obtener los valores de configuración
        font_style = self.findChild(QtWidgets.QComboBox, "style_msg_box").currentText()
        font_size = self.findChild(QtWidgets.QSpinBox, "size_msg_spin").value()
        # Suponemos que el botón que define el color tiene un stylesheet del tipo "color: #000000;"
        text_color = self.findChild(QtWidgets.QPushButton, "color_msg_btn").styleSheet().split(":")[-1].strip()
        font_type = self.findChild(QtWidgets.QComboBox, "type_font_msg").currentText()

        # Crear el texto con formato HTML
        styled_text = f"""
            <div style="
                background-color: transparent;
                font-weight: {font_type};
                border-radius: 5px;
                padding: 5px;
                color: {text_color};
                font-family: {font_style};
                font-size: {font_size}px;
                margin-bottom: 10px;">
                {new_text}
            </div>
        """
        
        updated = False
        for message in self.message_list:
            if message['id'] == msg_id:
                message['html'] = styled_text
                updated = True
                break
        if not updated:
            self.message_list.append({'id': msg_id, 'html': styled_text})

        self.render_messages()

    def render_messages(self):
        self.Consola.clear()
        for message in self.message_list:
            self.Consola.insertHtml(message['html'])
            self.Consola.append("")  # Separador
        self.Consola.verticalScrollBar().setValue(self.Consola.verticalScrollBar().maximum())
    
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
                self.findChild(QtWidgets.QDoubleSpinBox, "opacity_bg_console").setValue(config.get("opacity_bg_console", 1.0))
                self.findChild(QtWidgets.QPushButton, "bg_color_console").setStyleSheet(f"background-color: {config.get('bg_color_console', '#464d5f')};")
                self.findChild(QtWidgets.QLineEdit, "name_input").setText(config.get("user_name", ""))

                # Aplicar color de fondo y opacidad al messages_container
                self.apply_consola_style(config)

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
        logger.debug("Guardando configuración...")

        # Guardar configuración de estilos de texto
        self.save_style_config()  # Esta es la función que ya tienes para guardar estilos
        # Guardar configuración de audio
        self.save_audio_config()  # Esta es la función que implementaste para guardar audio

        # Llamar a las funciones de carga para aplicar los cambios inmediatamente
        self.load_style_config()
        self.load_audio_config()

        self.sys_msg("config","Configuracion guardada exitosamente")
    
    #Guardar configuracion de audio
    def save_audio_config(self):
        """Guarda la configuración de audio en el archivo JSON."""
        logger.debug("Guardando configuración de audio...")

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
            "WHISPER_MODEL": self.whisper_model,
            "BUFFER_SIZE": self.findChild(QtWidgets.QSpinBox, "buffer_size").value(),
        }

        # Guardar en el archivo JSON
        with open(self.config_audio_file, 'w') as f:
            json.dump(audio_config, f, indent=4)  # Usar indent=4 para mejorar la legibilidad

        logger.debug("Configuración de audio guardada correctamente.")
        # Opcional: Mostrar un mensaje al usuario
        #Infor MSG para despues
    
    #Guardar configuracion de estilos
    def save_style_config(self):
        logger.debug("Guardando configuración de estilos...")
        """Guarda la configuración en el archivo JSON."""
        config = {
            "font_style": self.findChild(QtWidgets.QComboBox, "style_msg_box").currentText(),
            "font_size": self.findChild(QtWidgets.QSpinBox, "size_msg_spin").value(),
            "font_type": self.font_type,
            "color_msg": self.extract_color(self.findChild(QtWidgets.QPushButton, "color_msg_btn").styleSheet()),  # Obtener el color del texto
            "opacity_bg_console": self.findChild(QtWidgets.QDoubleSpinBox, "opacity_bg_console").value(),
            "color_bg_console": self.extract_color(self.findChild(QtWidgets.QPushButton, "bg_color_console").styleSheet()),  # Obtener el color de fondo de la consola
            "user_name": self.findChild(QtWidgets.QLineEdit, "name_input").text()
        }
        with open(self.config_style_file, 'w') as f:
            json.dump(config, f, indent=4)  # Usar indent=4 para mejorar la legibilidad

#####################################################################################################
    def apply_consola_style(self, config):
        """Aplica el color de fondo y la opacidad al QTextEdit (Consola) usando CSS RGBA."""
        # Obtener configuraciones
        bg_color = config.get("color_bg_console", "#464d5f")  # Color de fondo por defecto
        opacity = config.get("opacity_bg_console", 1.0)         # Opacidad por defecto (valor entre 0 y 1)

        # Convertir el color hexadecimal a QColor para extraer los componentes RGB
        color = QColor(bg_color)
        # Construir la cadena CSS en formato rgba: (r, g, b, alfa) con alfa en 0-1
        rgba_color = f"rgba({color.red()}, {color.green()}, {color.blue()}, {opacity})"

        # Aplicar el estilo al QTextEdit
        self.Consola.setStyleSheet(f"QTextEdit {{ background-color: {rgba_color}; }}")

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
        logger.debug(f"Tasa de muestreo actualizada a: {rate} HZ")  # Mensaje de depuración
    
    def update_chunk_duration(self):
        """Actualiza la duración del chunk basada en el input del usuario."""
        chunk_duration = self.findChild(QtWidgets.QSpinBox, "chunk_duration").value()
        logger.debug(f"Duración del chunk actualizada a: {chunk_duration} ms")  # Mensaje de depuración

    def update_voice_window(self):
        """Actualiza la ventana de voz basada en el input del usuario."""
        voice_window = self.findChild(QtWidgets.QDoubleSpinBox, "voice_window").value()
        logger.debug(f"Ventana de voz actualizada a: {voice_window} seg")  # Mensaje de depuración
    
    def update_min_voice_duration(self):
        """Actualiza la duracion minima de la voz basada en el input del usuario."""
        min_voice_duration = self.findChild(QtWidgets.QDoubleSpinBox, "min_voice_duration").value()
        logger.debug(f"Duración mínima de voz actualizada a: {min_voice_duration} seg")  # Mensaje de depuración

    def update_max_continuous_speech_time(self):
        """Actualiza la ventana de voz basada en el input del usuario."""
        max_continuous_speech_time = self.findChild(QtWidgets.QDoubleSpinBox, "max_continuous_speech_time").value()
        logger.debug(f"Tiempo máximo de habla continua actualizado a: {max_continuous_speech_time} seg")  # Mensaje de depuración

    def update_cut_time(self):
        """Actualiza la ventana de voz basada en el input del usuario."""
        cut_time = self.findChild(QtWidgets.QDoubleSpinBox, "cut_time").value()
        logger.debug(f"Tiempo de corte actualizado a: {cut_time} seg")  # Mensaje de depuración

    def update_threshold(self):
        """Actualiza la ventana de voz basada en el input del usuario."""
        threshold = self.findChild(QtWidgets.QSpinBox, "threshold").value()
        logger.debug(f"Umbral actualizado a: {threshold}")  # Mensaje de depuración

    def update_vad(self):
        """Actualiza la ventana de voz basada en el input del usuario."""
        vad = self.findChild(QtWidgets.QSpinBox, "vad").value()
        logger.debug(f"VAD actualizado a: {vad}")  # Mensaje de depuración
    
    def update_temp_dir(self):
        """Actualiza la ruta temporal basada en el input del usuario."""
        temp_dir = self.findChild(QtWidgets.QLineEdit, "temp_dir").text()
        logger.debug(f"Ruta temporal ingresada: {temp_dir}")  # Mensaje de depuración

        # Validar la ruta solo al perder el foco o al hacer clic en un botón
        if not os.path.exists(temp_dir) and temp_dir != "":
            logger.debug("La ruta temporal no es válida. Por favor, ingresa una ruta existente.")
            self.sys_msg("error","La ruta temporal no es válida. Por favor, ingresa una ruta existente.")
            # Aquí puedes limpiar el campo o establecer un valor predeterminado
            self.findChild(QtWidgets.QLineEdit, "temp_dir").clear()  # Limpiar el campo

    def update_whisper_model(self):
        """Actualiza el modelo Whisper basado en el input del usuario."""
        model = self.findChild(QtWidgets.QComboBox, "whisper_model").currentText()
        logger.debug(f"Modelo Whisper seleccionado: {model}")  # Mensaje de depuración

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
        logger.debug(f"Modelo Whisper en minúsculas: {self.whisper_model}")  # Mensaje de depuración

    def update_buffer_size(self):
        """Actualiza la ventana de voz basada en el input del usuario."""
        buffer_size = self.findChild(QtWidgets.QSpinBox, "buffer_size").value()
        logger.debug(f"Tamaño de buffer actualizado a: {buffer_size}")  # Mensaje de depuración

##################################################################################################################
    #Funciones para tomar correctamente los valores de los inputs de estilos de texto
    def update_text_style(self):
        """Actualiza el estilo de texto basado en el input del usuario."""
        self.current_font_family = self.findChild(QtWidgets.QComboBox, "style_msg_box").currentText()
        logger.debug(f"Estilo de texto actualizado a: {self.current_font_family}")

    def update_text_size(self):
        """Actualiza el tamaño de texto basado en el input del usuario."""
        self.current_font_size = self.findChild(QtWidgets.QSpinBox, "size_msg_spin").value()
        logger.debug(f"Tamaño de texto actualizado a: {self.current_font_size}px")

    def update_text_type(self):
        """Actualiza el peso del texto basado en el input del usuario."""
        self.current_font_weight = self.findChild(QtWidgets.QComboBox, "type_font_msg").currentText().lower()
        logger.debug(f"Peso de texto actualizado a: {self.current_font_weight}")

    def select_text_color(self):
        """Selecciona el color del texto."""
        color = QColorDialog.getColor()
        if color.isValid():
            # Aplicar el color al botón y a las etiquetas
            self.findChild(QtWidgets.QPushButton, "color_msg_btn").setStyleSheet(f"color: {color.name()};")
            logger.debug(f"Color de texto seleccionado: {color.name()}")  # Mensaje de depuración

    def select_background_color_msg(self):
        """Selecciona el color del texto."""
        color = QColorDialog.getColor()
        if color.isValid():
            # Aplicar el color al botón y a las etiquetas
            self.findChild(QtWidgets.QPushButton, "color_bg_msg").setStyleSheet(f"color: {color.name()};")
            logger.debug(f"Color de texto seleccionado: {color.name()}")  # Mensaje de depuración
    
    def update_opacity_bg(self):
        """Actualiza la opacidad del fondo de la consola actualizando la hoja de estilos."""
        # Obtener la opacidad desde el QDoubleSpinBox
        opacity = self.findChild(QtWidgets.QDoubleSpinBox, "opacity_bg_console").value()
        logger.debug(f"Opacidad del fondo de la consola actualizada a: {opacity}")

        # Usar el color actual; si tienes un atributo para ello, por ejemplo self.current_bg_color
        # Si no, usamos un valor por defecto:
        bg_color = getattr(self, "current_bg_color", "#464d5f")
        # Convertir a QColor
        color = QColor(bg_color)
        # Construir la cadena en formato rgba
        rgba_color = f"rgba({color.red()}, {color.green()}, {color.blue()}, {opacity})"

        # Actualizar la hoja de estilos del QTextEdit
        self.Consola.setStyleSheet(f"QTextEdit {{ background-color: {rgba_color}; }}")

    def select_bg_color_console(self):
        """Selecciona el color del fondo de la consola y actualiza la hoja de estilos."""
        color = QColorDialog.getColor()
        if color.isValid():
            # Actualizar el color del botón (opcional)
            self.findChild(QtWidgets.QPushButton, "bg_color_console").setStyleSheet(f"background-color: {color.name()};")
            logger.debug(f"Color de fondo de la consola seleccionado: {color.name()}")
            
            # Guardar el color seleccionado en un atributo
            self.current_bg_color = color.name()
            
            # Obtener la opacidad actual
            opacity = self.findChild(QtWidgets.QDoubleSpinBox, "opacity_bg_console").value()
            
            # Construir la cadena RGBA
            rgba_color = f"rgba({color.red()}, {color.green()}, {color.blue()}, {opacity})"
            
            # Actualizar el estilo del QTextEdit
            self.Consola.setStyleSheet(f"QTextEdit {{ background-color: {rgba_color}; }}")

##################################################################################################################

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # Configura el icono global de la aplicación
    app.setWindowIcon(QtGui.QIcon('.\\ui\\imgs\\icon.ico'))  # Ruta al icono

    window = MainApp()  # Crea la ventana principal
    window.setWindowIcon(QtGui.QIcon('.\\ui\\imgs\\icon.ico'))  # Configura el icono para la ventana
    window.show()

    sys.exit(app.exec_())