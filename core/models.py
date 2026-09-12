"""
YTDWN Data Models
=================
Data classes for playlist items, download jobs, and results.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List


class PlaylistState(Enum):
    IDLE = 'IDLE'
    LOADING = 'LOADING'
    READY = 'READY'
    DOWNLOADING = 'DOWNLOADING'
    CANCELLING = 'CANCELLING'
    COMPLETED = 'COMPLETED'
    COMPLETED_WITH_ERRORS = 'COMPLETED_WITH_ERRORS'
    CANCELLED = 'CANCELLED'
    FAILED = 'FAILED'


class ItemStatus(Enum):
    PENDING = 'PENDING'
    SELECTED = 'SELECTED'
    SKIPPED = 'SKIPPED'
    DOWNLOADING = 'DOWNLOADING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'
    UNAVAILABLE = 'UNAVAILABLE'


class QualityPolicy(Enum):
    BEST_UP_TO_SELECTED = 'BEST_UP_TO_SELECTED'
    EXACT = 'EXACT'


@dataclass
class PlaylistItem:
    index: int
    video_id: str
    title: str
    url: str
    duration: int = 0
    thumbnail_url: str = ''
    uploader: str = ''
    playlist_index: int = 0
    status: ItemStatus = ItemStatus.SELECTED
    selected: bool = True
    progress: float = 0.0
    filesize: int = 0
    error: str = ''
    output_path: str = ''
    actual_resolution: str = ''
    speed_str: str = ''
    eta_str: str = ''


@dataclass
class PlaylistInfo:
    playlist_id: str = ''
    title: str = ''
    url: str = ''
    uploader: str = ''
    uploader_id: str = ''
    description: str = ''
    thumbnail_url: str = ''
    total_count: int = 0
    items: List[PlaylistItem] = field(default_factory=list)


@dataclass
class DownloadResult:
    success: bool = False
    status: ItemStatus = ItemStatus.PENDING
    video_id: str = ''
    title: str = ''
    output_path: str = ''
    error_code: str = ''
    error_message: str = ''
    actual_resolution: str = ''
    actual_format: str = ''
    duration: int = 0
    filesize: int = 0


@dataclass
class PlaylistSummary:
    playlist_title: str = ''
    total_selected: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    cancelled: int = 0
    output_directory: str = ''
    failed_items: List[PlaylistItem] = field(default_factory=list)


QUALITY_PRESETS = [
    {'label': 'Best Available', 'height': 9999, 'format_expr': 'bestvideo+bestaudio/best'},
    {'label': '2160p (4K)', 'height': 2160, 'format_expr': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]'},
    {'label': '1440p (2K)', 'height': 1440, 'format_expr': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]'},
    {'label': '1080p (Full HD)', 'height': 1080, 'format_expr': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'},
    {'label': '720p (HD)', 'height': 720, 'format_expr': 'bestvideo[height<=720]+bestaudio/best[height<=720]'},
    {'label': '480p', 'height': 480, 'format_expr': 'bestvideo[height<=480]+bestaudio/best[height<=480]'},
    {'label': '360p', 'height': 360, 'format_expr': 'bestvideo[height<=360]+bestaudio/best[height<=360]'},
    {'label': 'Audio Only (Best)', 'height': 0, 'format_expr': 'bestaudio/best', 'audio_only': True},
]
