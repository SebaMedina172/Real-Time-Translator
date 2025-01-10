import threading
import time
from audio_handler import record_audio, stop_recording
from speech_processing import process_audio
from obs_integration import initialize_obs
import config

def main():
    # Inicializa OBS
    obs_manager = initialize_obs(config.HOST, config.PORT, config.PASSWORD)

    print("Escuchando... Presiona Ctrl+C para detener.")
    try:
        # Iniciar hilo de grabación
        recording_thread = threading.Thread(target=record_audio)
        recording_thread.daemon = True
        recording_thread.start()

        # Mantener el programa en ejecución
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        stop_recording()
        obs_manager.disconnect()
        print("\nDetenido por el usuario.")
    finally:
        print("Cerrando el programa.")

if __name__ == "__main__":
    main()
