import wave
import pyaudio
import webrtcvad
import os
import numpy as np

# Configuración básica
RATE = 16000
CHUNK_DURATION_MS = 30
CHUNK = int(RATE * CHUNK_DURATION_MS / 1000)
VOICE_WINDOW = 0.3
MIN_VOICE_DURATION = 0.2

audio = pyaudio.PyAudio()
stream = audio.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
vad = webrtcvad.Vad(2)

def save_temp_audio(frames):
    # Crea una carpeta "temp" dentro del proyecto si no existe
    temp_dir = "./temp"
    os.makedirs(temp_dir, exist_ok=True)

    # Define la ruta completa para el archivo temporal
    temp_file_path = os.path.join(temp_dir, "temp_audio.wav")

    # Guarda el archivo en la carpeta temporal
    with wave.open(temp_file_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    
    return temp_file_path

def is_loud_enough(frame, threshold=500):
    audio_data = np.frombuffer(frame, dtype=np.int16)
    return np.abs(audio_data).mean() > threshold

print("Escuchando... Presiona Ctrl+C para detener.")
try:
    is_speaking = False
    audio_buffer = []
    silence_frames = int(RATE / CHUNK * VOICE_WINDOW)
    silence_counter = 0

    while True:
        frame = stream.read(CHUNK, exception_on_overflow=False)

        try:
            is_voice = vad.is_speech(frame, RATE) or is_loud_enough(frame)
        except webrtcvad.Error as e:
            print(f"Error en VAD: {e}")
            continue

        if is_voice:
            silence_counter = 0
            audio_buffer.append(frame)
            is_speaking = True
        elif is_speaking:
            silence_counter += 1
            if silence_counter > silence_frames:
                if len(audio_buffer) >= int(MIN_VOICE_DURATION * RATE / CHUNK):
                    temp_file = save_temp_audio(audio_buffer)
                    print(f"Segmento guardado en {temp_file}")
                    os.remove(temp_file)  # Elimina el archivo después de procesarlo
                audio_buffer = []
                is_speaking = False
except KeyboardInterrupt:
    print("\nDetenido por el usuario.")
finally:
    stream.stop_stream()
    stream.close()
    audio.terminate()
