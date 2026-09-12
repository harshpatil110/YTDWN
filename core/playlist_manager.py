"""
YTDWN Playlist Manager
======================
Handles playlist extraction, download queue, archive, and state persistence.
Uses yt-dlp Python API for all YouTube interactions.
"""

import os
import re
import json
import time
import threading
import yt_dlp
from .helpers import safe_filename, ensure_directory, setup_logging, format_size
from .ffmpeg_utils import get_ffmpeg_path
from .models import (
    PlaylistState, ItemStatus, QualityPolicy,
    PlaylistItem, PlaylistInfo, DownloadResult,
    PlaylistSummary, QUALITY_PRESETS,
)

logger = setup_logging()

# Maximum filename length for Windows (excluding extension)
MAX_FILENAME_LENGTH = 180


def _safe_playlist_folder(title, playlist_id=''):
    """Create a safe Windows folder name from playlist title."""
    if not title:
        title = playlist_id or 'Unknown_Playlist'
    # Remove invalid Windows path characters
    cleaned = re.sub(r'[<>:"/\\|?*]', '', title)
    # Remove leading/trailing dots and spaces
    cleaned = cleaned.strip('. ')
    # Limit length
    if len(cleaned) > MAX_FILENAME_LENGTH:
        cleaned = cleaned[:MAX_FILENAME_LENGTH].rstrip('. ')
    return cleaned or playlist_id or 'Unknown_Playlist'


def _safe_video_filename(playlist_index, title, ext='mp4'):
    """Create a safe Windows filename with playlist index prefix."""
    safe_title = safe_filename(title or 'Unknown')
    # Limit title length to leave room for index prefix and extension
    max_title_len = MAX_FILENAME_LENGTH - 10  # room for "01 - " and ".mp4"
    if len(safe_title) > max_title_len:
        safe_title = safe_title[:max_title_len].rstrip('. ')
    return f"{playlist_index:02d} - {safe_title}.{ext}"


def detect_url_type(url):
    """
    Determine if a URL points to a single video or a playlist.
    Returns: 'video', 'playlist', or 'mixed'
    """
    url = url.strip()
    # Pure playlist URL (no video ID)
    if re.match(r'https?://(www\.)?youtube\.com/playlist\?list=', url):
        return 'playlist'
    # URL with both video ID and playlist
    if re.search(r'[?&]list=', url) and re.search(r'[?&]v=', url):
        return 'mixed'
    if re.search(r'[?&]list=', url) and 'youtu.be/' in url:
        return 'mixed'
    # Single video
    return 'video'


def extract_playlist_id(url):
    """Extract playlist ID from URL."""
    m = re.search(r'[?&]list=([a-zA-Z0-9_-]+)', url)
    return m.group(1) if m else ''


class DownloadArchive:
    """Persistent archive of successfully downloaded video IDs."""

    def __init__(self, archive_dir):
        ensure_directory(archive_dir)
        self.archive_path = os.path.join(archive_dir, 'download_archive.txt')
        self._ids = set()
        self._load()

    def _load(self):
        """Load archived IDs from file."""
        if os.path.exists(self.archive_path):
            try:
                with open(self.archive_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            # yt-dlp format: "youtube VIDEO_ID"
                            parts = line.split()
                            vid = parts[-1] if parts else line
                            self._ids.add(vid)
            except Exception as e:
                logger.warning(f"Could not load archive: {e}")

    def is_archived(self, video_id):
        """Check if a video has been successfully downloaded."""
        return video_id in self._ids

    def mark_completed(self, video_id):
        """Mark a video as successfully downloaded."""
        if video_id not in self._ids:
            self._ids.add(video_id)
            try:
                with open(self.archive_path, 'a', encoding='utf-8') as f:
                    f.write(f"youtube {video_id}\n")
            except Exception as e:
                logger.warning(f"Could not write archive: {e}")

    def count(self):
        return len(self._ids)


class PlaylistState_:
    """Persistent playlist state for resume support."""

    def __init__(self, state_dir, playlist_id):
        ensure_directory(state_dir)
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', playlist_id)
        self.state_path = os.path.join(state_dir, f'playlist_{safe_id}_state.json')
        self.data = {}
        self._load()

    def _load(self):
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load playlist state: {e}")
                self.data = {}

    def save(self):
        try:
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not save playlist state: {e}")

    def get_item_status(self, video_id):
        items = self.data.get('items', {})
        return items.get(video_id, {}).get('status', None)

    def set_item_status(self, video_id, status, error='', output_path=''):
        if 'items' not in self.data:
            self.data['items'] = {}
        self.data['items'][video_id] = {
            'status': status,
            'error': error,
            'output_path': output_path,
            'timestamp': time.time(),
        }
        self.save()


class PlaylistManager:
    """
    Manages playlist extraction, download queue, and execution.
    Uses yt-dlp Python API. Sequential downloads (one at a time).
    """

    def __init__(self, base_download_path, ffmpeg_path=None):
        self.base_download_path = base_download_path
        self.ffmpeg_path = ffmpeg_path or get_ffmpeg_path()
        ensure_directory(base_download_path)

        # Archive directory
        self.archive_dir = os.path.join(base_download_path, '.ytdwn')
        self.archive = DownloadArchive(self.archive_dir)

        # State
        self.playlist_info = None
        self.state = PlaylistState.IDLE
        self.cancel_event = threading.Event()
        self.current_item_index = -1
        self.output_directory = ''

        # Quality
        self.selected_quality = QUALITY_PRESETS[4]  # Default: 720p
        self.quality_policy = QualityPolicy.BEST_UP_TO_SELECTED

        # Playlist state persistence
        self._playlist_state = None

        logger.info("PlaylistManager initialized.")

    def _get_ytdlp_opts(self, extra_opts=None):
        """Build base yt-dlp options."""
        opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
        }
        if self.ffmpeg_path:
            opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg_path)
        if extra_opts:
            opts.update(extra_opts)
        return opts

    def extract_playlist(self, url, callback):
        """
        Extract playlist metadata without downloading media.
        Uses flat extraction for speed on large playlists.
        callback(event, data) where event is one of:
          'loading', 'loaded', 'error'
        """
        try:
            self.state = PlaylistState.LOADING
            callback('loading', {'message': 'Extracting playlist information...'})
            logger.info(f"Extracting playlist: {url}")

            # Flat extraction: fast, only gets basic metadata per item
            opts = self._get_ytdlp_opts({
                'extract_flat': 'in_playlist',
                'skip_download': True,
            })

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if not info:
                raise ValueError("No playlist data returned from yt-dlp.")

            # Determine if this is actually a playlist
            if info.get('_type') != 'playlist' and not info.get('entries'):
                raise ValueError("URL does not point to a playlist.")

            entries = list(info.get('entries', []) or [])
            playlist_id = info.get('id', '') or extract_playlist_id(url)
            playlist_title = info.get('title', '') or f'Playlist {playlist_id}'

            logger.info(f"Playlist: {playlist_title} ({len(entries)} entries)")

            # Build PlaylistInfo
            items = []
            for i, entry in enumerate(entries):
                if not entry:
                    continue
                vid_id = entry.get('id', '') or entry.get('url', '')
                vid_title = entry.get('title', '') or f'Video {i+1}'
                vid_url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else entry.get('url', '')
                vid_duration = entry.get('duration') or 0

                # Check archive for already-downloaded videos
                already_done = self.archive.is_archived(vid_id)

                item = PlaylistItem(
                    index=i,
                    video_id=vid_id,
                    title=vid_title,
                    url=vid_url,
                    duration=int(vid_duration) if vid_duration else 0,
                    thumbnail_url=entry.get('thumbnails', [{}])[0].get('url', '') if entry.get('thumbnails') else '',
                    uploader=entry.get('uploader', '') or entry.get('channel', '') or '',
                    playlist_index=i + 1,
                    status=ItemStatus.COMPLETED if already_done else ItemStatus.SELECTED,
                    selected=not already_done,
                )
                items.append(item)

            self.playlist_info = PlaylistInfo(
                playlist_id=playlist_id,
                title=playlist_title,
                url=url,
                uploader=info.get('uploader', '') or info.get('channel', '') or info.get('uploader_id', '') or '',
                uploader_id=info.get('uploader_id', '') or '',
                description=info.get('description', '') or '',
                thumbnail_url=info.get('thumbnails', [{}])[-1].get('url', '') if info.get('thumbnails') else '',
                total_count=len(items),
                items=items,
            )

            # Setup output directory
            folder_name = _safe_playlist_folder(playlist_title, playlist_id)
            self.output_directory = os.path.join(self.base_download_path, folder_name)
            ensure_directory(self.output_directory)

            # Setup persistent state
            self._playlist_state = PlaylistState_(self.archive_dir, playlist_id)

            self.state = PlaylistState.READY
            logger.info(f"Playlist ready: {len(items)} items, output: {self.output_directory}")

            callback('loaded', {
                'playlist_info': self.playlist_info,
                'output_directory': self.output_directory,
                'already_completed': sum(1 for it in items if it.status == ItemStatus.COMPLETED),
            })

        except Exception as e:
            self.state = PlaylistState.FAILED
            error_msg = str(e)
            logger.error(f"Playlist extraction failed: {error_msg}")
            callback('error', {'message': f"Failed to load playlist: {error_msg}"})

    def get_selected_count(self):
        """Count currently selected (not skipped/completed) items."""
        if not self.playlist_info:
            return 0
        return sum(1 for it in self.playlist_info.items if it.selected and it.status != ItemStatus.COMPLETED)

    def get_completed_count(self):
        if not self.playlist_info:
            return 0
        return sum(1 for it in self.playlist_info.items if it.status == ItemStatus.COMPLETED)

    def set_quality(self, preset_index):
        """Set quality preset by index."""
        if 0 <= preset_index < len(QUALITY_PRESETS):
            self.selected_quality = QUALITY_PRESETS[preset_index]
            logger.info(f"Quality set to: {self.selected_quality['label']}")

    def toggle_item(self, index):
        """Toggle selection for a single item."""
        if self.playlist_info and 0 <= index < len(self.playlist_info.items):
            item = self.playlist_info.items[index]
            if item.status != ItemStatus.COMPLETED:
                item.selected = not item.selected
                item.status = ItemStatus.SELECTED if item.selected else ItemStatus.SKIPPED

    def select_all(self):
        if self.playlist_info:
            for item in self.playlist_info.items:
                if item.status != ItemStatus.COMPLETED:
                    item.selected = True
                    item.status = ItemStatus.SELECTED

    def deselect_all(self):
        if self.playlist_info:
            for item in self.playlist_info.items:
                if item.status != ItemStatus.COMPLETED:
                    item.selected = False
                    item.status = ItemStatus.SKIPPED

    def start_download(self, callback, continue_on_error=True):
        """
        Start sequential playlist download in a background thread.
        callback(event, data) events:
          'item_start', 'item_progress', 'item_complete', 'item_failed',
          'item_skipped', 'playlist_progress', 'playlist_complete',
          'playlist_cancelled'
        """
        if self.state == PlaylistState.DOWNLOADING:
            logger.warning("Download already in progress.")
            return

        self.cancel_event.clear()
        self.state = PlaylistState.DOWNLOADING

        thread = threading.Thread(
            target=self._download_loop,
            args=(callback, continue_on_error),
            daemon=True,
        )
        thread.start()
        return thread

    def _download_loop(self, callback, continue_on_error):
        """Main download loop. Runs in background thread."""
        if not self.playlist_info:
            return

        selected_items = [
            it for it in self.playlist_info.items
            if it.selected and it.status not in (ItemStatus.COMPLETED, ItemStatus.SKIPPED)
        ]
        total_selected = len(selected_items)

        if total_selected == 0:
            self.state = PlaylistState.COMPLETED
            summary = self._build_summary()
            callback('playlist_complete', {'summary': summary})
            return

        logger.info(f"Starting playlist download: {total_selected} items, "
                     f"quality: {self.selected_quality['label']}")

        completed = 0
        failed = 0
        skipped = 0
        format_expr = self.selected_quality['format_expr']
        is_audio_only = self.selected_quality.get('audio_only', False)

        for idx, item in enumerate(selected_items):
            # Check cancellation
            if self.cancel_event.is_set():
                item.status = ItemStatus.CANCELLED
                self.state = PlaylistState.CANCELLED
                logger.info("Playlist download cancelled by user.")
                callback('playlist_cancelled', {'summary': self._build_summary()})
                return

            # Check if already in archive (may have been downloaded in a previous session)
            if self.archive.is_archived(item.video_id):
                item.status = ItemStatus.COMPLETED
                item.selected = False
                skipped += 1
                completed += 1
                callback('item_skipped', {
                    'item': item,
                    'reason': 'Already downloaded',
                    'completed': completed,
                    'total': total_selected,
                })
                continue

            self.current_item_index = item.index
            item.status = ItemStatus.DOWNLOADING
            item.progress = 0
            item.error = ''

            ext = 'mp3' if is_audio_only else 'mp4'
            filename = _safe_video_filename(item.playlist_index, item.title, ext)
            output_path = os.path.join(self.output_directory, filename)
            item.output_path = output_path

            callback('item_start', {
                'item': item,
                'current_num': idx + 1,
                'total': total_selected,
            })

            # Overall progress
            overall_pct = (completed / total_selected) * 100
            callback('playlist_progress', {
                'completed': completed,
                'failed': failed,
                'skipped': skipped,
                'total': total_selected,
                'percent': overall_pct,
            })

            result = self._download_single_item(
                item, format_expr, output_path, is_audio_only, callback, idx, total_selected, completed
            )

            if result.success:
                item.status = ItemStatus.COMPLETED
                item.actual_resolution = result.actual_resolution
                item.progress = 100
                completed += 1
                self.archive.mark_completed(item.video_id)
                if self._playlist_state:
                    self._playlist_state.set_item_status(
                        item.video_id, 'COMPLETED', output_path=output_path
                    )
                callback('item_complete', {
                    'item': item,
                    'result': result,
                    'completed': completed,
                    'total': total_selected,
                })
            else:
                item.status = ItemStatus.FAILED
                item.error = result.error_message
                failed += 1
                if self._playlist_state:
                    self._playlist_state.set_item_status(
                        item.video_id, 'FAILED', error=result.error_message
                    )
                callback('item_failed', {
                    'item': item,
                    'result': result,
                    'completed': completed,
                    'total': total_selected,
                })
                if not continue_on_error:
                    self.state = PlaylistState.FAILED
                    callback('playlist_complete', {'summary': self._build_summary()})
                    return

        # Done
        if failed > 0:
            self.state = PlaylistState.COMPLETED_WITH_ERRORS
        else:
            self.state = PlaylistState.COMPLETED

        summary = self._build_summary()
        logger.info(f"Playlist complete. Completed: {summary.completed}, "
                     f"Failed: {summary.failed}, Skipped: {summary.skipped}")
        callback('playlist_complete', {'summary': summary})

    def _download_single_item(self, item, format_expr, output_path, is_audio_only,
                               callback, current_idx, total_selected, completed_so_far):
        """Download a single playlist item using yt-dlp. Returns DownloadResult."""
        max_retries = 3
        last_error = None

        for attempt in range(1, max_retries + 1):
            if self.cancel_event.is_set():
                return DownloadResult(
                    success=False, status=ItemStatus.CANCELLED,
                    video_id=item.video_id, title=item.title,
                    error_message='Cancelled by user',
                )

            try:
                logger.info(f"Downloading [{item.playlist_index}] {item.title} "
                            f"(attempt {attempt}/{max_retries})")

                # Clean partial files
                for p in [output_path, output_path + '.part']:
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except OSError:
                            pass

                actual_resolution = ''

                def progress_hook(d):
                    nonlocal actual_resolution
                    if self.cancel_event.is_set():
                        raise KeyboardInterrupt("Download cancelled")

                    if d.get('status') == 'downloading':
                        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                        downloaded = d.get('downloaded_bytes', 0)
                        speed = d.get('speed', 0) or 0
                        eta = d.get('eta', 0) or 0

                        if total > 0:
                            pct = (downloaded / total) * 100
                        else:
                            pct = 0

                        item.progress = pct
                        item.speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed else ""
                        item.eta_str = f"{eta}s" if eta else ""

                        # Weighted overall progress
                        overall = ((completed_so_far + pct / 100) / total_selected) * 100

                        callback('item_progress', {
                            'item': item,
                            'percent': pct,
                            'speed': item.speed_str,
                            'eta': item.eta_str,
                            'overall_percent': overall,
                            'current_num': current_idx + 1,
                            'total': total_selected,
                        })

                    elif d.get('status') == 'finished':
                        item.status = ItemStatus.PROCESSING
                        item.progress = 100
                        # Try to capture actual resolution
                        info_dict = d.get('info_dict', {})
                        h = info_dict.get('height')
                        if h:
                            actual_resolution = f"{h}p"

                        callback('item_progress', {
                            'item': item,
                            'percent': 100,
                            'speed': '',
                            'eta': '',
                            'overall_percent': ((completed_so_far + 1) / total_selected) * 100,
                            'current_num': current_idx + 1,
                            'total': total_selected,
                            'processing': True,
                        })

                # Build yt-dlp options for this item
                outtmpl = output_path.replace('.mp4', '.%(ext)s').replace('.mp3', '.%(ext)s')
                dl_opts = {
                    'format': format_expr,
                    'outtmpl': outtmpl,
                    'progress_hooks': [progress_hook],
                    'retries': 3,
                    'fragment_retries': 3,
                    'quiet': True,
                    'no_warnings': True,
                }

                # For MP4 output, let yt-dlp merge using FFmpeg
                if not is_audio_only:
                    dl_opts['merge_output_format'] = 'mp4'
                    dl_opts['postprocessors'] = [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]
                else:
                    dl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '0',
                    }]

                opts = self._get_ytdlp_opts(dl_opts)

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info_dict = ydl.extract_info(item.url, download=True)

                # Determine actual output file
                actual_output = output_path
                if not os.path.exists(actual_output):
                    # yt-dlp may have used a different extension, search for it
                    base = os.path.splitext(output_path)[0]
                    for candidate_ext in ['mp4', 'mkv', 'webm', 'mp3', 'm4a']:
                        candidate = f"{base}.{candidate_ext}"
                        if os.path.exists(candidate):
                            actual_output = candidate
                            break

                if os.path.exists(actual_output) and os.path.getsize(actual_output) > 0:
                    fsize = os.path.getsize(actual_output)
                    item.filesize = fsize
                    item.output_path = actual_output

                    # Get actual resolution from info_dict
                    if info_dict and not actual_resolution:
                        h = info_dict.get('height')
                        if h:
                            actual_resolution = f"{h}p"
                        elif info_dict.get('requested_downloads'):
                            for rd in info_dict['requested_downloads']:
                                rh = rd.get('height')
                                if rh:
                                    actual_resolution = f"{rh}p"
                                    break

                    logger.info(f"Download complete: {os.path.basename(actual_output)} "
                                f"({fsize / 1024 / 1024:.1f} MB) [{actual_resolution}]")

                    return DownloadResult(
                        success=True,
                        status=ItemStatus.COMPLETED,
                        video_id=item.video_id,
                        title=item.title,
                        output_path=actual_output,
                        actual_resolution=actual_resolution,
                        actual_format=os.path.splitext(actual_output)[1],
                        filesize=fsize,
                    )
                else:
                    raise IOError(f"Output file missing or empty: {actual_output}")

            except KeyboardInterrupt:
                return DownloadResult(
                    success=False, status=ItemStatus.CANCELLED,
                    video_id=item.video_id, title=item.title,
                    error_message='Cancelled by user',
                )
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                logger.warning(f"Download attempt {attempt} failed for "
                               f"[{item.playlist_index}] {item.title}: {e}")

                # Don't retry permanent errors
                if any(kw in err_str for kw in
                       ['unavailable', 'private', 'sign in', 'login', 'age',
                        'not available', 'copyright', 'removed']):
                    break

                # Clean partial files
                for p in [output_path, output_path + '.part']:
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except OSError:
                            pass

                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)

        # All retries exhausted
        error_msg = str(last_error) if last_error else 'Unknown error'
        # Make user-friendly
        user_msg = self._classify_error(error_msg)
        return DownloadResult(
            success=False,
            status=ItemStatus.FAILED,
            video_id=item.video_id,
            title=item.title,
            error_code=type(last_error).__name__ if last_error else '',
            error_message=user_msg,
        )

    def _classify_error(self, error_msg):
        """Map error patterns to user-friendly messages."""
        msg_lower = error_msg.lower()
        if 'private' in msg_lower:
            return 'This video is private.'
        if 'unavailable' in msg_lower or 'not available' in msg_lower:
            return 'This video is unavailable.'
        if 'age' in msg_lower and 'restrict' in msg_lower:
            return 'Age-restricted video.'
        if 'sign in' in msg_lower or 'login' in msg_lower:
            return 'Requires authentication.'
        if '403' in error_msg:
            return 'Access blocked (HTTP 403).'
        if '429' in error_msg:
            return 'Rate limited (HTTP 429).'
        if 'no video formats' in msg_lower:
            return 'No downloadable formats found.'
        if 'copyright' in msg_lower:
            return 'Blocked due to copyright.'
        if 'removed' in msg_lower:
            return 'Video has been removed.'
        if 'network' in msg_lower or 'connection' in msg_lower or 'timeout' in msg_lower:
            return 'Network error.'
        # Truncate long error messages
        if len(error_msg) > 120:
            return error_msg[:120] + '...'
        return error_msg

    def _build_summary(self):
        """Build a PlaylistSummary from current state."""
        if not self.playlist_info:
            return PlaylistSummary()

        items = self.playlist_info.items
        completed = sum(1 for it in items if it.status == ItemStatus.COMPLETED)
        failed = sum(1 for it in items if it.status == ItemStatus.FAILED)
        skipped = sum(1 for it in items if it.status == ItemStatus.SKIPPED)
        cancelled = sum(1 for it in items if it.status == ItemStatus.CANCELLED)
        selected = sum(1 for it in items if it.selected)
        failed_items = [it for it in items if it.status == ItemStatus.FAILED]

        return PlaylistSummary(
            playlist_title=self.playlist_info.title,
            total_selected=selected,
            completed=completed,
            failed=failed,
            skipped=skipped,
            cancelled=cancelled,
            output_directory=self.output_directory,
            failed_items=failed_items,
        )

    def cancel_download(self):
        """Request cancellation of the current playlist download."""
        logger.info("Cancellation requested.")
        self.cancel_event.set()
        self.state = PlaylistState.CANCELLING

    def retry_failed(self, callback, continue_on_error=True):
        """Retry only failed items."""
        if not self.playlist_info:
            return

        for item in self.playlist_info.items:
            if item.status == ItemStatus.FAILED:
                item.status = ItemStatus.SELECTED
                item.selected = True
                item.progress = 0
                item.error = ''

        self.start_download(callback, continue_on_error)

    def get_failed_count(self):
        if not self.playlist_info:
            return 0
        return sum(1 for it in self.playlist_info.items if it.status == ItemStatus.FAILED)
