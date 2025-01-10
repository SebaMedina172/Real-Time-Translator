import obsws_python as obs
import config

class OBSManager:
    def __init__(self, host=config.HOST, port=config.PORT, password=config.PASSWORD, scene_name=config.SCENE_NAME, target_source_name=config.TARGET_SOURCE_NAME):
        self.host = host
        self.port = port
        self.password = password
        self.scene_name = scene_name
        self.target_source_name = target_source_name
        self.ws = None

    def connect(self):
        """Establece conexión con el servidor OBS."""
        try:
            self.ws = obs.ReqClient(host=self.host, port=self.port, password=self.password)
            print("Conexión a OBS exitosa.")
        except Exception as e:
            print(f"Error al conectar con OBS: {e}")

    def update_text(self, new_text):
        """Actualiza el texto en una fuente específica."""
        if self.ws is None:
            print("No hay conexión activa con OBS.")
            return
        
        try:
            self.ws.set_input_settings(
                self.target_source_name,
                {"text": new_text},
                overlay=True
            )
            print(f"Texto actualizado en OBS: {new_text}")
        except Exception as e:
            print(f"Error al actualizar texto en OBS: {e}")

    def disconnect(self):
        """Cierra la conexión con el servidor OBS."""
        if self.ws is not None:
            self.ws.disconnect()
            self.ws = None
            print("Conexión con OBS cerrada.")
        else:
            print("No hay conexión activa para cerrar.")
