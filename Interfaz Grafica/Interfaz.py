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
from PyQt5 import QtWidgets, uic, QtCore, QtGui  # Cambia a PyQt6 si lo estás usando.
from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal, QObject, QThread, QTimer  # Para manejar flags de maximizar/restaurar.
from PyQt5.QtGui import QMouseEvent, QCursor, QIcon, QTextCursor
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QColorDialog, QGraphicsDropShadowEffect
import config
from audio_handler import record_audio, stop_recording
from speech_processing import process_audio


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
        self.config_file = "interface_config.json"  # Asegúrate de que este sea el nombre correcto
        self.load_config()

        # Conectar señales de los campos de entrada a funciones
        self.findChild(QtWidgets.QComboBox, "style_msg_box").currentTextChanged.connect(self.update_text_style)
        self.findChild(QtWidgets.QSpinBox, "size_msg_spin").valueChanged.connect(self.update_text_size)
        self.findChild(QtWidgets.QPushButton, "color_msg_btn").clicked.connect(self.select_text_color)
        self.findChild(QtWidgets.QComboBox, "type_font_msg").currentTextChanged.connect(self.update_text_type)
        self.findChild(QtWidgets.QSpinBox, "stroke_border_msg").valueChanged.connect(self.update_border_thickness)
        self.findChild(QtWidgets.QPushButton, "color_border_msg").clicked.connect(self.select_border_color_msg)
        self.findChild(QtWidgets.QPushButton, "color_bg_msg").clicked.connect(self.select_background_color_msg)
        self.findChild(QtWidgets.QDoubleSpinBox, "opacity_bg_console").valueChanged.connect(self.update_opacity_bg)
        self.findChild(QtWidgets.QPushButton, "bg_color_console").clicked.connect(self.select_bg_color_console)
        

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
                        # valid_microphones.append((i, name))  # Agregar a la lista de micrófonos válidos

                        # Agregar el micrófono al QComboBox con tooltip
                        microphone_combo_box.addItem(name)
                        microphone_combo_box.setItemData(microphone_combo_box.count() - 1, name, Qt.ToolTipRole)
                    else:
                        print(f"Dispositivo omitido por latencia: {name}")

                except Exception as e:
                    print(f"Error al abrir el dispositivo ({name}): {e}")
                    print(f"Detalles del dispositivo: {device_info}")  # Imprimir detalles del dispositivo

        # Agregar los micrófonos válidos al QComboBox
        for index, name in valid_microphones:
            microphone_combo_box.addItem(name)

        p.terminate()  # Terminar PyAudio

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
    
    
    #Cargar la configuracion guardada en el json
    def load_config(self):
        """Carga la configuración desde el archivo JSON."""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
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

    #Guardar Configuracion
    def save_config(self):
        print("Guardando configuración...")
        """Guarda la configuración en el archivo JSON."""
        config = {
            "font_style": self.findChild(QtWidgets.QComboBox, "style_msg_box").currentText(),
            "font_size": self.findChild(QtWidgets.QSpinBox, "size_msg_spin").value(),
            "font_type": self.findChild(QtWidgets.QComboBox, "type_font_msg").currentText(),
            "color_msg": self.extract_color(self.findChild(QtWidgets.QPushButton, "color_msg_btn").styleSheet()),  # Obtener el color del texto
            "stroke_border": self.findChild(QtWidgets.QSpinBox, "stroke_border_msg").value(),
            "color_border_msg": self.extract_color(self.findChild(QtWidgets.QPushButton, "color_border_msg").styleSheet()),  # Obtener el color del borde
            "color_bg_msg": self.extract_color(self.findChild(QtWidgets.QPushButton, "color_bg_msg").styleSheet()),  # Obtener el color de fondo
            "opacity_bg_console": self.findChild(QtWidgets.QDoubleSpinBox, "opacity_bg_console").value(),
            "color_bg_console": self.extract_color(self.findChild(QtWidgets.QPushButton, "bg_color_console").styleSheet()),  # Obtener el color de fondo de la consola
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)  # Usar indent=4 para mejorar la legibilidad
    
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

    #Funciones para tomar correctamente los valores de los inputs
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
        font_weight = "normal"
        if text_type == "Bold":
            font_weight = "bold"
        elif text_type == "Italic":
            font_weight = "italic"
        elif text_type == "Underlined":
            font_weight = "underline"
        
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

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())
