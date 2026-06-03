import tkinter as tk
from tkinter import ttk, messagebox
import threading
from core.downloader import Downloader
from core.helpers import get_default_download_path, resource_path
import os

# --- DESIGN SYSTEM ---
COLOR_BG = "#121212"
COLOR_SURFACE = "#1E1E1E"
COLOR_ACCENT = "#BB86FC"
COLOR_ACCENT_HOVER = "#9F70E0"
COLOR_INPUT_BG = "#2C2C2C"
COLOR_TEXT = "#E0E0E0"
COLOR_TEXT_MUTED = "#888888"
COLOR_BORDER = "#333333"

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
        if self['state'] != 'disabled':
            self["bg"] = self.hover_bg

    def on_leave(self, e):
        if self['state'] != 'disabled':
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
            insertbackground="white",
            relief="flat",
            bd=0
        )
        self.entry.pack(fill="both", expand=True, ipady=8, padx=5)

class YouTubeDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Video Downloader")
        self.geometry("650x800")
        self.configure(bg=COLOR_BG)
        self.resizable(False, False)

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
            messagebox.showerror("Initialization Error", f"Could not initialize core:\n{e}")

        self.url_var = tk.StringVar()
        self.download_mode = tk.StringVar(value="video")
        self.status_var = tk.StringVar(value="Ready to download")
        self.progress_var = tk.DoubleVar(value=0)

        self.video_streams_map = {}
        self.audio_streams_map = {}

        self.configure_styles()
        self.create_widgets()

    def configure_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure(
            "Modern.Horizontal.TProgressbar",
            troughcolor=COLOR_SURFACE,
            background=COLOR_ACCENT,
            borderwidth=0,
            thickness=6
        )

    def create_widgets(self):
        main_container = tk.Frame(self, bg=COLOR_BG)
        main_container.pack(expand=True, fill="both", padx=60, pady=20)

        # 1. Header Section
        header_frame = tk.Frame(main_container, bg=COLOR_BG)
        header_frame.pack(fill="x", pady=(0, 20))

        lbl_title = tk.Label(header_frame, text="YouTube Video Downloader", font=FONT_TITLE, bg=COLOR_BG, fg=COLOR_TEXT)
        lbl_title.pack(side="top", anchor="center")

        lbl_subtitle = tk.Label(header_frame, text="Premium YouTube Downloader", font=(FONT_FAMILY, 10), bg=COLOR_BG, fg=COLOR_TEXT_MUTED)
        lbl_subtitle.pack(side="top", anchor="center", pady=(2, 0))

        # 2. Input Section
        input_frame = tk.Frame(main_container, bg=COLOR_BG)
        input_frame.pack(fill="x", pady=(0, 15))

        lbl_input = tk.Label(input_frame, text="VIDEO URL", font=FONT_SUBTITLE, bg=COLOR_BG, fg=COLOR_TEXT_MUTED)
        lbl_input.pack(anchor="w", pady=(0, 8))

        input_control_frame = tk.Frame(input_frame, bg=COLOR_BG)
        input_control_frame.pack(fill="x")

        self.entry_field = ModernEntry(input_control_frame, textvariable=self.url_var)
        self.entry_field.pack(side="left", fill="x", expand=True)

        self.btn_enter = ModernButton(
            input_control_frame,
            text="ENTER",
            font=FONT_BUTTON,
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            hover_bg=COLOR_BORDER,
            command=self.fetch_streams_thread
        )
        self.btn_enter.pack(side="right", padx=(10, 0), ipady=5, ipadx=10)

        # 3. Streams Section
        streams_frame = tk.Frame(main_container, bg=COLOR_BG)
        streams_frame.pack(fill="x", pady=(0, 20))

        # Video Qualities
        lbl_video = tk.Label(streams_frame, text="Available Video Qualities", font=FONT_SUBTITLE, bg=COLOR_BG, fg=COLOR_TEXT_MUTED)
        lbl_video.pack(anchor="w", pady=(0, 5))

        video_list_frame = tk.Frame(streams_frame, bg=COLOR_INPUT_BG, highlightbackground=COLOR_BORDER, highlightthickness=1)
        video_list_frame.pack(fill="x", pady=(0, 15))

        self.list_video = tk.Listbox(
            video_list_frame, bg=COLOR_INPUT_BG, fg=COLOR_TEXT,
            font=FONT_INPUT, selectbackground=COLOR_ACCENT, selectforeground="#121212",
            relief="flat", bd=0, height=4, highlightthickness=0
        )
        self.list_video.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        scroll_video = tk.Scrollbar(video_list_frame, orient="vertical", command=self.list_video.yview)
        scroll_video.pack(side="right", fill="y")
        self.list_video.config(yscrollcommand=scroll_video.set)

        # Audio Qualities
        lbl_audio = tk.Label(streams_frame, text="Available Audio Qualities", font=FONT_SUBTITLE, bg=COLOR_BG, fg=COLOR_TEXT_MUTED)
        lbl_audio.pack(anchor="w", pady=(0, 5))

        audio_list_frame = tk.Frame(streams_frame, bg=COLOR_INPUT_BG, highlightbackground=COLOR_BORDER, highlightthickness=1)
        audio_list_frame.pack(fill="x")

        self.list_audio = tk.Listbox(
            audio_list_frame, bg=COLOR_INPUT_BG, fg=COLOR_TEXT,
            font=FONT_INPUT, selectbackground=COLOR_ACCENT, selectforeground="#121212",
            relief="flat", bd=0, height=4, highlightthickness=0
        )
        self.list_audio.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        scroll_audio = tk.Scrollbar(audio_list_frame, orient="vertical", command=self.list_audio.yview)
        scroll_audio.pack(side="right", fill="y")
        self.list_audio.config(yscrollcommand=scroll_audio.set)

        # 4. Format Selection
        options_frame = tk.Frame(main_container, bg=COLOR_BG)
        options_frame.pack(fill="x", pady=(0, 20))

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
                selectcolor=COLOR_BG,
                activebackground=COLOR_BG,
                activeforeground=COLOR_ACCENT,
                bd=0,
                indicatoron=1,
                cursor="hand2"
            )

        rb_video = create_radio("High Quality Video", "video")
        rb_video.pack(side="left", padx=20)

        rb_audio = create_radio("High Quality MP3", "mp3")
        rb_audio.pack(side="left", padx=20)

        # 5. Action Button
        self.btn_download = ModernButton(
            main_container,
            text="DOWNLOAD CONTENT",
            font=FONT_BUTTON,
            bg=COLOR_ACCENT,
            fg="#121212",
            hover_bg=COLOR_ACCENT_HOVER,
            command=self.start_download_thread
        )
        self.btn_download.pack(fill="x", pady=(0, 20), ipady=6)

        # 6. Status & Progress Section
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
        lbl_footer.pack(side="bottom", pady=10)

    def fetch_streams_thread(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please paste a valid YouTube URL first.")
            return

        if not self.downloader:
            messagebox.showerror("System Error", "Downloader core failed to initialize.")
            return

        self.btn_enter.config(state="disabled")
        self.status_var.set("Fetching streams...")
        self.progress_var.set(0)

        self.list_video.delete(0, tk.END)
        self.list_audio.delete(0, tk.END)
        self.video_streams_map.clear()
        self.audio_streams_map.clear()

        threading.Thread(target=self.run_fetch_streams, args=(url,), daemon=True).start()

    def run_fetch_streams(self, url):
        def ui_callback(status_type, message, progress):
            self.after(0, lambda: self.handle_callback(status_type, message, progress))
        
        self.downloader.fetch_streams(url, ui_callback)

    def start_download_thread(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please paste a valid YouTube URL first.")
            return

        if not self.downloader:
            messagebox.showerror("System Error", "Downloader core failed to initialize.")
            return

        mode = self.download_mode.get()
        selected_itag = None

        if mode == "video":
            selection = self.list_video.curselection()
            if not selection:
                messagebox.showwarning("Selection Required", "Please select a Video Quality or fetch streams first.")
                return
            selected_itag = self.video_streams_map[selection[0]]
        else:
            selection = self.list_audio.curselection()
            if not selection:
                messagebox.showwarning("Selection Required", "Please select an Audio Quality or fetch streams first.")
                return
            selected_itag = self.audio_streams_map[selection[0]]

        # UI State: Downloading
        self.btn_download.config(state="disabled", text="PROCESSING...", bg=COLOR_SURFACE, fg=COLOR_TEXT_MUTED)
        self.entry_field.entry.config(state="disabled")
        self.btn_enter.config(state="disabled")
        self.list_video.config(state="disabled")
        self.list_audio.config(state="disabled")
        self.status_var.set("Initializing request...")
        self.progress_var.set(0)

        threading.Thread(target=self.run_download, args=(url, mode, selected_itag), daemon=True).start()

    def run_download(self, url, mode, itag):
        def ui_callback(status_type, message, progress):
            self.after(0, lambda: self.handle_callback(status_type, message, progress))

        if mode == "video":
            self.downloader.download_video(url, ui_callback, video_itag=itag)
        else:
            self.downloader.download_mp3(url, ui_callback, audio_itag=itag)

    def handle_callback(self, status_type, message, progress):
        if status_type == "streams_fetched":
            self.btn_enter.config(state="normal")
            self.status_var.set("Streams fetched successfully.")
            
            videos = message.get("video", [])
            for idx, v in enumerate(videos):
                display_text = f"{v['resolution']} - {v['mime_type']} - {v['filesize_str']}"
                self.list_video.insert(tk.END, display_text)
                self.video_streams_map[idx] = v['itag']
                
            audios = message.get("audio", [])
            for idx, a in enumerate(audios):
                display_text = f"{a['abr']} - {a['mime_type']} - {a['filesize_str']}"
                self.list_audio.insert(tk.END, display_text)
                self.audio_streams_map[idx] = a['itag']

        elif status_type == "progress":
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
            self.btn_enter.config(state="normal")
            messagebox.showerror("Error", message)
            self.reset_ui()

    def reset_ui(self):
        self.btn_download.config(state="normal", text="DOWNLOAD CONTENT", bg=COLOR_ACCENT, fg="#121212")
        self.entry_field.entry.config(state="normal")
        self.btn_enter.config(state="normal")
        self.list_video.config(state="normal")
        self.list_audio.config(state="normal")
        self.status_var.set("Ready")

