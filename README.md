# YTDWN - Premium YouTube Downloader

![Version](https://img.shields.io/badge/version-2.0.0-purple.svg) ![Platform](https://img.shields.io/badge/platform-windows-blue.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg)

**YTDWN** is a professional-grade desktop application for downloading YouTube content in the highest available quality. Built with a modern, dark-themed UI, it offers a seamless user experience for creators, archivists, and power users.

## ✨ Features

- **💎 Modern Dark UI**: A sleek, minimal interface designed for Windows 10/11.
- **🎬 4K/8K Video Support**: Automatically grabs the highest resolution video stream and merges it with the best audio track.
- **🎵 High-Fidelity Audio**: Extracts audio and converts it to crystal-clear MP3 (320kbps equivalent).
- **🚀 Multi-threaded Core**: Downloads run in the background, ensuring the UI remains responsive.
- **🛠 FFmpeg Powered**: Uses industry-standard FFmpeg for robust media processing.
- **📦 Portable Ready**: Can be packaged into a single lightweight `.exe` file.

## 📥 Installation

### Prerequisites
- Python 3.8+
- [FFmpeg](https://ffmpeg.org/download.html) (Must be added to System PATH)

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ytdwn.git
   cd ytdwn
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage

Run the application:
```bash
python main.py
```

1. **Paste URL**: Enter a valid YouTube link.
2. **Select Mode**: Choose between **High Quality Video** or **MP3 Audio**.
3. **Download**: Click the button and watch the progress.
4. **Locate Files**: Content is saved to `C:\Users\<You>\Downloads\YouTube`.

## 📦 Build for Production (EXE)

To create a standalone executable for distribution:

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --icon "assets/icon.ico" --name "YTDWN" --add-data "assets;assets" main.py
```

## 🏗 Tech Stack

- **Frontend**: Python Tkinter (Custom Styling)
- **Backend**: Pytubefix
- **Processing**: FFmpeg
- **Packaging**: PyInstaller

---
*Designed for performance and aesthetics.*
