import os
import time
from pytubefix import YouTube
from .helpers import safe_filename, ensure_directory
from .ffmpeg_utils import get_ffmpeg_path, merge_video_audio, convert_to_mp3

class Downloader:
    def __init__(self, download_path):
        self.download_path = download_path
        ensure_directory(self.download_path)
        self.ffmpeg_path = get_ffmpeg_path()
        if not self.ffmpeg_path:
            raise FileNotFoundError("FFmpeg not found. Please ensure FFmpeg is installed and added to PATH.")

    def _progress_hook(self, stream, chunk, bytes_remaining, total_size, callback):
        if callback:
            percent = (1 - bytes_remaining / total_size) * 100
            callback("progress", f"Downloading... {int(percent)}%", percent)

    def download_video(self, url, status_callback):
        try:
            status_callback("info", "Fetching video info...", 0)
            
            # wrapper for progress
            def on_progress(stream, chunk, bytes_remaining):
                self._progress_hook(stream, chunk, bytes_remaining, stream.filesize, status_callback)

            yt = YouTube(url, on_progress_callback=on_progress)
            title = safe_filename(yt.title)
            
            # 1. Get Video Stream
            video_stream = yt.streams.filter(adaptive=True, only_video=True).order_by("resolution").desc().first()
            # 2. Get Audio Stream
            audio_stream = yt.streams.filter(adaptive=True, only_audio=True).order_by("abr").desc().first()

            if not video_stream or not audio_stream:
                status_callback("error", "Could not find suitable streams.", 0)
                return

            info_msg = f"Found: {yt.title}\nVideo: {video_stream.resolution} | Audio: {audio_stream.abr}"
            status_callback("info", info_msg, 0)
            
            # Download Paths
            temp_video = os.path.join(self.download_path, f"temp_video_{title}.mp4")
            temp_audio = os.path.join(self.download_path, f"temp_audio_{title}.m4a")
            final_output = os.path.join(self.download_path, f"{title}.mp4")

            # Download Video
            status_callback("info", "Downloading Video Stream...", 0)
            video_stream.download(output_path=self.download_path, filename=os.path.basename(temp_video))
            
            # Download Audio
            status_callback("info", "Downloading Audio Stream...", 0)
            audio_stream.download(output_path=self.download_path, filename=os.path.basename(temp_audio))

            # Merge
            status_callback("info", "Merging Video and Audio...", 100)
            merge_video_audio(temp_video, temp_audio, final_output, self.ffmpeg_path)

            # Cleanup
            if os.path.exists(temp_video): os.remove(temp_video)
            if os.path.exists(temp_audio): os.remove(temp_audio)

            status_callback("success", f"Successfully downloaded: {title}.mp4", 100)

        except Exception as e:
            status_callback("error", str(e), 0)

    def download_mp3(self, url, status_callback):
        try:
            status_callback("info", "Fetching audio info...", 0)
            
            def on_progress(stream, chunk, bytes_remaining):
                self._progress_hook(stream, chunk, bytes_remaining, stream.filesize, status_callback)

            yt = YouTube(url, on_progress_callback=on_progress)
            title = safe_filename(yt.title)

            audio_stream = yt.streams.filter(adaptive=True, only_audio=True).order_by("abr").desc().first()
            
            if not audio_stream:
                status_callback("error", "No audio stream found.", 0)
                return

            info_msg = f"Found: {yt.title}\nAudio: {audio_stream.abr}"
            status_callback("info", info_msg, 0)

            temp_audio = os.path.join(self.download_path, f"temp_audio_{title}.webm") # pytubefix usually grabs webm/opus for high quality
            final_output = os.path.join(self.download_path, f"{title}.mp3")

            status_callback("info", "Downloading Audio...", 0)
            audio_stream.download(output_path=self.download_path, filename=os.path.basename(temp_audio))

            status_callback("info", "Converting to MP3...", 100)
            convert_to_mp3(temp_audio, final_output, self.ffmpeg_path)

            if os.path.exists(temp_audio): os.remove(temp_audio)

            status_callback("success", f"Successfully downloaded: {title}.mp3", 100)

        except Exception as e:
            status_callback("error", str(e), 0)
