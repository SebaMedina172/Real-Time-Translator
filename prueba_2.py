import os
import time
import whisper
import soundfile as sf

# ================================
# CONFIGURACIONES
# ================================
SEGMENTS_DIR = "segments"          # Directorio donde se guardan los segmentos
PROCESSED_DIR = "processed_segments"  # Directorio para mover los segmentos ya procesados
os.makedirs(PROCESSED_DIR, exist_ok=True)
POLL_INTERVAL = 1.0                # Intervalo (en segundos) para revisar nuevos archivos

# Cargar el modelo robusto para transcripción final (por ejemplo, "base")
full_model = whisper.load_model("base")

# ================================
# FUNCIÓN DE TRANSCRIPCIÓN DE UN ARCHIVO
# ================================
def transcribe_file(filepath):
    try:
        audio, sr = sf.read(filepath, dtype='float32')
        if sr != 16000:
            print(f"Advertencia: {filepath} tiene tasa de muestreo {sr} (se espera 16000)")
        result = full_model.transcribe(audio, fp16=False, language="es", task="transcribe")
        text = result["text"].strip()
        return text
    except Exception as e:
        print(f"Error al transcribir {filepath}: {e}")
        return None

# ================================
# FUNCIÓN PRINCIPAL
# ================================
def main():
    print("Monitoreando segmentos en:", SEGMENTS_DIR)
    while True:
        files = [f for f in os.listdir(SEGMENTS_DIR) if f.endswith(".wav")]
        if not files:
            time.sleep(POLL_INTERVAL)
            continue
        for file in files:
            filepath = os.path.join(SEGMENTS_DIR, file)
            print(f"\nProcesando {filepath} ...")
            text = transcribe_file(filepath)
            if text is not None:
                print("\n[Transcripción Completa] " + text)
            # Mover el archivo procesado al directorio de procesados
            new_path = os.path.join(PROCESSED_DIR, file)
            try:
                os.rename(filepath, new_path)
            except Exception as e:
                print(f"No se pudo mover {filepath}: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()