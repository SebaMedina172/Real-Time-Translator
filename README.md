# RTT – Real Time Translator

**Real-time audio translator** designed for maximum customization and low resource consumption. Ideal for streaming, gaming, or running in the background on any Windows machine.

---

## 📖 Table of Contents

1. [Introduction](#introduction)  
2. [Features](#features)  
3. [Tech Stack](#tech-stack)  
4. [Installation](#-installation)  
5. [Usage](#-usage)  
6. [Configuration](#configuration)  
7. [Architecture & Modules](#architecture--modules)  
8. [Screenshots](#screenshots)  
9. [Contributing](#contributing)  
10. [License](#license)

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

1. **Clone the repo**  
   ```bash
   git clone https://github.com/tu-usuario/RTT.git
   cd RTT
   Download Release

   Go to the Releases page

   Download RTT-Setup.exe
   
---

## 🚀 Usage
1. Launch **RTT.exe**.

2. In the UI, select your **input device**.

3. Configure your **Translation** & **Text** **settings** (see next section).

4. Click **Start Translation**.

5. Speak into your microphone—translations appear live in the console window.

## 🔧 Configuration
### *Translation Settings*

| Option                 | Description                                               |
| ---------------------- | --------------------------------------------------------- |
| Silence Threshold      | Minimum dB level to start detecting speech                |
| Voice Window           | Seconds below threshold to consider speech ended          |
| Min/Max Audio Duration | Bounds for fragment length before forced cut-off          |
| Whisper Model          | Select quality vs. speed (e.g. `small`, `base`, `medium`) |
| Translation Direction  | EN → SPA, SPA → EN or Auto-detect (EN ↔ SPA)                              |

### *Text Settings*
| Option      | Description                             |
| ----------- | --------------------------------------- |
| Font Family | Console font (e.g. `Consolas`, `Arial`) |
| Font Size   | Text size in px                     |
| Font Type   | Text normal, bold, italic, underline              |
| Text Color  | Hex code or named colour                |
| label Name   | Name before each translation                |
| background Opacity   | Color opacity fo background                     |
| Background Color  | Hex code or named colour for background console |

---
## 🏗 Architecture & Modules
RTT/
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
## 🖼️ Screenshots
*I´ve to put some test videos here*

## 📄 License
