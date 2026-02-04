import tkinter as tk
from tkinter import ttk, messagebox
import threading
from core.downloader import Downloader
from core.helpers import get_default_download_path, resource_path
import os

# Theme Colors
COLOR_BG = "#121212"
COLOR_SURFACE = "#1E1E1E"
COLOR_PRIMARY = "#BB86FC"
COLOR_SECONDARY = "#03DAC6"
COLOR_TEXT = "#E0E0E0"
COLOR_TEXT_MUTED = "#A0A0A0"
COLOR_ERROR = "#CF6679"

FONT_MAIN = ("Segoe UI", 10)
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_STATUS = ("Consolas", 9)

class YouTubeDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("YTDWN - Professional Downloader")
        self.geometry("600x450")
        self.configure(bg=COLOR_BG)
        self.resizable(False, False)

        # helper for icon
        try:
            icon_path = resource_path("assets/icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        self.downloader = None
        try:
            download_path = get_default_download_path()
            self.downloader = Downloader(download_path)
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Could not initialize downloader:\n{e}")

        # Variables
        self.url_var = tk.StringVar()
        self.download_mode = tk.StringVar(value="video") # video or mp3
        self.status_var = tk.StringVar(value="Ready to download")
        self.progress_var = tk.DoubleVar(value=0)

        self.create_widgets()

    def create_widgets(self):
        # Main Container
        main_frame = tk.Frame(self, bg=COLOR_BG)
        main_frame.pack(expand=True, fill="both", padx=40, pady=30)

        # Header
        lbl_title = tk.Label(
            main_frame, 
            text="YouTube Downloader", 
            font=FONT_TITLE, 
            bg=COLOR_BG, 
            fg=COLOR_PRIMARY
        )
        lbl_title.pack(pady=(0, 20))

        # URL Input
        lbl_url = tk.Label(main_frame, text="Video URL", font=FONT_MAIN, bg=COLOR_BG, fg=COLOR_TEXT)
        lbl_url.pack(anchor="w", pady=(0, 5))

        self.entry_url = tk.Entry(
            main_frame, 
            textvariable=self.url_var, 
            font=FONT_MAIN, 
            bg=COLOR_SURFACE, 
            fg=COLOR_TEXT, 
            insertbackground="white",
            bd=0,
            relief="flat"
        )
        # Add padding inside entry by wrapping or configured padding? Tk entry padding is tricky.
        # We'll stick to simple styling.
        self.entry_url.pack(fill="x", pady=(0, 15), ipady=5)

        # Options (Radio Buttons)
        options_frame = tk.Frame(main_frame, bg=COLOR_BG)
        options_frame.pack(fill="x", pady=(0, 20))

        # Custom styling for radio buttons roughly
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure TConfig for progress bar
        style.configure(
            "Horizontal.TProgressbar", 
            troughcolor=COLOR_SURFACE, 
            background=COLOR_SECONDARY, 
            thickness=10, 
            borderwidth=0
        )

        # Direct tk Radiobuttons allow easier color customization on Windows than ttk
        rb_video = tk.Radiobutton(
            options_frame, 
            text="Highest Quality Video", 
            variable=self.download_mode, 
            value="video",
            font=FONT_MAIN,
            bg=COLOR_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_BG,
            activebackground=COLOR_BG,
            activeforeground=COLOR_PRIMARY
        )
        rb_video.pack(side="left", padx=(0, 20))

        rb_audio = tk.Radiobutton(
            options_frame, 
            text="Highest Quality MP3", 
            variable=self.download_mode, 
            value="mp3",
            font=FONT_MAIN,
            bg=COLOR_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_BG,
            activebackground=COLOR_BG,
            activeforeground=COLOR_PRIMARY
        )
        rb_audio.pack(side="left")

        # Download Button
        self.btn_download = tk.Button(
            main_frame, 
            text="DOWNLOAD", 
            font=("Segoe UI", 11, "bold"), 
            bg=COLOR_PRIMARY, 
            fg=COLOR_BG, # Dark text on bright button
            activebackground="#A370DB",
            activeforeground=COLOR_BG,
            relief="flat",
            cursor="hand2",
            command=self.start_download_thread
        )
        self.btn_download.pack(fill="x", pady=(0, 20), ipady=5)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(
            main_frame, 
            variable=self.progress_var, 
            maximum=100, 
            style="Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill="x", pady=(0, 10))

        # Status Text
        self.lbl_status = tk.Label(
            main_frame, 
            textvariable=self.status_var, 
            font=FONT_STATUS, 
            bg=COLOR_BG, 
            fg=COLOR_TEXT_MUTED,
            wraplength=500,
            justify="center"
        )
        self.lbl_status.pack(fill="x")

        # Footer
        lbl_footer = tk.Label(
            self, 
            text="Powered by FFmpeg & pytubefix", 
            font=("Segoe UI", 8), 
            bg=COLOR_BG, 
            fg="#555555"
        )
        lbl_footer.pack(side="bottom", pady=10)

    def start_download_thread(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a valid YouTube URL")
            return

        if not self.downloader:
            messagebox.showerror("Error", "Downloader core not initialized.")
            return

        # Disable UI
        self.btn_download.config(state="disabled", text="DOWNLOADING...")
        self.entry_url.config(state="disabled")
        self.status_var.set("Initializing...")
        self.progress_var.set(0)

        # Start Thread
        mode = self.download_mode.get()
        threading.Thread(target=self.run_download, args=(url, mode), daemon=True).start()

    def run_download(self, url, mode):
        # This runs in background thread
        # We must use self.after to update UI safely
        
        def ui_callback(status_type, message, progress):
            self.after(0, lambda: self.handle_callback(status_type, message, progress))

        if mode == "video":
            self.downloader.download_video(url, ui_callback)
        else:
            self.downloader.download_mp3(url, ui_callback)

    def handle_callback(self, status_type, message, progress):
        # Runs on main thread
        if status_type == "progress":
            self.progress_var.set(progress)
            self.status_var.set(message)
        elif status_type == "info":
            self.status_var.set(message)
        elif status_type == "success":
            self.progress_var.set(100)
            self.status_var.set("Download Complete! ✅")
            messagebox.showinfo("Success", message)
            self.reset_ui()
        elif status_type == "error":
            self.progress_var.set(0)
            self.status_var.set(f"Error: {message}")
            messagebox.showerror("Download Failed", message)
            self.reset_ui()

    def reset_ui(self):
        self.btn_download.config(state="normal", text="DOWNLOAD")
        self.entry_url.config(state="normal")
