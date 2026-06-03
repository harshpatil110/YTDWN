import tkinter as tk
from tkinter import ttk, messagebox
import threading
from core.downloader import Downloader
from core.helpers import get_default_download_path, resource_path
import os

# --- STITCH DESIGN TOKENS ---
COLOR_BG = "#FBF9F4"
COLOR_SURFACE = "#FFFFFF"
COLOR_PRIMARY = "#000000"
COLOR_SECONDARY = "#645D58"
COLOR_ACCENT = "#D5E4F8"
COLOR_BORDER = "#D0C4BE"
COLOR_HOVER = "#F5F3EE"
COLOR_TEXT = "#1B1C19"
COLOR_SUCCESS = "#4ADE80"
COLOR_ERROR = "#BA1A1A"

FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 32, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 14)
FONT_LABEL = (FONT_FAMILY, 10, "bold")
FONT_INPUT = (FONT_FAMILY, 12)
FONT_BUTTON = (FONT_FAMILY, 12, "bold")
FONT_CARD_TITLE = (FONT_FAMILY, 12, "bold")
FONT_CARD_SUBTITLE = (FONT_FAMILY, 10)
FONT_STATUS = (FONT_FAMILY, 10)

class FlatButton(tk.Button):
    def __init__(self, master, **kwargs):
        self.default_bg = kwargs.get("bg", COLOR_PRIMARY)
        self.hover_bg = kwargs.pop("hover_bg", "#333333")
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

class FlatEntry(tk.Frame):
    def __init__(self, master, textvariable):
        super().__init__(master, bg=COLOR_SURFACE, highlightbackground=COLOR_PRIMARY, highlightthickness=2, pady=4, padx=8)
        
        self.entry = tk.Entry(
            self,
            textvariable=textvariable,
            font=FONT_INPUT,
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            insertbackground=COLOR_PRIMARY,
            relief="flat",
            bd=0
        )
        self.entry.pack(fill="both", expand=True, ipady=8, padx=5)

class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=COLOR_SURFACE, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLOR_SURFACE)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

class StitchQualityCard(tk.Frame):
    def __init__(self, master, mode, stream_info, on_select, **kwargs):
        super().__init__(master, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1, cursor="hand2", **kwargs)
        self.mode = mode
        self.stream_info = stream_info
        self.itag = stream_info['itag']
        self.on_select = on_select
        
        self.pack(fill="x", pady=4, padx=4)

        self.bind("<Enter>", self.on_hover)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.select)
        
        title_text = f"{stream_info.get('resolution', stream_info.get('abr'))} | {stream_info['mime_type'].split('/')[1].upper()}"
        subtitle_text = stream_info['filesize_str']
        
        content_frame = tk.Frame(self, bg=COLOR_SURFACE)
        content_frame.pack(fill="x", padx=10, pady=10)
        content_frame.bind("<Button-1>", self.select)
        content_frame.bind("<Enter>", self.on_hover)
        content_frame.bind("<Leave>", self.on_leave)
        self.content_frame = content_frame

        self.lbl_title = tk.Label(content_frame, text=title_text, font=FONT_CARD_TITLE, bg=COLOR_SURFACE, fg=COLOR_TEXT)
        self.lbl_title.pack(side="left")
        self.lbl_title.bind("<Button-1>", self.select)
        self.lbl_title.bind("<Enter>", self.on_hover)
        self.lbl_title.bind("<Leave>", self.on_leave)

        self.lbl_subtitle = tk.Label(content_frame, text=subtitle_text, font=FONT_CARD_SUBTITLE, bg=COLOR_SURFACE, fg=COLOR_SECONDARY)
        self.lbl_subtitle.pack(side="right")
        self.lbl_subtitle.bind("<Button-1>", self.select)
        self.lbl_subtitle.bind("<Enter>", self.on_hover)
        self.lbl_subtitle.bind("<Leave>", self.on_leave)
        
        self.selected = False

    def on_hover(self, e):
        if not self.selected:
            self.config(bg=COLOR_HOVER)
            self.content_frame.config(bg=COLOR_HOVER)
            self.lbl_title.config(bg=COLOR_HOVER)
            self.lbl_subtitle.config(bg=COLOR_HOVER)

    def on_leave(self, e):
        if not self.selected:
            self.config(bg=COLOR_SURFACE)
            self.content_frame.config(bg=COLOR_SURFACE)
            self.lbl_title.config(bg=COLOR_SURFACE)
            self.lbl_subtitle.config(bg=COLOR_SURFACE)

    def select(self, e=None):
        self.on_select(self)

    def set_selected(self, is_selected):
        self.selected = is_selected
        if is_selected:
            self.config(bg=COLOR_ACCENT, highlightbackground=COLOR_PRIMARY, highlightthickness=1)
            self.content_frame.config(bg=COLOR_ACCENT)
            self.lbl_title.config(bg=COLOR_ACCENT)
            self.lbl_subtitle.config(bg=COLOR_ACCENT)
        else:
            self.config(bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1)
            self.content_frame.config(bg=COLOR_SURFACE)
            self.lbl_title.config(bg=COLOR_SURFACE)
            self.lbl_subtitle.config(bg=COLOR_SURFACE)


class YouTubeDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("YTDWN - Professional YouTube Downloader")
        self.geometry("900x800")
        self.configure(bg=COLOR_BG)
        self.minsize(800, 600)

        try:
            icon_path = resource_path("assets/icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        self.downloader = None
        try:
            self.download_path = get_default_download_path()
            self.downloader = Downloader(self.download_path)
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Could not initialize core:\n{e}")

        self.url_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.video_title_var = tk.StringVar(value="Video Information")

        self.selected_mode = None
        self.selected_itag = None
        self.cards = []

        self.configure_styles()
        self.create_widgets()

    def configure_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure(
            "Stitch.Horizontal.TProgressbar",
            troughcolor=COLOR_BORDER,
            background=COLOR_PRIMARY,
            borderwidth=0,
            thickness=8
        )
        style.configure("Vertical.TScrollbar", background=COLOR_SURFACE, troughcolor=COLOR_SURFACE, borderwidth=0, arrowcolor=COLOR_PRIMARY)

    def create_widgets(self):
        self.main_container = tk.Frame(self, bg=COLOR_BG)
        self.main_container.pack(expand=True, fill="both", padx=60, pady=40)

        # 1. Header Section
        header_frame = tk.Frame(self.main_container, bg=COLOR_BG)
        header_frame.pack(fill="x", pady=(0, 30))

        # Arrow down placeholder box
        icon_box = tk.Frame(header_frame, bg=COLOR_BG, highlightbackground=COLOR_PRIMARY, highlightthickness=2, width=50, height=50)
        icon_box.pack(side="top", anchor="center", pady=(0, 10))
        icon_box.pack_propagate(False)
        lbl_icon = tk.Label(icon_box, text="↓", font=("Arial", 20, "bold"), bg=COLOR_BG, fg=COLOR_PRIMARY)
        lbl_icon.pack(expand=True)

        lbl_title = tk.Label(header_frame, text="YTDWN", font=FONT_TITLE, bg=COLOR_BG, fg=COLOR_PRIMARY)
        lbl_title.pack(side="top", anchor="center")

        lbl_subtitle = tk.Label(header_frame, text="Professional YouTube Downloader", font=FONT_SUBTITLE, bg=COLOR_BG, fg=COLOR_SECONDARY)
        lbl_subtitle.pack(side="top", anchor="center")

        # 2. URL Input Panel
        input_panel = tk.Frame(self.main_container, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1)
        input_panel.pack(fill="x", pady=(0, 20))
        
        input_inner = tk.Frame(input_panel, bg=COLOR_SURFACE)
        input_inner.pack(fill="x", padx=30, pady=30)

        lbl_input = tk.Label(input_inner, text="VIDEO URL", font=FONT_LABEL, bg=COLOR_SURFACE, fg=COLOR_SECONDARY)
        lbl_input.pack(anchor="w", pady=(0, 10))

        input_control_frame = tk.Frame(input_inner, bg=COLOR_SURFACE)
        input_control_frame.pack(fill="x")

        self.entry_field = FlatEntry(input_control_frame, textvariable=self.url_var)
        self.entry_field.pack(side="left", fill="x", expand=True)

        self.btn_enter = FlatButton(
            input_control_frame,
            text="ENTER →",
            font=FONT_BUTTON,
            bg=COLOR_PRIMARY,
            fg=COLOR_SURFACE,
            hover_bg="#333333",
            command=self.fetch_streams_thread
        )
        self.btn_enter.pack(side="right", padx=(15, 0), ipady=8, ipadx=20)

        # Container for everything that is hidden initially
        self.results_container = tk.Frame(self.main_container, bg=COLOR_BG)

        # 3. Streams Section (Two-Column Grid)
        self.streams_grid = tk.Frame(self.results_container, bg=COLOR_BG)
        self.streams_grid.pack(fill="both", expand=True, pady=(0, 20))
        self.streams_grid.columnconfigure(0, weight=1)
        self.streams_grid.columnconfigure(1, weight=1)

        # Left Column: Video Details
        details_col = tk.Frame(self.streams_grid, bg=COLOR_BG)
        details_col.grid(row=0, column=0, sticky="nsew", padx=(0, 15))

        self.lbl_video_title = tk.Label(details_col, textvariable=self.video_title_var, font=FONT_TITLE, bg=COLOR_BG, fg=COLOR_PRIMARY, wraplength=400, justify="left", anchor="nw")
        self.lbl_video_title.pack(fill="both", expand=True, pady=(0, 10))

        # Right Column: Qualities
        qualities_col = tk.Frame(self.streams_grid, bg=COLOR_BG)
        qualities_col.grid(row=0, column=1, sticky="nsew", padx=(15, 0))

        # Video Qualities Card
        video_card = tk.Frame(qualities_col, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1)
        video_card.pack(fill="both", expand=True, pady=(0, 15))
        
        lbl_video_q = tk.Label(video_card, text="AVAILABLE VIDEO QUALITIES", font=FONT_LABEL, bg=COLOR_SURFACE, fg=COLOR_SECONDARY)
        lbl_video_q.pack(anchor="w", padx=15, pady=(15, 5))
        
        self.scroll_video = ScrollableFrame(video_card)
        self.scroll_video.pack(fill="both", expand=True, padx=10, pady=(0, 15))

        # Audio Qualities Card
        audio_card = tk.Frame(qualities_col, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1)
        audio_card.pack(fill="both", expand=True)

        lbl_audio_q = tk.Label(audio_card, text="AVAILABLE AUDIO QUALITIES", font=FONT_LABEL, bg=COLOR_SURFACE, fg=COLOR_SECONDARY)
        lbl_audio_q.pack(anchor="w", padx=15, pady=(15, 5))
        
        self.scroll_audio = ScrollableFrame(audio_card)
        self.scroll_audio.pack(fill="both", expand=True, padx=10, pady=(0, 15))

        # 4. Download Action Panel
        action_panel = tk.Frame(self.results_container, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1)
        action_panel.pack(fill="x", pady=(0, 20))
        
        action_inner = tk.Frame(action_panel, bg=COLOR_SURFACE)
        action_inner.pack(fill="x", padx=20, pady=20)

        # Save Destination info
        dest_frame = tk.Frame(action_inner, bg=COLOR_SURFACE)
        dest_frame.pack(side="left")
        
        lbl_dest = tk.Label(dest_frame, text="SAVE DESTINATION", font=FONT_LABEL, bg=COLOR_SURFACE, fg=COLOR_SECONDARY)
        lbl_dest.pack(anchor="w")
        
        path_box = tk.Label(dest_frame, text=self.download_path, font=FONT_STATUS, bg=COLOR_BG, fg=COLOR_PRIMARY, padx=10, pady=5)
        path_box.pack(anchor="w", pady=(5, 0))

        self.btn_download = FlatButton(
            action_inner,
            text="DOWNLOAD",
            font=FONT_BUTTON,
            bg=COLOR_PRIMARY,
            fg=COLOR_SURFACE,
            command=self.start_download_thread
        )
        self.btn_download.pack(side="right", ipady=12, ipadx=30)

        # 5. Status & Progress Section
        self.status_frame = tk.Frame(self.results_container, bg=COLOR_BG)
        self.status_frame.pack(fill="x")

        self.progress_bar = ttk.Progressbar(
            self.status_frame,
            variable=self.progress_var,
            maximum=100,
            style="Stitch.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill="x", pady=(0, 10))

        self.lbl_status = tk.Label(
            self.status_frame,
            textvariable=self.status_var,
            font=FONT_STATUS,
            bg=COLOR_BG,
            fg=COLOR_SECONDARY
        )
        self.lbl_status.pack(anchor="center")

        # Footer
        lbl_footer = tk.Label(
            self,
            text="Powered by FFmpeg",
            font=FONT_STATUS,
            bg=COLOR_BG,
            fg=COLOR_SECONDARY
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

        self.btn_enter.config(state="disabled")
        self.status_var.set("Loading available streams...")
        self.progress_var.set(0)
        self.video_title_var.set("Fetching video information...")
        
        self.results_container.pack(fill="both", expand=True)
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

        self.btn_download.config(state="disabled", text="PROCESSING...")
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
            self.btn_enter.config(state="normal")
            self.status_var.set("Ready to download")
            
            videos = message.get("video", [])
            for v in videos:
                card = StitchQualityCard(self.scroll_video.scrollable_frame, mode="video", stream_info=v, on_select=self.on_card_select)
                self.cards.append(card)
                
            audios = message.get("audio", [])
            for a in audios:
                card = StitchQualityCard(self.scroll_audio.scrollable_frame, mode="mp3", stream_info=a, on_select=self.on_card_select)
                self.cards.append(card)

        elif status_type == "progress":
            self.progress_var.set(progress)
            self.status_var.set(message)
        elif status_type == "info":
            # Extract video title from info if it matches "Found: {title}..."
            if isinstance(message, str) and message.startswith("Found: "):
                title = message.replace("Found: ", "").replace("...", "")
                self.video_title_var.set(title)
            self.status_var.set(message)
        elif status_type == "success":
            self.progress_var.set(100)
            self.status_var.set("Completed successfully")
            messagebox.showinfo("Success", message)
            self.reset_ui()
        elif status_type == "error":
            self.progress_var.set(0)
            self.status_var.set("Error occurred")
            self.btn_enter.config(state="normal")
            messagebox.showerror("Error", message)
            self.reset_ui()

    def reset_ui(self):
        self.btn_download.config(state="normal", text="DOWNLOAD")
        self.entry_field.entry.config(state="normal")
        self.btn_enter.config(state="normal")
        self.status_var.set("Ready")


