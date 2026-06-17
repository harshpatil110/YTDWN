# 🎬 YTDWN - Premium YouTube Downloader

![Version](https://img.shields.io/badge/version-2.0.0-purple.svg)
![Platform](https://img.shields.io/badge/platform-windows-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Downloads](https://img.shields.io/badge/downloads-latest-brightgreen.svg)

> **Professional-grade desktop application for downloading YouTube content in the highest available quality**

YTDWN combines a sleek, modern interface with powerful downloading capabilities, making it the perfect tool for content creators, archivists, and power users who demand the best quality from YouTube.

## 📸 Screenshots

<p align="center">
  <img src="assets/screenshot.png" alt="YTDWN Interface" width="600">
</p>

## ✨ Key Features

### 🎨 User Experience
- **💎 Modern Dark UI**: Eye-friendly interface designed for Windows 10/11 with custom styling
- **⚡ Responsive Design**: Multi-threaded downloads keep the UI smooth and responsive
- **📊 Real-time Progress**: Visual feedback with progress bars and status updates
- **🎯 Simple Workflow**: Three-step process - paste, select, download

### 🎥 Video Capabilities
- **🎬 4K/8K Support**: Automatically grabs the highest available video resolution
- **🔊 High-Quality Audio**: Merges with the best audio track for perfect synchronization
- **📁 Smart Organization**: Automatic file naming and organization

### 🎵 Audio Features
- **🎧 MP3 Extraction**: Convert videos to crystal-clear MP3 (320kbps equivalent)
- **🎼 Metadata Preservation**: Maintains track information when available
- **📀 Multiple Formats**: Support for various audio formats

### 🛠 Technical Excellence
- **🚀 Multi-threaded Architecture**: Downloads run in background threads
- **🛡️ Error Handling**: Robust error management with user-friendly messages
- **📦 Portable Ready**: Single executable file for easy distribution
- **🔧 FFmpeg Integration**: Industry-standard media processing backend

## 📥 Installation

### System Requirements
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 | Windows 11 |
| Python | 3.8 | 3.10+ |
| RAM | 2GB | 4GB+ |
| Storage | 100MB | 500MB+ |
| Internet | Broadband | High-speed |

### Prerequisites
1. **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
2. **FFmpeg** - [Download FFmpeg](https://ffmpeg.org/download.html)
   - Add FFmpeg to System PATH during installation

### Quick Setup

#### Option 1: From Source
```bash
# Clone the repository
git clone https://github.com/yourusername/ytdwn.git
cd ytdwn

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

#### Option 2: Portable Executable
Download the latest `YTDWN.exe` from the [Releases](https://github.com/yourusername/ytdwn/releases) page and run directly - no installation required!

## 🚀 Usage Guide

### Basic Workflow
1. **Launch YTDWN** - Double-click the executable or run `python main.py`
2. **Paste URL** - Copy and paste any YouTube URL into the input field
3. **Choose Mode** - Select your preferred download type:
   - 🎬 **High Quality Video** - Best available video with optimal audio
   - 🎵 **MP3 Audio** - Extract audio in high-quality MP3 format
4. **Start Download** - Click the download button and watch the progress
5. **Find Your Files** - Content saves to `C:\Users\<Username>\Downloads\YouTube`

### Advanced Tips
- **Multiple Downloads**: Start new downloads while others are processing
- **Cancel Operation**: Use the stop button to cancel ongoing downloads
- **Open Folder**: Quickly access your downloads with the folder button
- **Quality Selection**: The app automatically selects the best available quality

## 🔧 Build Instructions

### Create Standalone Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build single executable
pyinstaller --noconfirm --onefile --windowed `
    --icon "assets/icon.ico" `
    --name "YTDWN" `
    --add-data "assets;assets" `
    --hidden-import "pytubefix" `
    --clean `
    main.py
```

The executable will be created in the `dist` folder.

### Build Configuration Options
- `--onefile`: Single executable file
- `--windowed`: No console window (GUI only)
- `--icon`: Application icon
- `--add-data`: Include assets folder
- `--hidden-import`: Ensure all dependencies are included

## 🏗️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | Python Tkinter | GUI framework with custom styling |
| **Download Engine** | Pytubefix | YouTube video/audio extraction |
| **Media Processing** | FFmpeg | Video/audio conversion and merging |
| **Threading** | Python Threading | Background operations |
| **Packaging** | PyInstaller | Executable creation |

## 📁 Project Structure

```
ytdwn/
├── main.py              # Application entry point
├── downloader.py        # Core download logic
├── ui/                  # GUI components
│   ├── main_window.py   # Main application window
│   └── styles.py        # Custom styling
├── assets/              # Resources
│   ├── icon.ico         # Application icon
│   └── logo.png         # Logo assets
├── requirements.txt     # Python dependencies
└── README.md           # Documentation
```

## ❓ Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **FFmpeg not found** | Ensure FFmpeg is installed and added to System PATH |
| **Download fails** | Check internet connection and URL validity |
| **Video not available** | Some videos may be age-restricted or private |
| **Slow downloads** | YouTube may throttle speeds; try again later |

### Support
- 📧 **Email**: support@ytdwn.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/ytdwn/issues)
- 💬 **Discord**: [Join our community](https://discord.gg/ytdwn)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [pytubefix](https://github.com/JuanBindez/pytubefix) - YouTube download library
- [FFmpeg](https://ffmpeg.org/) - Multimedia framework
- [Tkinter](https://docs.python.org/3/library/tkinter.html) - Python GUI toolkit

## ⚠️ Disclaimer

YTDWN is intended for personal use only. Please respect copyright laws and YouTube's Terms of Service. Only download content you have permission to use.

---

<p align="center">
  Made with ❤️ for the YouTube community
  <br>
  ⭐ Star this repository if you find it useful!
</p>