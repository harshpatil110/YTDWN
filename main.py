import sys
import os
import tkinter as tk
from ui.app_ui import YouTubeDownloaderApp

def main():
    app = YouTubeDownloaderApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    main()
