import json

class TranslationState:
    def __init__(self, json_data):
        # Inicializar las variables de estado
        self.translatedText = "Texto Default"
        self.recording_active = False
        self.chunk = 0  # Suponiendo que chunk es un número
        self.inputs = json_data  # Cargar inputs desde el JSON (ya pasados al constructor)

    # Método para actualizar los inputs y recalcular variables relacionadas
    def update_inputs(self):
        # Obtener los valores de rate y chunk_duration_ms desde los inputs cargados del JSON
        rate = self.inputs.get("rate", 16000)  # Si no se encuentra, usar 1 por defecto
        chunk_duration_ms = self.inputs.get("chunk_duration_ms", 30)  # Si no se encuentra, usar 1 por defecto

        # Recalcular chunk basado en los valores de rate y chunk_duration_ms
        self.calculate_chunk(rate, chunk_duration_ms)

    # Método para recalcular el valor de 'chunk'
    def calculate_chunk(self, rate, chunk_duration_ms):
        self.chunk = int(rate * chunk_duration_ms / 1000)  # Cálculo para 'chunk'
        print(f"Chunk recalculado: {self.chunk}")

    # Método para actualizar el estado de la traducción
    def update_translated_text(self, translated_text):
        self.translatedText = translated_text
        print(f"Traducción actualizada: {self.translatedText}")

    def update_recording_active(self, is_active):
        self.recording_active = is_active
        print(f"Estado de grabación: {self.recording_active}")

    # Método para obtener solo el valor de recording_active (sin modificarlo)
    def get_recording_active(self):
        return self.recording_active
    
    def get_translated_text(self):
        return self.translatedText

    # Método para obtener el estado actual
    def get_state(self):
        return {
            "translatedText": self.translatedText,
            "recording_active": self.recording_active,
            "chunk": self.chunk
        }

# Simulación de cómo cargar los datos desde el JSON
# Aquí cargamos un ejemplo de JSON para ilustrar cómo cargar los inputs
json_data = {
    "rate": 16000,
    "chunk_duration_ms": 30
}

# # Crear una instancia de TranslationState con los datos del JSON
# state = TranslationState(json_data)

# # Ejemplo de cómo actualizar los inputs y recalcular el 'chunk'
# state.update_inputs()  # Esto usará los datos cargados de rate y chunk_duration_ms del JSON

# print(state.get_translated_text())

# # Ejemplo de cómo actualizar el estado de la traducción
# state.update_translated_text("Hello World")

# print(state.get_translated_text())


# state.update_recording_active(True)

# # Obtener el estado actual
# print(state.get_state())

# # Obtener solo el valor de 'recording_active'
# print(f"Valor de 'recording_active': {state.get_recording_active()}")
