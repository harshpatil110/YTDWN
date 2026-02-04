# YTDWN - Professional YouTube Downloader

A modern, clean, and efficient YouTube video and audio downloader desktop application.

## Features

- **Highest Quality Video**: Downloads up to 4K/8K (merges video+audio automatically).
- **Highest Quality MP3**: Extracts and converts audio to MP3.
- **Modern UI**: Dark-themed, responsive, and user-friendly interface.
- **Queue System**: Process runs in background without freezing UI.
- **FFmpeg Integration**: Uses FFmpeg for robust media processing.

## Installation

1. Clone or download this repository.
2. Install Python 3.8+.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Ensure **FFmpeg** is installed and added to your system PATH.

## Usage

Run the application:
```bash
python main.py
```

1. Paste a YouTube URL.
2. Select **Video** or **MP3**.
3. Click **DOWNLOAD**.
4. Files are saved to `C:\Users\<YourUser>\Downloads\YouTube`.

## Building for Windows (.exe)

To package the application as a standalone executable:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Run the build command:
   ```bash
   pyinstaller --noconfirm --onefile --windowed --icon "assets/icon.ico" --name "YTDownloader" --add-data "assets;assets" main.py
   ```
   *(Note: Ensure you have an `assets/icon.ico` file, or remove the `--icon` flag if not).*

## Dependencies

- [pytubefix](https://github.com/JuanBindez/pytubefix)
- [FFmpeg](https://ffmpeg.org/) (External Dependency)
