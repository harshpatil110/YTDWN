import tkinter as tk
from tkinter import ttk, messagebox
import threading
import urllib.request
import io
import os
import datetime
import subprocess
from core.downloader import Downloader
from core.playlist_manager import PlaylistManager, detect_url_type
from core.models import (
    PlaylistState, ItemStatus, QUALITY_PRESETS, PlaylistItem
)
from core.helpers import get_default_download_path, resource_path, setup_logging, format_size

logger = setup_logging()

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

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
COLOR_WARNING = "#E8A317"

FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 24, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 14)
FONT_LABEL = (FONT_FAMILY, 10, "bold")
FONT_INPUT = (FONT_FAMILY, 12)
FONT_BUTTON = (FONT_FAMILY, 12, "bold")
FONT_CARD_TITLE = (FONT_FAMILY, 12, "bold")
FONT_CARD_SUBTITLE = (FONT_FAMILY, 10)
FONT_STATUS = (FONT_FAMILY, 10)
FONT_SMALL = (FONT_FAMILY, 9)


def format_duration(seconds):
    if not seconds:
        return "N/A"
    return str(datetime.timedelta(seconds=int(seconds)))


def format_views(views):
    if not views:
        return "N/A"
    return f"{int(views):,}"


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


class StitchQualityCard(tk.Frame):
    def __init__(self, master, mode, stream_info, on_select, **kwargs):
        super().__init__(master, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1, cursor="hand2", **kwargs)
        self.mode = mode
        self.stream_info = stream_info
        self.itag = stream_info.get('itag')
        self.on_select = on_select

        self.pack(fill="x", pady=4, padx=4)

        self.bind("<Enter>", self.on_hover)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.select)

        if mode == "video":
            title_text = f"{stream_info.get('resolution', 'N/A')} | {stream_info.get('format', 'UNKNOWN')}"
            subtitle_text = f"{stream_info.get('fps', 'N/A')} FPS | {stream_info.get('codec', 'N/A')} | {stream_info.get('filesize_str', 'Unknown')}"
        else:
            title_text = f"{stream_info.get('abr', 'N/A')} | {stream_info.get('format', 'UNKNOWN')}"
            subtitle_text = f"{stream_info.get('codec', 'N/A')} | {stream_info.get('filesize_str', 'Unknown')}"

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


# ─── Playlist Item Row Widget ─────────────────────────────────────────
class PlaylistItemRow(tk.Frame):
    """A single row in the playlist list showing checkbox, index, title, duration, status."""

    def __init__(self, master, item, on_toggle, **kwargs):
        super().__init__(master, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1, **kwargs)
        self.item = item
        self.on_toggle = on_toggle

        inner = tk.Frame(self, bg=COLOR_SURFACE)
        inner.pack(fill="x", padx=10, pady=6)

        # Checkbox
        self.check_var = tk.BooleanVar(value=item.selected)
        self.cb = tk.Checkbutton(
            inner, variable=self.check_var,
            bg=COLOR_SURFACE, activebackground=COLOR_SURFACE,
            command=self._toggle,
            state='normal' if item.status != ItemStatus.COMPLETED else 'disabled'
        )
        self.cb.pack(side="left", padx=(0, 5))

        # Index
        idx_lbl = tk.Label(inner, text=f"{item.playlist_index:02d}", font=FONT_LABEL, bg=COLOR_SURFACE, fg=COLOR_SECONDARY, width=4)
        idx_lbl.pack(side="left", padx=(0, 8))

        # Title + duration frame
        info_frame = tk.Frame(inner, bg=COLOR_SURFACE)
        info_frame.pack(side="left", fill="x", expand=True)

        title_text = item.title if len(item.title) <= 60 else item.title[:57] + "..."
        self.title_lbl = tk.Label(info_frame, text=title_text, font=FONT_CARD_SUBTITLE, bg=COLOR_SURFACE, fg=COLOR_TEXT, anchor="w")
        self.title_lbl.pack(side="left", fill="x", expand=True)

        # Duration
        if item.duration:
            dur_str = format_duration(item.duration)
            dur_lbl = tk.Label(inner, text=dur_str, font=FONT_SMALL, bg=COLOR_SURFACE, fg=COLOR_SECONDARY, width=8)
            dur_lbl.pack(side="right", padx=(8, 0))

        # Status label
        self.status_lbl = tk.Label(inner, text="", font=FONT_SMALL, bg=COLOR_SURFACE, width=14, anchor="e")
        self.status_lbl.pack(side="right", padx=(8, 0))
        self._update_status_display()

    def _toggle(self):
        self.on_toggle(self.item.index, self.check_var.get())

    def _update_status_display(self):
        status = self.item.status
        text = status.value
        color = COLOR_SECONDARY

        if status == ItemStatus.COMPLETED:
            text = "COMPLETED"
            color = "#2E7D32"
            self.check_var.set(False)
            self.cb.config(state='disabled')
        elif status == ItemStatus.DOWNLOADING:
            text = f"DOWNLOADING {self.item.progress:.0f}%"
            color = COLOR_PRIMARY
        elif status == ItemStatus.PROCESSING:
            text = "MERGING..."
            color = COLOR_WARNING
        elif status == ItemStatus.FAILED:
            text = "FAILED"
            color = COLOR_ERROR
        elif status == ItemStatus.CANCELLED:
            text = "CANCELLED"
            color = COLOR_WARNING
        elif status == ItemStatus.SKIPPED:
            text = "SKIPPED"
            color = COLOR_SECONDARY
        elif status == ItemStatus.SELECTED:
            text = "READY"
            color = COLOR_SECONDARY
        elif status == ItemStatus.UNAVAILABLE:
            text = "UNAVAILABLE"
            color = COLOR_ERROR

        self.status_lbl.config(text=text, fg=color)

    def update_item(self, item):
        self.item = item
        self._update_status_display()


class YouTubeDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("YTDWN - Professional YouTube Downloader")
        self.geometry("1000x850")
        self.configure(bg=COLOR_BG)
        self.minsize(900, 700)

        try:
            icon_path = resource_path("assets/icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        self.downloader = None
        self.playlist_manager = None
        try:
            self.download_path = get_default_download_path()
            self.downloader = Downloader(self.download_path)
            self.playlist_manager = PlaylistManager(self.download_path, self.downloader.ffmpeg_path)
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Could not initialize core:\n{e}")

        self.url_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)

        # Metadata Vars
        self.video_title_var = tk.StringVar(value="Video Information")
        self.channel_name_var = tk.StringVar(value="Channel")
        self.duration_var = tk.StringVar(value="00:00")
        self.views_var = tk.StringVar(value="0")
        self.date_var = tk.StringVar(value="N/A")

        self.selected_mode = None  # 'video' or 'mp3'
        self.selected_itag = None
        self.cards = []
        self.thumbnail_image = None

        # App mode: 'single' or 'playlist'
        self.app_mode = 'single'

        # Playlist UI state
        self.playlist_rows = []
        self.playlist_quality_var = tk.StringVar(value=QUALITY_PRESETS[4]['label'])
        self.playlist_continue_on_error = tk.BooleanVar(value=True)

        self.configure_styles()
        self.create_widgets()

        # Graceful shutdown
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        """Handle window close: cancel any running playlist download gracefully."""
        if self.playlist_manager and self.playlist_manager.state == PlaylistState.DOWNLOADING:
            self.playlist_manager.cancel_download()
        self.destroy()

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
        style.configure("Vertical.TScrollbar", background=COLOR_BG, troughcolor=COLOR_BG, borderwidth=0, arrowcolor=COLOR_PRIMARY)

    def _on_canvas_configure(self, event):
        self.main_canvas.itemconfig(self.canvas_window_id, width=event.width)

    def _on_mousewheel(self, event):
        self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def create_widgets(self):
        # Global Scroll Architecture
        self.main_canvas = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0)
        self.main_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.main_canvas.yview, style="Vertical.TScrollbar")

        self.main_container = tk.Frame(self.main_canvas, bg=COLOR_BG)

        self.main_container.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(
                scrollregion=self.main_canvas.bbox("all")
            )
        )

        self.canvas_window_id = self.main_canvas.create_window((0, 0), window=self.main_container, anchor="nw")
        self.main_canvas.bind('<Configure>', self._on_canvas_configure)
        self.bind_all("<MouseWheel>", self._on_mousewheel)

        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.main_scrollbar.pack(side="right", fill="y")
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)

        self.content_wrapper = tk.Frame(self.main_container, bg=COLOR_BG)
        self.content_wrapper.pack(expand=True, fill="both", padx=60, pady=40)

        # 1. Header Section
        header_frame = tk.Frame(self.content_wrapper, bg=COLOR_BG)
        header_frame.pack(fill="x", pady=(0, 20))

        icon_box = tk.Frame(header_frame, bg=COLOR_BG, highlightbackground=COLOR_PRIMARY, highlightthickness=2, width=50, height=50)
        icon_box.pack(side="top", anchor="center", pady=(0, 10))
        icon_box.pack_propagate(False)
        lbl_icon = tk.Label(icon_box, text="\u2193", font=("Arial", 20, "bold"), bg=COLOR_BG, fg=COLOR_PRIMARY)
        lbl_icon.pack(expand=True)

        lbl_title = tk.Label(header_frame, text="YTDWN", font=(FONT_FAMILY, 32, "bold"), bg=COLOR_BG, fg=COLOR_PRIMARY)
        lbl_title.pack(side="top", anchor="center")

        lbl_subtitle = tk.Label(header_frame, text="Professional YouTube Downloader", font=FONT_SUBTITLE, bg=COLOR_BG, fg=COLOR_SECONDARY)
        lbl_subtitle.pack(side="top", anchor="center")

        # ─── Mode Selector ──────────────────────────────────────────
        mode_frame = tk.Frame(self.content_wrapper, bg=COLOR_BG)
        mode_frame.pack(fill="x", pady=(0, 15))

        mode_inner = tk.Frame(mode_frame, bg=COLOR_BG)
        mode_inner.pack(anchor="center")

        self.btn_mode_single = FlatButton(
            mode_inner, text="Single Video", font=FONT_BUTTON,
            bg=COLOR_PRIMARY, fg=COLOR_SURFACE,
            hover_bg="#333333",
            command=lambda: self._set_mode('single')
        )
        self.btn_mode_single.pack(side="left", ipadx=25, ipady=8, padx=(0, 2))

        self.btn_mode_playlist = FlatButton(
            mode_inner, text="Playlist", font=FONT_BUTTON,
            bg=COLOR_SURFACE, fg=COLOR_PRIMARY,
            hover_bg=COLOR_HOVER,
            command=lambda: self._set_mode('playlist')
        )
        self.btn_mode_playlist.pack(side="left", ipadx=25, ipady=8, padx=(2, 0))

        # 2. URL Input Panel
        input_panel = tk.Frame(self.content_wrapper, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1)
        input_panel.pack(fill="x", pady=(0, 20))

        input_inner = tk.Frame(input_panel, bg=COLOR_SURFACE)
        input_inner.pack(fill="x", padx=30, pady=30)

        self.lbl_input_label = tk.Label(input_inner, text="VIDEO URL", font=FONT_LABEL, bg=COLOR_SURFACE, fg=COLOR_SECONDARY)
        self.lbl_input_label.pack(anchor="w", pady=(0, 10))

        input_control_frame = tk.Frame(input_inner, bg=COLOR_SURFACE)
        input_control_frame.pack(fill="x")

        self.entry_field = FlatEntry(input_control_frame, textvariable=self.url_var)
        self.entry_field.pack(side="left", fill="x", expand=True)

        self.btn_enter = FlatButton(
            input_control_frame,
            text="ENTER \u2192",
            font=FONT_BUTTON,
            bg=COLOR_PRIMARY,
            fg=COLOR_SURFACE,
            hover_bg="#333333",
            command=self._on_enter
        )
        self.btn_enter.pack(side="right", padx=(15, 0), ipady=8, ipadx=20)

        # ─── Single Video Results Container ──────────────────────────
        self.results_container = tk.Frame(self.content_wrapper, bg=COLOR_BG)

        # 3. Streams Section (Two-Column Grid)
        self.streams_grid = tk.Frame(self.results_container, bg=COLOR_BG)
        self.streams_grid.pack(fill="both", expand=True, pady=(0, 20))
        self.streams_grid.columnconfigure(0, weight=1, minsize=350)
        self.streams_grid.columnconfigure(1, weight=1, minsize=350)

        # --- LEFT COLUMN: Video Details ---
        details_col = tk.Frame(self.streams_grid, bg=COLOR_BG)
        details_col.grid(row=0, column=0, sticky="nsew", padx=(0, 15))

        self.thumbnail_lbl = tk.Label(details_col, text="Thumbnail Loading...", bg=COLOR_BORDER, fg=COLOR_SECONDARY, font=FONT_LABEL)
        self.thumbnail_lbl.pack(fill="x", pady=(0, 15), ipady=60)

        self.lbl_video_title = tk.Label(details_col, textvariable=self.video_title_var, font=FONT_TITLE, bg=COLOR_BG, fg=COLOR_PRIMARY, wraplength=400, justify="left", anchor="nw")
        self.lbl_video_title.pack(fill="x", pady=(0, 10))

        meta_frame = tk.Frame(details_col, bg=COLOR_BG)
        meta_frame.pack(fill="x")

        channel_lbl = tk.Label(meta_frame, text="Channel", font=FONT_LABEL, bg=COLOR_BG, fg=COLOR_SECONDARY)
        channel_lbl.grid(row=0, column=0, sticky="w", pady=(5, 5))
        tk.Label(meta_frame, textvariable=self.channel_name_var, font=FONT_STATUS, bg=COLOR_BG, fg=COLOR_PRIMARY).grid(row=0, column=1, sticky="w", padx=(10, 0))

        dur_lbl = tk.Label(meta_frame, text="Duration", font=FONT_LABEL, bg=COLOR_BG, fg=COLOR_SECONDARY)
        dur_lbl.grid(row=1, column=0, sticky="w", pady=(5, 5))
        tk.Label(meta_frame, textvariable=self.duration_var, font=FONT_STATUS, bg=COLOR_BG, fg=COLOR_PRIMARY).grid(row=1, column=1, sticky="w", padx=(10, 0))

        date_lbl = tk.Label(meta_frame, text="Upload Date", font=FONT_LABEL, bg=COLOR_BG, fg=COLOR_SECONDARY)
        date_lbl.grid(row=2, column=0, sticky="w", pady=(5, 5))
        tk.Label(meta_frame, textvariable=self.date_var, font=FONT_STATUS, bg=COLOR_BG, fg=COLOR_PRIMARY).grid(row=2, column=1, sticky="w", padx=(10, 0))

        views_lbl = tk.Label(meta_frame, text="View Count", font=FONT_LABEL, bg=COLOR_BG, fg=COLOR_SECONDARY)
        views_lbl.grid(row=3, column=0, sticky="w", pady=(5, 5))
        tk.Label(meta_frame, textvariable=self.views_var, font=FONT_STATUS, bg=COLOR_BG, fg=COLOR_PRIMARY).grid(row=3, column=1, sticky="w", padx=(10, 0))

        # --- RIGHT COLUMN: Qualities ---
        qualities_col = tk.Frame(self.streams_grid, bg=COLOR_BG)
        qualities_col.grid(row=0, column=1, sticky="nsew", padx=(15, 0))

        video_card = tk.Frame(qualities_col, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1)
        video_card.pack(fill="both", expand=True, pady=(0, 15))

        lbl_video_q = tk.Label(video_card, text="AVAILABLE VIDEO QUALITIES", font=FONT_LABEL, bg=COLOR_SURFACE, fg=COLOR_SECONDARY)
        lbl_video_q.pack(anchor="w", padx=15, pady=(15, 5))

        self.video_list_frame = tk.Frame(video_card, bg=COLOR_SURFACE)
        self.video_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 15))

        audio_card = tk.Frame(qualities_col, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1)
        audio_card.pack(fill="both", expand=True)

        lbl_audio_q = tk.Label(audio_card, text="AVAILABLE AUDIO QUALITIES", font=FONT_LABEL, bg=COLOR_SURFACE, fg=COLOR_SECONDARY)
        lbl_audio_q.pack(anchor="w", padx=15, pady=(15, 5))

        self.audio_list_frame = tk.Frame(audio_card, bg=COLOR_SURFACE)
        self.audio_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 15))

        # 4. Download Action Panel (single video)
        action_panel = tk.Frame(self.results_container, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1)
        action_panel.pack(fill="x", pady=(0, 20))

        action_inner = tk.Frame(action_panel, bg=COLOR_SURFACE)
        action_inner.pack(fill="x", padx=20, pady=20)

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

        # 5. Status & Progress Section (single video)
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

        # ─── Playlist Results Container ──────────────────────────────
        self.playlist_container = tk.Frame(self.content_wrapper, bg=COLOR_BG)
        self._build_playlist_ui()

        # Footer
        lbl_footer = tk.Label(
            self.content_wrapper,
            text="Powered by FFmpeg",
            font=FONT_STATUS,
            bg=COLOR_BG,
            fg=COLOR_SECONDARY
        )
        lbl_footer.pack(side="bottom", pady=15)

    # ─── Playlist UI Builder ─────────────────────────────────────────
    def _build_playlist_ui(self):
        """Build all playlist-specific UI widgets inside self.playlist_container."""
        # Playlist metadata section
        self.pl_meta_frame = tk.Frame(self.playlist_container, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1)
        self.pl_meta_frame.pack(fill="x", pady=(0, 15))

        pl_meta_inner = tk.Frame(self.pl_meta_frame, bg=COLOR_SURFACE)
        pl_meta_inner.pack(fill="x", padx=20, pady=15)

        self.pl_title_var = tk.StringVar(value="Playlist Information")
        self.pl_channel_var = tk.StringVar(value="")
        self.pl_count_var = tk.StringVar(value="")
        self.pl_selected_var = tk.StringVar(value="")

        tk.Label(pl_meta_inner, textvariable=self.pl_title_var, font=FONT_TITLE, bg=COLOR_SURFACE, fg=COLOR_PRIMARY, wraplength=800, justify="left", anchor="nw").pack(fill="x", pady=(0, 5))
        tk.Label(pl_meta_inner, textvariable=self.pl_channel_var, font=FONT_SUBTITLE, bg=COLOR_SURFACE, fg=COLOR_SECONDARY).pack(anchor="w")
        tk.Label(pl_meta_inner, textvariable=self.pl_count_var, font=FONT_STATUS, bg=COLOR_SURFACE, fg=COLOR_SECONDARY).pack(anchor="w", pady=(3, 0))
        tk.Label(pl_meta_inner, textvariable=self.pl_selected_var, font=FONT_LABEL, bg=COLOR_SURFACE, fg=COLOR_PRIMARY).pack(anchor="w", pady=(3, 0))

        # Controls: Select All / Deselect All / Quality
        controls_frame = tk.Frame(self.playlist_container, bg=COLOR_BG)
        controls_frame.pack(fill="x", pady=(0, 10))

        left_controls = tk.Frame(controls_frame, bg=COLOR_BG)
        left_controls.pack(side="left")

        FlatButton(left_controls, text="Select All", font=FONT_SMALL, bg=COLOR_SURFACE, fg=COLOR_PRIMARY, hover_bg=COLOR_HOVER, command=self._pl_select_all).pack(side="left", ipadx=10, ipady=4, padx=(0, 5))
        FlatButton(left_controls, text="Deselect All", font=FONT_SMALL, bg=COLOR_SURFACE, fg=COLOR_PRIMARY, hover_bg=COLOR_HOVER, command=self._pl_deselect_all).pack(side="left", ipadx=10, ipady=4, padx=(0, 5))

        right_controls = tk.Frame(controls_frame, bg=COLOR_BG)
        right_controls.pack(side="right")

        tk.Label(right_controls, text="Quality:", font=FONT_LABEL, bg=COLOR_BG, fg=COLOR_SECONDARY).pack(side="left", padx=(0, 5))

        quality_labels = [p['label'] for p in QUALITY_PRESETS]
        self.pl_quality_menu = ttk.Combobox(
            right_controls, textvariable=self.playlist_quality_var,
            values=quality_labels, state="readonly", width=20,
            font=FONT_SMALL
        )
        self.pl_quality_menu.pack(side="left")
        self.pl_quality_menu.current(4)  # Default: 720p
        self.pl_quality_menu.bind("<<ComboboxSelected>>", self._pl_quality_changed)

        # Error policy
        tk.Checkbutton(
            right_controls, text="Continue on error",
            variable=self.playlist_continue_on_error,
            bg=COLOR_BG, activebackground=COLOR_BG,
            font=FONT_SMALL, fg=COLOR_SECONDARY
        ).pack(side="left", padx=(15, 0))

        # Playlist item list (scrollable)
        list_container = tk.Frame(self.playlist_container, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1)
        list_container.pack(fill="both", expand=True, pady=(0, 15))

        list_header = tk.Frame(list_container, bg=COLOR_SURFACE)
        list_header.pack(fill="x", padx=10, pady=(10, 5))
        tk.Label(list_header, text="PLAYLIST VIDEOS", font=FONT_LABEL, bg=COLOR_SURFACE, fg=COLOR_SECONDARY).pack(anchor="w")

        # Scrollable list
        self.pl_list_canvas = tk.Canvas(list_container, bg=COLOR_SURFACE, highlightthickness=0, height=300)
        pl_scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.pl_list_canvas.yview)

        self.pl_list_frame = tk.Frame(self.pl_list_canvas, bg=COLOR_SURFACE)
        self.pl_list_frame.bind("<Configure>", lambda e: self.pl_list_canvas.configure(scrollregion=self.pl_list_canvas.bbox("all")))

        self.pl_list_canvas_win = self.pl_list_canvas.create_window((0, 0), window=self.pl_list_frame, anchor="nw")
        self.pl_list_canvas.bind('<Configure>', lambda e: self.pl_list_canvas.itemconfig(self.pl_list_canvas_win, width=e.width))

        self.pl_list_canvas.pack(side="left", fill="both", expand=True, padx=5)
        pl_scrollbar.pack(side="right", fill="y")
        self.pl_list_canvas.configure(yscrollcommand=pl_scrollbar.set)

        # Bind mousewheel for playlist list
        def _pl_mousewheel(event):
            self.pl_list_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.pl_list_canvas.bind("<MouseWheel>", _pl_mousewheel)
        self.pl_list_frame.bind("<MouseWheel>", _pl_mousewheel)

        # Playlist action panel
        pl_action = tk.Frame(self.playlist_container, bg=COLOR_SURFACE, highlightbackground=COLOR_BORDER, highlightthickness=1)
        pl_action.pack(fill="x", pady=(0, 15))

        pl_action_inner = tk.Frame(pl_action, bg=COLOR_SURFACE)
        pl_action_inner.pack(fill="x", padx=20, pady=15)

        self.pl_dest_lbl = tk.Label(pl_action_inner, text=f"Save to: {self.download_path}", font=FONT_STATUS, bg=COLOR_SURFACE, fg=COLOR_SECONDARY)
        self.pl_dest_lbl.pack(side="left")

        self.btn_pl_download = FlatButton(
            pl_action_inner, text="DOWNLOAD PLAYLIST", font=FONT_BUTTON,
            bg=COLOR_PRIMARY, fg=COLOR_SURFACE,
            command=self._pl_start_download
        )
        self.btn_pl_download.pack(side="right", ipady=10, ipadx=25)

        self.btn_pl_cancel = FlatButton(
            pl_action_inner, text="CANCEL", font=FONT_BUTTON,
            bg=COLOR_ERROR, fg=COLOR_SURFACE, hover_bg="#8B0000",
            command=self._pl_cancel
        )
        # Cancel button hidden initially

        # Playlist progress section
        pl_progress_frame = tk.Frame(self.playlist_container, bg=COLOR_BG)
        pl_progress_frame.pack(fill="x", pady=(0, 10))

        self.pl_progress_var = tk.DoubleVar(value=0)
        self.pl_progress_bar = ttk.Progressbar(
            pl_progress_frame, variable=self.pl_progress_var, maximum=100,
            style="Stitch.Horizontal.TProgressbar"
        )
        self.pl_progress_bar.pack(fill="x", pady=(0, 5))

        self.pl_status_var = tk.StringVar(value="")
        tk.Label(pl_progress_frame, textvariable=self.pl_status_var, font=FONT_STATUS, bg=COLOR_BG, fg=COLOR_SECONDARY).pack(anchor="center")

        # Current video info
        self.pl_current_var = tk.StringVar(value="")
        tk.Label(pl_progress_frame, textvariable=self.pl_current_var, font=FONT_SMALL, bg=COLOR_BG, fg=COLOR_PRIMARY).pack(anchor="center", pady=(3, 0))

        # Stats line
        self.pl_stats_var = tk.StringVar(value="")
        tk.Label(pl_progress_frame, textvariable=self.pl_stats_var, font=FONT_SMALL, bg=COLOR_BG, fg=COLOR_SECONDARY).pack(anchor="center", pady=(3, 0))

        # Post-download buttons
        self.pl_post_frame = tk.Frame(self.playlist_container, bg=COLOR_BG)
        # Built dynamically after completion

    # ─── Mode Switching ─────────────────────────────────────────────
    def _set_mode(self, mode):
        self.app_mode = mode
        # Update button styling
        if mode == 'single':
            self.btn_mode_single.config(bg=COLOR_PRIMARY, fg=COLOR_SURFACE)
            self.btn_mode_single.default_bg = COLOR_PRIMARY
            self.btn_mode_playlist.config(bg=COLOR_SURFACE, fg=COLOR_PRIMARY)
            self.btn_mode_playlist.default_bg = COLOR_SURFACE
            self.lbl_input_label.config(text="VIDEO URL")
            # Show single, hide playlist
            self.playlist_container.pack_forget()
            # Don't show results container unless already populated
        elif mode == 'playlist':
            self.btn_mode_playlist.config(bg=COLOR_PRIMARY, fg=COLOR_SURFACE)
            self.btn_mode_playlist.default_bg = COLOR_PRIMARY
            self.btn_mode_single.config(bg=COLOR_SURFACE, fg=COLOR_PRIMARY)
            self.btn_mode_single.default_bg = COLOR_SURFACE
            self.lbl_input_label.config(text="PLAYLIST URL")
            # Hide single, show playlist if loaded
            self.results_container.pack_forget()

    def _on_enter(self):
        """Handle ENTER button based on current mode."""
        if self.app_mode == 'playlist':
            self._pl_fetch_playlist()
        else:
            self.fetch_streams_thread()

    # ─── Single Video Methods (unchanged) ────────────────────────────
    def clear_cards(self):
        for widget in self.video_list_frame.winfo_children():
            widget.destroy()
        for widget in self.audio_list_frame.winfo_children():
            widget.destroy()
        self.cards.clear()
        self.selected_mode = None
        self.selected_itag = None
        self.thumbnail_lbl.config(image='', text="Thumbnail Loading...")
        self.thumbnail_image = None

    def on_card_select(self, clicked_card):
        for card in self.cards:
            card.set_selected(False)
        clicked_card.set_selected(True)
        self.selected_mode = clicked_card.mode
        self.selected_itag = clicked_card.itag
        logger.info(f"Selected {clicked_card.mode} stream, itag: {clicked_card.itag}")

    def fetch_streams_thread(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please paste a valid YouTube URL first.")
            return

        if not self.downloader:
            messagebox.showerror("System Error", "Downloader core failed to initialize.")
            return

        # Auto-detect: if URL is a playlist and we're in single mode, offer to switch
        url_type = detect_url_type(url)
        if url_type == 'playlist':
            self._set_mode('playlist')
            self._pl_fetch_playlist()
            return
        elif url_type == 'mixed':
            # In single mode, strip playlist parameter
            pass  # continue with single video

        self.btn_enter.config(state="disabled")
        self.status_var.set("Loading available streams...")
        self.progress_var.set(0)
        self.video_title_var.set("Fetching video information...")

        self.playlist_container.pack_forget()
        self.results_container.pack(fill="both", expand=True)
        self.clear_cards()

        threading.Thread(target=self.run_fetch_streams, args=(url,), daemon=True).start()

    def load_thumbnail(self, url):
        try:
            if not HAS_PIL:
                self.thumbnail_lbl.after(0, lambda: self.thumbnail_lbl.config(text="Thumbnail N/A (Requires Pillow)"))
                return

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as u:
                raw_data = u.read()

            image = Image.open(io.BytesIO(raw_data))
            image.thumbnail((400, 300))
            photo = ImageTk.PhotoImage(image)

            self.thumbnail_image = photo
            self.thumbnail_lbl.after(0, lambda: self.thumbnail_lbl.config(image=photo, text=""))
        except Exception as e:
            logger.warning(f"Failed to load thumbnail: {e}")
            self.thumbnail_lbl.after(0, lambda: self.thumbnail_lbl.config(text="Thumbnail Unavailable"))

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

            v_info = message.get("video_info", {})
            self.video_title_var.set(v_info.get("title", "Unknown Title"))
            self.channel_name_var.set(v_info.get("author", "Unknown Author"))
            self.duration_var.set(format_duration(v_info.get("length", 0)))
            self.views_var.set(format_views(v_info.get("views", 0)))
            self.date_var.set(str(v_info.get("publish_date", "N/A")))

            thumb_url = v_info.get("thumbnail_url")
            if thumb_url:
                threading.Thread(target=self.load_thumbnail, args=(thumb_url,), daemon=True).start()
            else:
                self.thumbnail_lbl.config(text="No Thumbnail Provided")

            videos = message.get("video", [])
            for v in videos:
                card = StitchQualityCard(self.video_list_frame, mode="video", stream_info=v, on_select=self.on_card_select)
                self.cards.append(card)

            audios = message.get("audio", [])
            for a in audios:
                card = StitchQualityCard(self.audio_list_frame, mode="mp3", stream_info=a, on_select=self.on_card_select)
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
            self.btn_enter.config(state="normal")
            messagebox.showerror("Error", message)
            self.reset_ui()

    def reset_ui(self):
        self.btn_download.config(state="normal", text="DOWNLOAD")
        self.entry_field.entry.config(state="normal")
        self.btn_enter.config(state="normal")
        self.status_var.set("Ready")

    # ─── Playlist Methods ────────────────────────────────────────────
    def _pl_fetch_playlist(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please paste a valid YouTube playlist URL.")
            return

        if not self.playlist_manager:
            messagebox.showerror("System Error", "Playlist manager failed to initialize.")
            return

        self.btn_enter.config(state="disabled")
        self.pl_status_var.set("Loading playlist...")
        self.pl_progress_var.set(0)

        # Show playlist container
        self.results_container.pack_forget()
        self.playlist_container.pack(fill="both", expand=True)

        # Clear previous playlist rows
        self._pl_clear_rows()

        threading.Thread(target=self._pl_extract_thread, args=(url,), daemon=True).start()

    def _pl_extract_thread(self, url):
        def cb(event, data):
            self.after(0, lambda: self._pl_handle_extract(event, data))
        self.playlist_manager.extract_playlist(url, cb)

    def _pl_handle_extract(self, event, data):
        if event == 'loading':
            self.pl_status_var.set(data.get('message', 'Loading...'))

        elif event == 'loaded':
            self.btn_enter.config(state="normal")
            pi = data['playlist_info']
            already = data.get('already_completed', 0)

            self.pl_title_var.set(pi.title)
            self.pl_channel_var.set(pi.uploader or "Unknown Channel")
            self.pl_count_var.set(f"{pi.total_count} videos")

            if pi.thumbnail_url:
                self.pl_dest_lbl.config(text=f"Save to: {data['output_directory']}")

            # Build playlist item rows
            self._pl_clear_rows()
            for item in pi.items:
                row = PlaylistItemRow(self.pl_list_frame, item, self._pl_toggle_item)
                row.pack(fill="x", padx=5, pady=2)
                self.playlist_rows.append(row)
                # Bind mousewheel on each row
                for child in row.winfo_children():
                    child.bind("<MouseWheel>", lambda e: self.pl_list_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

            self._pl_update_selected_count()

            if already > 0:
                self.pl_status_var.set(f"Loaded. {already} videos already downloaded.")
            else:
                self.pl_status_var.set("Playlist loaded. Select videos and quality, then click Download.")

            # Reset buttons
            self.btn_pl_download.pack(side="right", ipady=10, ipadx=25)
            self.btn_pl_cancel.pack_forget()

        elif event == 'error':
            self.btn_enter.config(state="normal")
            self.pl_status_var.set("Error loading playlist.")
            messagebox.showerror("Playlist Error", data.get('message', 'Unknown error'))

    def _pl_clear_rows(self):
        for row in self.playlist_rows:
            row.destroy()
        self.playlist_rows.clear()

    def _pl_toggle_item(self, index, selected):
        self.playlist_manager.toggle_item(index)
        # Update the item's selected state
        if self.playlist_manager.playlist_info:
            item = self.playlist_manager.playlist_info.items[index]
            item.selected = selected
            if not selected and item.status != ItemStatus.COMPLETED:
                item.status = ItemStatus.SKIPPED
            elif selected and item.status == ItemStatus.SKIPPED:
                item.status = ItemStatus.SELECTED
        self._pl_update_selected_count()
        # Update row display
        if 0 <= index < len(self.playlist_rows):
            self.playlist_rows[index].update_item(self.playlist_manager.playlist_info.items[index])

    def _pl_select_all(self):
        self.playlist_manager.select_all()
        if self.playlist_manager.playlist_info:
            for i, row in enumerate(self.playlist_rows):
                item = self.playlist_manager.playlist_info.items[i]
                row.check_var.set(item.selected)
                row.update_item(item)
        self._pl_update_selected_count()

    def _pl_deselect_all(self):
        self.playlist_manager.deselect_all()
        if self.playlist_manager.playlist_info:
            for i, row in enumerate(self.playlist_rows):
                item = self.playlist_manager.playlist_info.items[i]
                row.check_var.set(item.selected)
                row.update_item(item)
        self._pl_update_selected_count()

    def _pl_update_selected_count(self):
        if self.playlist_manager.playlist_info:
            total = self.playlist_manager.playlist_info.total_count
            selected = self.playlist_manager.get_selected_count()
            completed = self.playlist_manager.get_completed_count()
            text = f"Selected: {selected} / {total}"
            if completed > 0:
                text += f"  |  Already downloaded: {completed}"
            self.pl_selected_var.set(text)

    def _pl_quality_changed(self, event=None):
        idx = self.pl_quality_menu.current()
        self.playlist_manager.set_quality(idx)

    def _pl_start_download(self):
        if not self.playlist_manager or not self.playlist_manager.playlist_info:
            return

        selected = self.playlist_manager.get_selected_count()
        if selected == 0:
            messagebox.showwarning("No Selection", "Please select at least one video to download.")
            return

        # Show cancel button, hide download button
        self.btn_pl_download.pack_forget()
        self.btn_pl_cancel.pack(side="right", ipady=10, ipadx=25)

        # Disable controls
        self.btn_enter.config(state="disabled")
        self.pl_quality_menu.config(state="disabled")
        self.entry_field.entry.config(state="disabled")
        self.btn_mode_single.config(state="disabled")

        # Hide post-download buttons
        for w in self.pl_post_frame.winfo_children():
            w.destroy()
        self.pl_post_frame.pack_forget()

        continue_on_error = self.playlist_continue_on_error.get()

        def cb(event, data):
            self.after(0, lambda: self._pl_handle_download(event, data))

        self.playlist_manager.start_download(cb, continue_on_error)

    def _pl_handle_download(self, event, data):
        if event == 'item_start':
            item = data['item']
            num = data['current_num']
            total = data['total']
            self.pl_current_var.set(f"Downloading: {item.playlist_index:02d} - {item.title[:50]}")
            self.pl_status_var.set(f"Video {num} of {total}")
            # Update row
            self._pl_update_row(item.index)

        elif event == 'item_progress':
            item = data['item']
            pct = data.get('percent', 0)
            speed = data.get('speed', '')
            eta = data.get('eta', '')
            overall = data.get('overall_percent', 0)
            processing = data.get('processing', False)

            self.pl_progress_var.set(overall)

            if processing:
                self.pl_current_var.set(f"Merging: {item.playlist_index:02d} - {item.title[:50]}")
            else:
                info_parts = [f"{pct:.0f}%"]
                if speed:
                    info_parts.append(speed)
                if eta:
                    info_parts.append(f"ETA: {eta}")
                self.pl_current_var.set(
                    f"Downloading: {item.playlist_index:02d} - {item.title[:40]}  |  {' | '.join(info_parts)}"
                )

            # Update row status
            self._pl_update_row(item.index)

        elif event == 'item_complete':
            item = data['item']
            completed = data['completed']
            total = data['total']
            self.pl_stats_var.set(f"Completed: {completed} / {total}")
            self._pl_update_row(item.index)

        elif event == 'item_failed':
            item = data['item']
            self.pl_stats_var.set(f"Failed: {item.playlist_index:02d} - {item.error[:60]}")
            self._pl_update_row(item.index)

        elif event == 'item_skipped':
            item = data['item']
            self._pl_update_row(item.index)

        elif event == 'playlist_progress':
            self.pl_progress_var.set(data.get('percent', 0))
            c = data.get('completed', 0)
            f = data.get('failed', 0)
            s = data.get('skipped', 0)
            t = data.get('total', 0)
            self.pl_stats_var.set(f"Completed: {c}  |  Failed: {f}  |  Skipped: {s}  |  Remaining: {t - c - f - s}")

        elif event == 'playlist_complete':
            summary = data['summary']
            self._pl_show_completion(summary)

        elif event == 'playlist_cancelled':
            summary = data['summary']
            self._pl_show_completion(summary, cancelled=True)

    def _pl_update_row(self, index):
        """Update a single playlist row's display."""
        if self.playlist_manager.playlist_info and 0 <= index < len(self.playlist_rows):
            item = self.playlist_manager.playlist_info.items[index]
            self.playlist_rows[index].update_item(item)

    def _pl_show_completion(self, summary, cancelled=False):
        """Show completion/cancellation summary."""
        # Re-enable controls
        self.btn_enter.config(state="normal")
        self.pl_quality_menu.config(state="readonly")
        self.entry_field.entry.config(state="normal")
        self.btn_mode_single.config(state="normal")

        # Hide cancel, show download
        self.btn_pl_cancel.pack_forget()
        self.btn_pl_download.pack(side="right", ipady=10, ipadx=25)

        self.pl_progress_var.set(100 if not cancelled else 0)

        if cancelled:
            self.pl_status_var.set("Playlist download cancelled.")
        elif summary.failed > 0:
            self.pl_status_var.set("Playlist completed with errors.")
        else:
            self.pl_status_var.set("Playlist download complete!")

        self.pl_current_var.set("")
        self.pl_stats_var.set(
            f"Completed: {summary.completed}  |  Failed: {summary.failed}  |  "
            f"Skipped: {summary.skipped}  |  Cancelled: {summary.cancelled}"
        )

        # Build post-download buttons
        for w in self.pl_post_frame.winfo_children():
            w.destroy()

        btn_frame = tk.Frame(self.pl_post_frame, bg=COLOR_BG)
        btn_frame.pack(anchor="center", pady=10)

        FlatButton(
            btn_frame, text="Open Folder", font=FONT_BUTTON,
            bg=COLOR_SURFACE, fg=COLOR_PRIMARY, hover_bg=COLOR_HOVER,
            command=lambda: self._open_folder(summary.output_directory)
        ).pack(side="left", ipadx=20, ipady=8, padx=5)

        if summary.failed > 0:
            FlatButton(
                btn_frame, text=f"Retry {summary.failed} Failed", font=FONT_BUTTON,
                bg=COLOR_PRIMARY, fg=COLOR_SURFACE,
                command=self._pl_retry_failed
            ).pack(side="left", ipadx=20, ipady=8, padx=5)

        self.pl_post_frame.pack(fill="x", pady=(0, 10))

        # Show summary message
        if not cancelled:
            msg = (
                f"Playlist: {summary.playlist_title}\n\n"
                f"Completed: {summary.completed}\n"
                f"Failed: {summary.failed}\n"
                f"Skipped: {summary.skipped}"
            )
            if summary.failed > 0:
                msg += "\n\nFailed videos:"
                for fi in summary.failed_items[:5]:
                    msg += f"\n  {fi.playlist_index:02d} - {fi.title[:40]}: {fi.error[:40]}"
                if len(summary.failed_items) > 5:
                    msg += f"\n  ... and {len(summary.failed_items) - 5} more"

            messagebox.showinfo("Playlist Download Complete", msg)

    def _pl_cancel(self):
        if self.playlist_manager:
            self.playlist_manager.cancel_download()
            self.pl_status_var.set("Cancelling...")
            self.btn_pl_cancel.config(state="disabled", text="CANCELLING...")

    def _pl_retry_failed(self):
        if not self.playlist_manager:
            return

        # Reset failed items in UI
        if self.playlist_manager.playlist_info:
            for item in self.playlist_manager.playlist_info.items:
                if item.status == ItemStatus.FAILED:
                    item.status = ItemStatus.SELECTED
                    item.selected = True
                    item.progress = 0
                    item.error = ''

            for i, row in enumerate(self.playlist_rows):
                row.update_item(self.playlist_manager.playlist_info.items[i])

        self._pl_update_selected_count()

        # Hide post buttons
        for w in self.pl_post_frame.winfo_children():
            w.destroy()
        self.pl_post_frame.pack_forget()

        # Show cancel, hide download
        self.btn_pl_download.pack_forget()
        self.btn_pl_cancel.pack(side="right", ipady=10, ipadx=25)
        self.btn_pl_cancel.config(state="normal", text="CANCEL")

        # Disable controls
        self.btn_enter.config(state="disabled")
        self.pl_quality_menu.config(state="disabled")
        self.entry_field.entry.config(state="disabled")
        self.btn_mode_single.config(state="disabled")

        continue_on_error = self.playlist_continue_on_error.get()

        def cb(event, data):
            self.after(0, lambda: self._pl_handle_download(event, data))

        self.playlist_manager.retry_failed(cb, continue_on_error)

    def _open_folder(self, path):
        """Open a folder in Windows Explorer."""
        if os.path.isdir(path):
            subprocess.Popen(['explorer', path])
        else:
            subprocess.Popen(['explorer', os.path.dirname(path)])
