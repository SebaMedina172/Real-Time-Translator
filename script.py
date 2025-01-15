import threading
import time
from audio_handler import record_audio, stop_recording
from speech_processing import process_audio
import config


def main():

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
        print("\nDetenido por el usuario.")
    finally:
        print("Cerrando el programa.")

if __name__ == "__main__":
    main()
