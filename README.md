# MicMaster Pro

<div align="center">
  <a href="https://github.com/Mattys03/MicMasterV2/releases/latest">
    <img src="https://img.shields.io/badge/📦_Download_Release-0078D4?style=for-the-badge&logo=github" alt="Download Release" />
  </a>
</div>

![Platform](https://img.shields.io/badge/Platform-Windows-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![License](https://img.shields.io/badge/License-MIT-purple)

A professional audio diagnostic and microphone management tool built in Python. Designed to troubleshoot, analyze, and optimize audio inputs, it provides real-time insights into microphone health, echo analysis, and signal processing.

## 🚀 Features

- **System Audio Diagnosis:** Deep scan of audio inputs, cables, and interfaces to identify hardware or driver issues.
- **Echo Analyzer:** Advanced analysis to detect latency and echo patterns in real-time.
- **Preset Management:** Allows loading, saving, and managing audio equalization/filter presets.
- **Synth Audio Testing:** Built-in synthesizer for generating test tones (beeps) to validate audio pathways.
- **GUI Dashboard:** Clean, intuitive Tkinter-based graphical interface for managing all features without touching the command line.

## 🛠️ Architecture

- **`core/`**: Contains the main audio processing engine (`audio_engine.py`), device managers, and logic handling.
- **`gui/`**: Contains the Tkinter-based user interface components.
- **`presets/`**: JSON configuration files for different microphone setups (e.g., `divine_voice_auto.json`).
- **`_diag.py` / `diagnose_system.py`**: Specialized scripts for diagnosing hardware connectivity and driver states.
- **`main.py`**: Entry point for the application.

## 📦 Installation

1. Clone the repository:
   ```cmd
   git clone https://github.com/yourusername/MicMasterV2.git
   cd MicMasterV2
   ```

2. Run the provided installation batch script to set up the environment:
   ```cmd
   install.bat
   ```

## 🏃‍♂️ Usage

You can start the tool in standard mode or run specific diagnostic tasks.

- **Standard Mode (GUI):**
  ```cmd
  RODAR_MICMASTER.bat
  ```

- **Run Diagnostics:**
  ```cmd
  RODAR_DIAGNOSTICO.bat
  ```

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.
