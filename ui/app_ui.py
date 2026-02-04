import tkinter as tk
from tkinter import ttk, messagebox
import threading
from core.downloader import Downloader
from core.helpers import get_default_download_path, resource_path
import os

# --- DESIGN SYSTEM ---
COLOR_BG = "#121212"           # Main Window Background
COLOR_SURFACE = "#1E1E1E"      # Card/Container Background
COLOR_ACCENT = "#BB86FC"       # Primary Action (Soft Purple)
COLOR_ACCENT_HOVER = "#9F70E0" # Slightly darker for hover
COLOR_INPUT_BG = "#2C2C2C"     # Input Field Background
COLOR_TEXT = "#E0E0E0"         # Primary Text
COLOR_TEXT_MUTED = "#888888"   # Secondary Text
COLOR_BORDER = "#333333"       # Subtle Borders

FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 22, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 10, "bold")
FONT_INPUT = (FONT_FAMILY, 11)
FONT_BUTTON = (FONT_FAMILY, 11, "bold")
FONT_STATUS = (FONT_FAMILY, 9)

class ModernButton(tk.Button):
    """Custom flat button with hover effects."""
    def __init__(self, master, **kwargs):
        self.default_bg = kwargs.get("bg", COLOR_ACCENT)
        self.hover_bg = kwargs.pop("hover_bg", COLOR_ACCENT_HOVER)
        self.default_fg = kwargs.get("fg", "#121212")
        
        # Enforce flat premium style
        kwargs.update({
            "relief": "flat",
            "borderwidth": 0,
            "cursor": "hand2",
            "activebackground": self.hover_bg,
            "activeforeground": self.default_fg
        })
        
        super().__init__(master, **kwargs)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self["bg"] = self.hover_bg

    def on_leave(self, e):
        self["bg"] = self.default_bg

class ModernEntry(tk.Frame):
    """A styled entry field with a border and padding."""
    def __init__(self, master, textvariable, placeholder=""):
        super().__init__(master, bg=COLOR_INPUT_BG, highlightbackground=COLOR_BORDER, highlightthickness=1, pady=2, padx=5)
        
        self.entry = tk.Entry(
            self,
            textvariable=textvariable,
            font=FONT_INPUT,
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT,
            insertbackground="white", # Cursor color
            relief="flat",
            bd=0
        )
        self.entry.pack(fill="both", expand=True, ipady=8, padx=5)

class YouTubeDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Video Downloader")
        self.geometry("650x500")
        self.configure(bg=COLOR_BG)
        self.resizable(False, False)

        # Icon setup
        try:
            icon_path = resource_path("assets/icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        # Core Logic initialization
        self.downloader = None
        try:
            download_path = get_default_download_path()
            self.downloader = Downloader(download_path)
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Could not initialize core:\n{e}")

        # State Variables
        self.url_var = tk.StringVar()
        self.download_mode = tk.StringVar(value="video")
        self.status_var = tk.StringVar(value="Ready to download")
        self.progress_var = tk.DoubleVar(value=0)

        # Style configuration for ttk widgets
        self.configure_styles()

        # Build UI
        self.create_widgets()

    def configure_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Custom TProgressbar
        style.configure(
            "Modern.Horizontal.TProgressbar",
            troughcolor=COLOR_SURFACE,
            background=COLOR_ACCENT,
            borderwidth=0,
            thickness=6
        )
        
        # Custom Radiobuttons (using ttk for better styling control if needed, but tk is often easier for dark mode background matching on Windows)
        # We will use tk.Radiobutton for exact color matching.

    def create_widgets(self):
        # --- Main Container (Centered Card) ---
        main_container = tk.Frame(self, bg=COLOR_BG)
        main_container.pack(expand=True, fill="both", padx=60, pady=40)

        # 1. Header Section
        header_frame = tk.Frame(main_container, bg=COLOR_BG)
        header_frame.pack(fill="x", pady=(0, 30))

        lbl_title = tk.Label(
            header_frame, 
            text="YouTube Video Downloader", 
            font=FONT_TITLE, 
            bg=COLOR_BG, 
            fg=COLOR_TEXT
        )
        lbl_title.pack(side="top", anchor="center")

        lbl_subtitle = tk.Label(
            header_frame,
            text="Premium YouTube Downloader",
            font=(FONT_FAMILY, 10),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MUTED
        )
        lbl_subtitle.pack(side="top", anchor="center", pady=(2, 0))

        # 2. Input Section
        input_frame = tk.Frame(main_container, bg=COLOR_BG)
        input_frame.pack(fill="x", pady=(0, 25))

        lbl_input = tk.Label(
            input_frame,
            text="VIDEO URL",
            font=FONT_SUBTITLE,
            bg=COLOR_BG,
            fg=COLOR_TEXT_MUTED
        )
        lbl_input.pack(anchor="w", pady=(0, 8))

        self.entry_field = ModernEntry(input_frame, textvariable=self.url_var)
        self.entry_field.pack(fill="x")

        # 3. Format Selection
        options_frame = tk.Frame(main_container, bg=COLOR_BG)
        options_frame.pack(fill="x", pady=(0, 30))

        # We use a frame to center the radio buttons
        radio_container = tk.Frame(options_frame, bg=COLOR_BG)
        radio_container.pack(anchor="center")

        def create_radio(text, value):
            return tk.Radiobutton(
                radio_container,
                text=text,
                variable=self.download_mode,
                value=value,
                font=(FONT_FAMILY, 10),
                bg=COLOR_BG,
                fg=COLOR_TEXT,
                selectcolor=COLOR_BG,       # Background when selected
                activebackground=COLOR_BG,  # Background when hovering
                activeforeground=COLOR_ACCENT,
                bd=0,
                indicatoron=1, # Standard circle
                cursor="hand2"
            )

        rb_video = create_radio("High Quality Video", "video")
        rb_video.pack(side="left", padx=20)

        rb_audio = create_radio("High Quality MP3", "mp3")
        rb_audio.pack(side="left", padx=20)

        # 4. Action Button
        self.btn_download = ModernButton(
            main_container,
            text="DOWNLOAD CONTENT",
            font=FONT_BUTTON,
            bg=COLOR_ACCENT,
            fg="#121212", # Dark text on bright button
            hover_bg=COLOR_ACCENT_HOVER,
            command=self.start_download_thread
        )
        self.btn_download.pack(fill="x", pady=(0, 25), ipady=6)

        # 5. Status & Progress Section
        status_frame = tk.Frame(main_container, bg=COLOR_BG)
        status_frame.pack(fill="x")

        self.progress_bar = ttk.Progressbar(
            status_frame,
            variable=self.progress_var,
            maximum=100,
            style="Modern.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill="x", pady=(0, 10))

        self.lbl_status = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=FONT_STATUS,
            bg=COLOR_BG,
            fg=COLOR_TEXT_MUTED
        )
        self.lbl_status.pack(anchor="center")

        # Footer
        lbl_footer = tk.Label(
            self,
            text="Powered by FFmpeg • v1.0.0",
            font=FONT_STATUS,
            bg=COLOR_BG,
            fg="#333333"
        )
        lbl_footer.pack(side="bottom", pady=15)

    def start_download_thread(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please paste a valid YouTube URL first.")
            return

        if not self.downloader:
            messagebox.showerror("System Error", "Downloader core failed to initialize.")
            return

        # UI State: Downloading
        self.btn_download.config(state="disabled", text="PROCESSING...", bg=COLOR_SURFACE, fg=COLOR_TEXT_MUTED)
        self.entry_field.entry.config(state="disabled")
        self.status_var.set("Initializing request...")
        self.progress_var.set(0)

        # Start background thread
        mode = self.download_mode.get()
        threading.Thread(target=self.run_download, args=(url, mode), daemon=True).start()

    def run_download(self, url, mode):
        # Bridge to Tkinter main loop using after()
        def ui_callback(status_type, message, progress):
            self.after(0, lambda: self.handle_callback(status_type, message, progress))

        if mode == "video":
            self.downloader.download_video(url, ui_callback)
        else:
            self.downloader.download_mp3(url, ui_callback)

    def handle_callback(self, status_type, message, progress):
        if status_type == "progress":
            self.progress_var.set(progress)
            self.status_var.set(message)
        elif status_type == "info":
            self.status_var.set(message)
        elif status_type == "success":
            self.progress_var.set(100)
            self.status_var.set("Task Complete")
            messagebox.showinfo("Success", message)
            self.reset_ui()
        elif status_type == "error":
            self.progress_var.set(0)
            self.status_var.set("Error occurred")
            messagebox.showerror("Download Failed", message)
            self.reset_ui()

    def reset_ui(self):
        self.btn_download.config(state="normal", text="DOWNLOAD CONTENT", bg=COLOR_ACCENT, fg="#121212")
        self.entry_field.entry.config(state="normal")
        self.status_var.set("Ready to download")
