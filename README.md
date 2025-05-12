# RTT – Real Time Translator

**Real-time audio translator** designed for maximum customization and low resource consumption. Ideal for streaming, gaming, or running in the background on any Windows machine.

---

## 📖 Table of Contents

1. [Introduction](#-introduction)  
2. [Features](#-features)  
3. [Tech Stack](#%EF%B8%8F-tech-stack)  
4. [Installation](#%EF%B8%8F-installation)  
5. [Usage](#-usage)  
6. [Configuration](#-configuration)  
7. [Architecture & Modules](#-architecture--modules)  
8. [Screenshots](#%EF%B8%8F-screenshots)   
9. [License](#-license)

---

## 📝 Introduction

RTT is a desktop application that captures microphone input, transcribes spoken audio with Whisper, and instantly translates it between English and Spanish via MarianMT. Its core goals are:

- **Real-time performance** with minimal latency  
- **High transcription & translation quality**  
- **Extreme customization** to adapt to any speaking style or system specs

---

## ⭐ Features

- **Bidirectional & Automatic Modes**  
  - Unidirectional (EN→ES, ES→EN) or Auto (detect source language and switch accordingly)
- **Translation Configuration**  
  - Silence threshold, voice window, min/max audio duration  
  - Choice of Whisper model for CPU vs. quality trade-off  
- **Text Configuration**  
  - Console typography: font family, size, text & background colours  
- **Intelligent Post-processing**  
  - Detects incomplete sentences (missing punctuation or trailing ellipsis)  
  - Merges fragment candidates and re-translates to ensure coherent output  
- **Lightweight & Background-friendly**  
  - Optimized audio capture loop and circular buffer for low CPU/RAM usage

---

## 🛠️ Tech Stack

- **Language:** Python 3.10  
- **UI:** PyQt5  
- **Speech-to-text:** OpenAI Whisper  
- **Machine Translation:** Hugging Face Transformers (Helsinki-NLP/opus-mt-en-es & opus-mt-es-en)  
- **Packaging:** PyInstaller → `RTT.exe`

---

## ⚙️ Installation

1. Download the latest `app/` folder from the repository.
   
3. Unzip/extract `app/` into any directory on your computer.
   
5. In the resulting folder, you will find:
- `RTT.exe`
- `internals/` folder with the necessary modules and configuration files

4. Run `RTT.exe`.
  
5. Done! The application will start and display the user interface to configure your input device and begin real-time translation.
   
---

## 🚀 Usage
1. Launch **RTT.exe**.

2. In the UI, select your **input device**.

3. Configure your **Translation** & **Text** **settings** (see next section).

4. Click **Start Translation**.

5. Speak into your microphone—translations appear live in the console window.

---

## 🔧 Configuration
### *Translation Settings*


| Option                     | Description                                                                                                                                                                           |
|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Microphone                 | Select from detected system input devices to use for audio capture and translation.                                                                                                   |
| Translation Models         | Choose which Whisper model to use for transcription (e.g. `tiny`, `base`, `small`, `medium`, `large`), balancing speed vs. accuracy.                                                  |
| Translation Direction      | EN → SPA, SPA → EN, or Auto-detect (En ⇔ SPA).                                                                                     |
| Silence Threshold          | dB level below which audio is considered “silent.”                                                                                                                                    |
| Voice Window               | Maximum time (in seconds) that audio can remain below the Silence Threshold before a segment is closed. Low values → more fragments; high values → fewer, larger segments.            |
| Min. Voice Duration        | Minimum continuous speech duration (in seconds) required to start a segment. Low values → possible false positives; high values → may cut off the start of phrases.                   |
| Max. Audio Duration        | Maximum length (in seconds) of a single audio segment before it is forcefully closed. High values can introduce latency or sync errors in real-time translation.                      |
| Context Time               | Amount of previous audio (in seconds) considered when post-processing for coherence. Low values → may omit initial words; high values → may repeat words from earlier segments.       |
| Mic Sensitivity            | Adjustment of input device sensitivity: lower values → more sensitive; higher values → less sensitive.                                                                                |
| Temp Files Path            | Filesystem path where temporary audio files are stored during processing. Not recommended to modify unless you know what you’re doing.                                                |
| Buffer Size                | Size of the audio buffer used internally (in frames). Modifying can destabilize the audio capture loop—leave at default.                                                              |
| Audio Segment Length       | Duration (in milliseconds) of each chunk analyzed per cycle. Changing this (along with sample rate) affects how the system computes its internal RATE parameter—do not alter.         |
| Sample Rate                | Number of audio samples per second. It should remain at the default value to ensure proper operation; changing it may disrupt synchronization and processing.                         |

### *Text Settings*
| Option      | Description                             |
| ----------- | --------------------------------------- |
| Font Family        | Console font (e.g. `Consolas`, `Arial`)         |
| Font Size          | Text size in px                                 |
| Font Type          | Text normal, bold, italic, underline            |
| Text Color         | Hex code or named colour                        |
| label Name         | Name before each translation                    |
| background Opacity | Color opacity fo background                     |
| Background Color   | Hex code or named colour for background console |

---

## 🏗 Architecture & Modules
```text
RTT/
├── Modules/
│   ├── audio_handler.py       # Audio fragmentation & capture
│   ├── speech_processing.py   # Whisper transcription & MarianMT translation
│   ├── postprocessor.py       # Candidate detection & fusion logic
│   ├── load_models.py         # Centralized model loading
│   ├── circular_buffer.py     # Thread-safe audio buffer
│   ├── persistent_loop.py     # Main capture/processing loop
│   └── worker.py              # Thread synchronization utilities
├── Config/
│   ├── audio_config.json          # Persisted audio config
│   └── interface_config.json     # Persisted text config
├── Ui/
│   ├── interfaz.py         # PyQt5 window logic
│   ├── RTT_dock_Edit.ui         # Qt Designer file
│   └── imgs/                # Icons & images
└── RTT.exe                   # Packaged executable (Releases)
```
---

## 🖼️ Screenshots
### English Video
[▶️ Ver video en GitHub](https://github.com/SebaMedina172/Real-Time-Translator/blob/main/Audio_samples/English%20Sample.mp4)

### Spanish Video
[▶️ Reproducir video (raw)](https://raw.githubusercontent.com/SebaMedina172/Real-Time-Translator/main/Audio_samples/Spanish%20Sample.mp4)

---

## 📄 License

© 2025 Medina Sebastian. All rights reserved.

This is a personal project. Unauthorized copying, distribution, or modification is prohibited.
