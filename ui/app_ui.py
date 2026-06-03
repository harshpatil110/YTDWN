import tkinter as tk
from tkinter import ttk, messagebox
import threading
from core.downloader import Downloader
from core.helpers import get_default_download_path, resource_path
import os

# --- DESIGN SYSTEM ---
COLOR_BG = "#0F1117"
COLOR_SURFACE = "#181C24"
COLOR_ACCENT = "#A970FF"
COLOR_ACCENT_HOVER = "#B889FF"
COLOR_INPUT_BG = "#13161C"
COLOR_TEXT = "#FFFFFF"
COLOR_TEXT_MUTED = "#70788C"
COLOR_BORDER = "#2A3140"
COLOR_HOVER = "#1E232E"
COLOR_SELECTED = "#242A38"
COLOR_SUCCESS = "#4ADE80"
COLOR_ERROR = "#F87171"

FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 24, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 10)
FONT_INPUT = (FONT_FAMILY, 12)
FONT_BUTTON = (FONT_FAMILY, 12, "bold")
FONT_CARD_TITLE = (FONT_FAMILY, 14, "bold")
FONT_CARD_SUBTITLE = (FONT_FAMILY, 11)
FONT_STATUS = (FONT_FAMILY, 10)

class ModernButton(tk.Button):
    def __init__(self, master, **kwargs):
        self.default_bg = kwargs.get("bg", COLOR_ACCENT)
        self.hover_bg = kwargs.pop("hover_bg", COLOR_ACCENT_HOVER)
        self.default_fg = kwargs.get("fg", "#FFFFFF")
        
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
    def __init__(self, master, textvariable, placeholder=""):
        super().__init__(master, bg=COLOR_INPUT_BG, highlightbackground=COLOR_BORDER, highlightthickness=1, pady=4, padx=8)
        
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

class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLOR_BG)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Ensure the canvas resizes the inner frame correctly
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Mousewheel binding
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

class QualityCard(tk.Frame):
    def __init__(self, master, mode, stream_info, on_select, **kwargs):
        super().__init__(master, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1, cursor="hand2", **kwargs)
        self.mode = mode
        self.stream_info = stream_info
        self.itag = stream_info['itag']
        self.on_select = on_select
        
        self.pack(fill="x", pady=5, padx=5)

        self.bind("<Enter>", self.on_hover)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.select)
        
        # Details
        title_text = f"{stream_info.get('resolution', stream_info.get('abr'))} {stream_info['mime_type']}"
        subtitle_text = stream_info['filesize_str']
        
        self.lbl_title = tk.Label(self, text=title_text, font=FONT_CARD_TITLE, bg=COLOR_SURFACE, fg=COLOR_TEXT)
        self.lbl_title.pack(anchor="w", padx=15, pady=(15, 2))
        self.lbl_title.bind("<Button-1>", self.select)
        self.lbl_title.bind("<Enter>", self.on_hover)
        self.lbl_title.bind("<Leave>", self.on_leave)

        self.lbl_subtitle = tk.Label(self, text=subtitle_text, font=FONT_CARD_SUBTITLE, bg=COLOR_SURFACE, fg=COLOR_ACCENT)
        self.lbl_subtitle.pack(anchor="w", padx=15, pady=(0, 15))
        self.lbl_subtitle.bind("<Button-1>", self.select)
        self.lbl_subtitle.bind("<Enter>", self.on_hover)
        self.lbl_subtitle.bind("<Leave>", self.on_leave)
        
        self.selected = False

    def on_hover(self, e):
        if not self.selected:
            self.config(bg=COLOR_HOVER)
            self.lbl_title.config(bg=COLOR_HOVER)
            self.lbl_subtitle.config(bg=COLOR_HOVER)

    def on_leave(self, e):
        if not self.selected:
            self.config(bg=COLOR_SURFACE)
            self.lbl_title.config(bg=COLOR_SURFACE)
            self.lbl_subtitle.config(bg=COLOR_SURFACE)

    def select(self, e=None):
        self.on_select(self)

    def set_selected(self, is_selected):
        self.selected = is_selected
        if is_selected:
            self.config(bg=COLOR_SELECTED, highlightbackground=COLOR_ACCENT, highlightthickness=2)
            self.lbl_title.config(bg=COLOR_SELECTED)
            self.lbl_subtitle.config(bg=COLOR_SELECTED)
        else:
            self.config(bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1)
            self.lbl_title.config(bg=COLOR_SURFACE)
            self.lbl_subtitle.config(bg=COLOR_SURFACE)

class YouTubeDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("YTDWN")
        self.geometry("750x850")
        self.configure(bg=COLOR_BG)
        self.minsize(600, 600)

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
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)

        self.selected_mode = None
        self.selected_itag = None
        self.cards = []

        self.configure_styles()
        self.create_widgets()

    def configure_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure(
            "Modern.Horizontal.TProgressbar",
            troughcolor=COLOR_INPUT_BG,
            background=COLOR_ACCENT,
            borderwidth=0,
            thickness=10
        )
        style.configure("Vertical.TScrollbar", background=COLOR_SURFACE, troughcolor=COLOR_BG, borderwidth=0, arrowcolor=COLOR_TEXT)

    def create_widgets(self):
        self.main_container = tk.Frame(self, bg=COLOR_BG)
        self.main_container.pack(expand=True, fill="both", padx=80, pady=40)

        # 1. Header Section
        header_frame = tk.Frame(self.main_container, bg=COLOR_BG)
        header_frame.pack(fill="x", pady=(0, 40))

        lbl_title = tk.Label(header_frame, text="YTDWN", font=FONT_TITLE, bg=COLOR_BG, fg=COLOR_TEXT)
        lbl_title.pack(side="top", anchor="center")

        lbl_subtitle = tk.Label(header_frame, text="Premium YouTube Downloader", font=FONT_SUBTITLE, bg=COLOR_BG, fg=COLOR_TEXT_MUTED)
        lbl_subtitle.pack(side="top", anchor="center", pady=(5, 0))

        # 2. Input Section
        input_frame = tk.Frame(self.main_container, bg=COLOR_BG)
        input_frame.pack(fill="x", pady=(0, 20))

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
            hover_bg=COLOR_ACCENT_HOVER,
            command=self.fetch_streams_thread
        )
        self.btn_enter.pack(side="right", padx=(15, 0), ipady=6, ipadx=15)

        # Container for everything that is hidden initially
        self.results_container = tk.Frame(self.main_container, bg=COLOR_BG)

        # 3. Streams Section
        self.streams_container = tk.Frame(self.results_container, bg=COLOR_BG)
        self.streams_container.pack(fill="both", expand=True, pady=(0, 30))

        # Split into two columns for Video and Audio
        self.streams_grid = tk.Frame(self.streams_container, bg=COLOR_BG)
        self.streams_grid.pack(fill="both", expand=True)
        self.streams_grid.columnconfigure(0, weight=1)
        self.streams_grid.columnconfigure(1, weight=1)

        # Video Qualities
        video_frame = tk.Frame(self.streams_grid, bg=COLOR_BG)
        video_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        lbl_video = tk.Label(video_frame, text="Available Video Qualities", font=FONT_SUBTITLE, bg=COLOR_BG, fg=COLOR_TEXT_MUTED)
        lbl_video.pack(anchor="w", pady=(0, 10))

        self.scroll_video = ScrollableFrame(video_frame)
        self.scroll_video.pack(fill="both", expand=True)

        # Audio Qualities
        audio_frame = tk.Frame(self.streams_grid, bg=COLOR_BG)
        audio_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        lbl_audio = tk.Label(audio_frame, text="Available Audio Qualities", font=FONT_SUBTITLE, bg=COLOR_BG, fg=COLOR_TEXT_MUTED)
        lbl_audio.pack(anchor="w", pady=(0, 10))

        self.scroll_audio = ScrollableFrame(audio_frame)
        self.scroll_audio.pack(fill="both", expand=True)

        # 4. Action Button
        self.btn_download = ModernButton(
            self.results_container,
            text="DOWNLOAD",
            font=FONT_BUTTON,
            bg=COLOR_ACCENT,
            fg="#FFFFFF",
            hover_bg=COLOR_ACCENT_HOVER,
            command=self.start_download_thread
        )
        self.btn_download.pack(fill="x", pady=(0, 20), ipady=12)

        # 5. Status & Progress Section
        self.status_frame = tk.Frame(self.results_container, bg=COLOR_BG)
        self.status_frame.pack(fill="x")

        self.progress_bar = ttk.Progressbar(
            self.status_frame,
            variable=self.progress_var,
            maximum=100,
            style="Modern.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill="x", pady=(0, 15))

        self.lbl_status = tk.Label(
            self.status_frame,
            textvariable=self.status_var,
            font=FONT_STATUS,
            bg=COLOR_BG,
            fg=COLOR_TEXT_MUTED
        )
        self.lbl_status.pack(anchor="center")

        # Footer
        lbl_footer = tk.Label(
            self,
            text="Powered by FFmpeg",
            font=FONT_STATUS,
            bg=COLOR_BG,
            fg=COLOR_BORDER
        )
        lbl_footer.pack(side="bottom", pady=15)

    def clear_cards(self):
        for widget in self.scroll_video.scrollable_frame.winfo_children():
            widget.destroy()
        for widget in self.scroll_audio.scrollable_frame.winfo_children():
            widget.destroy()
        self.cards.clear()
        self.selected_mode = None
        self.selected_itag = None

    def on_card_select(self, clicked_card):
        # Deselect all
        for card in self.cards:
            card.set_selected(False)
        
        # Select clicked
        clicked_card.set_selected(True)
        self.selected_mode = clicked_card.mode
        self.selected_itag = clicked_card.itag

    def fetch_streams_thread(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please paste a valid YouTube URL first.")
            return

        if not self.downloader:
            messagebox.showerror("System Error", "Downloader core failed to initialize.")
            return

        self.btn_enter.config(state="disabled", bg=COLOR_SURFACE, fg=COLOR_TEXT_MUTED)
        self.status_var.set("Loading available streams...")
        self.progress_var.set(0)
        
        self.results_container.pack(fill="both", expand=True) # Reveal the container for status updates
        self.clear_cards()

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

        if not self.selected_mode or not self.selected_itag:
            messagebox.showwarning("Selection Required", "Please select a stream quality to download.")
            return

        # UI State: Downloading
        self.btn_download.config(state="disabled", text="PROCESSING...", bg=COLOR_SURFACE, fg=COLOR_TEXT_MUTED)
        self.entry_field.entry.config(state="disabled")
        self.btn_enter.config(state="disabled")
        self.status_var.set("Initializing request...")
        self.progress_var.set(0)

        threading.Thread(target=self.run_download, args=(url, self.selected_mode, self.selected_itag), daemon=True).start()

    def run_download(self, url, mode, itag):
        def ui_callback(status_type, message, progress):
            self.after(0, lambda: self.handle_callback(status_type, message, progress))

        if mode == "video":
            self.downloader.download_video(url, ui_callback, video_itag=itag)
        else:
            self.downloader.download_mp3(url, ui_callback, audio_itag=itag)

    def handle_callback(self, status_type, message, progress):
        if status_type == "streams_fetched":
            self.btn_enter.config(state="normal", bg=COLOR_SURFACE, fg=COLOR_TEXT)
            self.status_var.set("Ready to download")
            
            videos = message.get("video", [])
            for v in videos:
                card = QualityCard(self.scroll_video.scrollable_frame, mode="video", stream_info=v, on_select=self.on_card_select)
                self.cards.append(card)
                
            audios = message.get("audio", [])
            for a in audios:
                card = QualityCard(self.scroll_audio.scrollable_frame, mode="mp3", stream_info=a, on_select=self.on_card_select)
                self.cards.append(card)

        elif status_type == "progress":
            self.progress_var.set(progress)
            self.status_var.set(message)
        elif status_type == "info":
            self.status_var.set(message)
        elif status_type == "success":
            self.progress_var.set(100)
            self.status_var.set("Completed successfully")
            messagebox.showinfo("Success", message)
            self.reset_ui()
        elif status_type == "error":
            self.progress_var.set(0)
            self.status_var.set("Error occurred")
            self.btn_enter.config(state="normal", bg=COLOR_SURFACE, fg=COLOR_TEXT)
            messagebox.showerror("Error", message)
            self.reset_ui()

    def reset_ui(self):
        self.btn_download.config(state="normal", text="DOWNLOAD", bg=COLOR_ACCENT, fg="#FFFFFF")
        self.entry_field.entry.config(state="normal")
        self.btn_enter.config(state="normal", bg=COLOR_SURFACE, fg=COLOR_TEXT)
        self.status_var.set("Ready")

