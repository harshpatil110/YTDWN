"""
YTDWN Downloader Module
=======================
Uses yt-dlp for both format discovery and media download.
Uses FFmpeg for video/audio merging and MP3 conversion.
"""

import os
import time
import re
import yt_dlp
from .helpers import safe_filename, ensure_directory, setup_logging, format_size
from .ffmpeg_utils import get_ffmpeg_path, merge_video_audio, convert_to_mp3

logger = setup_logging()


def _extract_video_id(url):
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})',
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def _normalize_url(url):
    """Normalize a YouTube URL to canonical form."""
    vid = _extract_video_id(url)
    if vid:
        return f"https://www.youtube.com/watch?v={vid}"
    return url


def extract_res_val(res_str):
    if not res_str:
        return 0
    return int(''.join(filter(str.isdigit, str(res_str))))


def extract_abr_val(abr_str):
    if not abr_str:
        return 0
    return int(''.join(filter(str.isdigit, str(abr_str))))


class Downloader:
    def __init__(self, download_path):
        self.download_path = download_path
        ensure_directory(self.download_path)
        self.ffmpeg_path = get_ffmpeg_path()
        if not self.ffmpeg_path:
            logger.error("FFmpeg not found.")
            raise FileNotFoundError(
                "FFmpeg not found. Please ensure FFmpeg is installed and added to PATH."
            )
        logger.info(f"Downloader initialized. Download path: {self.download_path}")
        logger.info(f"Download engine: yt-dlp {yt_dlp.version.__version__}")

    def _get_ytdlp_opts(self, extra_opts=None):
        """Build base yt-dlp options with FFmpeg path."""
        opts = {
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': os.path.dirname(self.ffmpeg_path),
            'socket_timeout': 30,
        }
        if extra_opts:
            opts.update(extra_opts)
        return opts

    def _extract_info(self, url):
        """Extract video info and formats using yt-dlp."""
        opts = self._get_ytdlp_opts({
            'skip_download': True,
        })
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _format_stream_info(self, fmt, is_video=True):
        """Convert a yt-dlp format dict to the stream_info dict the UI expects."""
        info = {
            'itag': fmt.get('format_id', ''),
            'mime_type': fmt.get('ext', ''),
            'format': (fmt.get('ext', '')).upper(),
            'filesize': fmt.get('filesize') or fmt.get('filesize_approx') or 0,
            'filesize_str': format_size(
                fmt.get('filesize') or fmt.get('filesize_approx') or 0
            ),
        }
        if is_video:
            height = fmt.get('height', 0)
            info['resolution'] = f"{height}p" if height else 'N/A'
            info['fps'] = fmt.get('fps') or 'N/A'
            info['codec'] = fmt.get('vcodec', 'N/A')
        else:
            abr = fmt.get('abr', 0)
            info['abr'] = f"{int(abr)}kbps" if abr else 'N/A'
            info['codec'] = fmt.get('acodec', 'N/A')
        return info

    def fetch_streams(self, url, status_callback):
        """Fetch metadata and available streams using yt-dlp."""
        try:
            normalized_url = _normalize_url(url)
            logger.info(f"Starting metadata extraction for URL: {normalized_url}")
            status_callback("info", "Fetching streams...", 0)

            info = self._extract_info(normalized_url)
            logger.info("Metadata extraction successful.")

            # Build video_info payload (same structure the UI expects)
            title = info.get('title') or 'Unknown Title'
            video_info = {
                'title': title,
                'author': info.get('channel') or info.get('uploader') or 'Unknown Author',
                'length': info.get('duration') or 0,
                'views': info.get('view_count') or 0,
                'publish_date': info.get('upload_date'),
                'thumbnail_url': info.get('thumbnail'),
            }
            logger.info(f"Fetched video metadata: {title}")

            # Collect video-only and audio-only formats
            all_formats = info.get('formats', [])

            # Video-only formats (has video codec, no audio codec)
            video_fmts = []
            for f in all_formats:
                vcodec = f.get('vcodec', 'none')
                acodec = f.get('acodec', 'none')
                if vcodec != 'none' and acodec == 'none':
                    video_fmts.append(f)

            # Sort by height descending
            video_fmts.sort(key=lambda f: f.get('height', 0), reverse=True)

            # Deduplicate by resolution — keep the best (first) per height
            unique_videos = []
            seen_res = set()
            for f in video_fmts:
                h = f.get('height', 0)
                if h and h not in seen_res:
                    seen_res.add(h)
                    unique_videos.append(self._format_stream_info(f, is_video=True))

            logger.info(f"Extracted {len(unique_videos)} unique video streams.")

            # Audio-only formats (no video codec, has audio codec)
            audio_fmts = []
            for f in all_formats:
                vcodec = f.get('vcodec', 'none')
                acodec = f.get('acodec', 'none')
                if vcodec == 'none' and acodec != 'none':
                    audio_fmts.append(f)

            # Sort by abr descending
            audio_fmts.sort(key=lambda f: f.get('abr', 0) or 0, reverse=True)

            # Deduplicate by abr
            unique_audios = []
            seen_abr = set()
            for f in audio_fmts:
                abr = f.get('abr', 0)
                abr_key = int(abr) if abr else 0
                if abr_key and abr_key not in seen_abr:
                    seen_abr.add(abr_key)
                    unique_audios.append(self._format_stream_info(f, is_video=False))

            logger.info(f"Extracted {len(unique_audios)} unique audio streams.")

            payload = {
                'video_info': video_info,
                'video': unique_videos,
                'audio': unique_audios,
            }
            status_callback("streams_fetched", payload, 100)

        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            logger.error(f"Failed to fetch streams: {error_type} - {error_msg}")

            user_friendly_msg = self._classify_error(error_type, error_msg)
            status_callback("error", user_friendly_msg, 0)

    def _classify_error(self, error_type, error_msg):
        """Map known error patterns to user-friendly messages."""
        msg_lower = error_msg.lower()

        if "private" in msg_lower:
            return "This video is private and cannot be accessed."
        if "unavailable" in msg_lower or "not available" in msg_lower:
            return "This video is unavailable."
        if "age" in msg_lower and "restrict" in msg_lower:
            return "This video is age-restricted and requires authentication."
        if "sign in" in msg_lower or "login" in msg_lower:
            return "This video requires authentication to access."
        if "403" in error_msg:
            return "YouTube blocked access to this stream (HTTP 403 Forbidden). Please try again later."
        if "429" in error_msg:
            return "YouTube rate-limited the request (HTTP 429). Please wait a moment and try again."
        if "no video formats" in msg_lower:
            return "No downloadable formats were found for this video."
        if "bot" in msg_lower:
            return "YouTube rejected the request as bot traffic. Please try again shortly."
        if "network" in msg_lower or "connection" in msg_lower or "timeout" in msg_lower:
            return "A network error occurred. Please check your connection and try again."
        if "sabr" in msg_lower or "potoken" in msg_lower:
            return (
                "YouTube's current stream protection rejected the download request. "
                "Please try again or select another quality."
            )
        return f"An error occurred: {error_type}: {error_msg}"

    def _download_with_ytdlp(self, url, format_id, output_path, status_callback, max_retries=3):
        """
        Download a specific format using yt-dlp with retry logic.
        Returns the path to the downloaded file.
        """
        normalized_url = _normalize_url(url)
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"Starting download attempt {attempt}/{max_retries} "
                    f"for format {format_id}"
                )

                # Clean up any previous partial file
                partial_pattern = output_path
                if os.path.exists(partial_pattern):
                    os.remove(partial_pattern)
                # Also clean .part files
                part_file = partial_pattern + '.part'
                if os.path.exists(part_file):
                    os.remove(part_file)

                def progress_hook(d):
                    if d.get('status') == 'downloading':
                        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                        downloaded = d.get('downloaded_bytes', 0)
                        if total > 0:
                            percent = (downloaded / total) * 100
                            speed = d.get('speed', 0) or 0
                            speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed else ""
                            eta = d.get('eta', 0) or 0
                            eta_str = f"ETA: {eta}s" if eta else ""
                            status_callback(
                                "progress",
                                f"Downloading... {int(percent)}%  {speed_str}  {eta_str}",
                                percent,
                            )
                    elif d.get('status') == 'finished':
                        status_callback("progress", "Download complete, processing...", 100)

                opts = self._get_ytdlp_opts({
                    'format': format_id,
                    'outtmpl': output_path,
                    'progress_hooks': [progress_hook],
                    'retries': 3,
                    'fragment_retries': 3,
                    'quiet': True,
                    'no_warnings': True,
                })

                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([normalized_url])

                # Verify downloaded file
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    fsize = os.path.getsize(output_path)
                    logger.info(
                        f"Download verified: {os.path.basename(output_path)} "
                        f"({fsize / 1024 / 1024:.1f} MB)"
                    )
                    return output_path
                else:
                    raise IOError(
                        f"Downloaded file missing or empty: {output_path}"
                    )

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Download attempt {attempt} failed: "
                    f"{type(e).__name__} - {str(e)}"
                )

                # Clean up partial files
                for p in [output_path, output_path + '.part']:
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except OSError:
                            pass

                # Don't retry permanent errors
                err_str = str(e).lower()
                if any(kw in err_str for kw in
                       ['unavailable', 'private', 'sign in', 'login', 'age']):
                    break

                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.info(f"Waiting {wait}s before retry...")
                    time.sleep(wait)

        raise last_error

    def download_video(self, url, status_callback, video_itag=None):
        """Download video (and merge with audio if adaptive)."""
        try:
            normalized_url = _normalize_url(url)
            logger.info(
                f"Starting video download for URL: {normalized_url}, "
                f"format_id: {video_itag}"
            )
            status_callback("info", "Fetching video info...", 0)

            # Re-extract info to get the title and verify format availability
            info = self._extract_info(normalized_url)
            title = safe_filename(info.get('title') or 'video')

            # Find the selected video format
            all_formats = info.get('formats', [])
            selected_fmt = None
            for f in all_formats:
                if str(f.get('format_id')) == str(video_itag):
                    selected_fmt = f
                    break

            if not selected_fmt:
                logger.warning(f"Format {video_itag} not found in extracted formats.")
                status_callback("error", "The selected video quality is no longer available.", 0)
                return

            height = selected_fmt.get('height', '?')
            vcodec = selected_fmt.get('vcodec', '?')
            logger.info(
                f"Selected format: id={video_itag}, {height}p, codec={vcodec}"
            )

            # Check if this is a video-only or muxed stream
            has_audio = selected_fmt.get('acodec', 'none') != 'none'

            if has_audio:
                # Progressive stream — just download directly
                final_output = os.path.join(self.download_path, f"{title}.mp4")
                status_callback("info", f"Downloading {height}p video...", 0)

                self._download_with_ytdlp(
                    normalized_url, str(video_itag),
                    final_output, status_callback,
                )

                logger.info("Download complete.")
                status_callback("success", f"Successfully downloaded: {title}.mp4", 100)
            else:
                # Adaptive — download video and best audio separately, then merge
                # Find best audio format
                best_audio = None
                for f in all_formats:
                    vc = f.get('vcodec', 'none')
                    ac = f.get('acodec', 'none')
                    if vc == 'none' and ac != 'none':
                        if best_audio is None or (f.get('abr', 0) or 0) > (best_audio.get('abr', 0) or 0):
                            best_audio = f

                if not best_audio:
                    logger.warning("No audio stream found to merge.")
                    status_callback("error", "Could not find a suitable audio stream to merge.", 0)
                    return

                audio_fmt_id = best_audio.get('format_id')
                audio_abr = best_audio.get('abr', '?')
                logger.info(
                    f"Will merge with audio format: id={audio_fmt_id}, "
                    f"{audio_abr}kbps, codec={best_audio.get('acodec', '?')}"
                )

                res_str = f"{height}p" if height != '?' else 'video'
                info_msg = f"Downloading: {title}\nVideo: {res_str} | Audio: {audio_abr}kbps"
                status_callback("info", info_msg, 0)

                ext_v = selected_fmt.get('ext', 'mp4')
                ext_a = best_audio.get('ext', 'm4a')
                temp_video = os.path.join(self.download_path, f"temp_video_{title}.{ext_v}")
                temp_audio = os.path.join(self.download_path, f"temp_audio_{title}.{ext_a}")
                final_output = os.path.join(self.download_path, f"{title}.mp4")

                # Download video
                status_callback("info", f"Downloading Video Stream ({res_str})...", 0)
                self._download_with_ytdlp(
                    normalized_url, str(video_itag),
                    temp_video, status_callback,
                )

                # Download audio
                status_callback("info", f"Downloading Audio Stream ({audio_abr}kbps)...", 0)
                self._download_with_ytdlp(
                    normalized_url, str(audio_fmt_id),
                    temp_audio, status_callback,
                )

                # Merge
                status_callback("info", "Merging Video and Audio...", 100)
                logger.info("Merging audio and video using FFmpeg...")
                merge_video_audio(temp_video, temp_audio, final_output, self.ffmpeg_path)

                # Cleanup temp files
                for p in [temp_video, temp_audio]:
                    if os.path.exists(p):
                        os.remove(p)

                # Verify final output
                if not os.path.exists(final_output) or os.path.getsize(final_output) == 0:
                    raise IOError("FFmpeg merge produced an empty or missing file.")

                logger.info("Merge complete.")
                status_callback("success", f"Successfully downloaded: {title}.mp4", 100)

        except Exception as e:
            logger.exception("Video download failed.")
            user_msg = self._classify_error(type(e).__name__, str(e))
            # Clean up any leftover temp files
            try:
                for pattern in ['temp_video_*', 'temp_audio_*']:
                    import glob
                    for f in glob.glob(os.path.join(self.download_path, pattern)):
                        os.remove(f)
            except OSError:
                pass
            status_callback("error", user_msg, 0)

    def download_mp3(self, url, status_callback, audio_itag=None):
        """Download audio and convert to MP3."""
        try:
            normalized_url = _normalize_url(url)
            logger.info(
                f"Starting audio download for URL: {normalized_url}, "
                f"format_id: {audio_itag}"
            )
            status_callback("info", "Fetching audio info...", 0)

            info = self._extract_info(normalized_url)
            title = safe_filename(info.get('title') or 'audio')

            # Find the selected audio format
            all_formats = info.get('formats', [])
            selected_fmt = None
            for f in all_formats:
                if str(f.get('format_id')) == str(audio_itag):
                    selected_fmt = f
                    break

            if not selected_fmt:
                logger.warning(f"Audio format {audio_itag} not found.")
                status_callback("error", "The selected audio quality is no longer available.", 0)
                return

            abr = selected_fmt.get('abr', '?')
            acodec = selected_fmt.get('acodec', '?')
            logger.info(f"Selected audio format: id={audio_itag}, {abr}kbps, codec={acodec}")

            ext = selected_fmt.get('ext', 'webm')
            temp_audio = os.path.join(self.download_path, f"temp_audio_{title}.{ext}")
            final_output = os.path.join(self.download_path, f"{title}.mp3")

            info_msg = f"Downloading: {title}\nAudio: {abr}kbps"
            status_callback("info", info_msg, 0)

            self._download_with_ytdlp(
                normalized_url, str(audio_itag),
                temp_audio, status_callback,
            )

            status_callback("info", "Converting to MP3...", 100)
            logger.info("Converting audio to MP3 using FFmpeg...")
            convert_to_mp3(temp_audio, final_output, self.ffmpeg_path)

            if os.path.exists(temp_audio):
                os.remove(temp_audio)

            if not os.path.exists(final_output) or os.path.getsize(final_output) == 0:
                raise IOError("MP3 conversion produced an empty or missing file.")

            logger.info("Conversion complete.")
            status_callback("success", f"Successfully downloaded: {title}.mp3", 100)

        except Exception as e:
            logger.exception("Audio download failed.")
            user_msg = self._classify_error(type(e).__name__, str(e))
            # Clean up temp
            try:
                import glob
                for f in glob.glob(os.path.join(self.download_path, 'temp_audio_*')):
                    os.remove(f)
            except OSError:
                pass
            status_callback("error", user_msg, 0)
