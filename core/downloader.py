import os
import time
from pytubefix import YouTube
from .helpers import safe_filename, ensure_directory
from .ffmpeg_utils import get_ffmpeg_path, merge_video_audio, convert_to_mp3

def format_size(bytes_size):
    if not bytes_size:
        return "Unknown Size"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

def extract_res_val(res_str):
    if not res_str: return 0
    return int(''.join(filter(str.isdigit, res_str)))

def extract_abr_val(abr_str):
    if not abr_str: return 0
    return int(''.join(filter(str.isdigit, abr_str)))

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

    def fetch_streams(self, url, status_callback):
        try:
            status_callback("info", "Fetching streams...", 0)
            yt = YouTube(url)

            # Fetch Video Streams
            video_streams = yt.streams.filter(type="video")
            video_list = list(video_streams)
            video_list.sort(key=lambda s: extract_res_val(s.resolution), reverse=True)
            
            unique_videos = []
            seen_video_res = set()
            for s in video_list:
                res = s.resolution
                if res and res not in seen_video_res:
                    seen_video_res.add(res)
                    unique_videos.append({
                        "itag": s.itag,
                        "resolution": res,
                        "mime_type": s.mime_type.split('/')[-1].upper(),
                        "filesize_str": format_size(s.filesize)
                    })

            # Fetch Audio Streams
            audio_streams = yt.streams.filter(only_audio=True)
            audio_list = list(audio_streams)
            audio_list.sort(key=lambda s: extract_abr_val(s.abr), reverse=True)
            
            unique_audios = []
            seen_audio_abr = set()
            for s in audio_list:
                abr = s.abr
                if abr and abr not in seen_audio_abr:
                    seen_audio_abr.add(abr)
                    unique_audios.append({
                        "itag": s.itag,
                        "abr": abr,
                        "mime_type": s.mime_type.split('/')[-1].upper(),
                        "filesize_str": format_size(s.filesize)
                    })

            status_callback("streams_fetched", {"video": unique_videos, "audio": unique_audios}, 100)
        except Exception as e:
            status_callback("error", f"Failed to fetch streams: {e}", 0)

    def download_video(self, url, status_callback, video_itag=None):
        try:
            status_callback("info", "Fetching video info...", 0)
            
            # wrapper for progress
            def on_progress(stream, chunk, bytes_remaining):
                self._progress_hook(stream, chunk, bytes_remaining, stream.filesize, status_callback)

            yt = YouTube(url, on_progress_callback=on_progress)
            title = safe_filename(yt.title)
            
            if video_itag:
                video_stream = yt.streams.get_by_itag(video_itag)
            else:
                # 1. Get Video Stream
                video_stream = yt.streams.filter(adaptive=True, only_video=True).order_by("resolution").desc().first()
            
            if not video_stream:
                status_callback("error", "Could not find video stream.", 0)
                return

            if video_stream.includes_audio_track:
                info_msg = f"Found: {yt.title}\nVideo: {video_stream.resolution}"
                status_callback("info", info_msg, 0)
                
                final_output = os.path.join(self.download_path, f"{title}.mp4")
                status_callback("info", "Downloading Video...", 0)
                video_stream.download(output_path=self.download_path, filename=os.path.basename(final_output))
                status_callback("success", f"Successfully downloaded: {title}.mp4", 100)
            else:
                # Need audio stream to merge
                audio_stream = yt.streams.filter(adaptive=True, only_audio=True).order_by("abr").desc().first()
                if not audio_stream:
                    audio_stream = yt.streams.filter(only_audio=True).first()
                
                if not audio_stream:
                    status_callback("error", "Could not find suitable audio stream to merge.", 0)
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

    def download_mp3(self, url, status_callback, audio_itag=None):
        try:
            status_callback("info", "Fetching audio info...", 0)
            
            def on_progress(stream, chunk, bytes_remaining):
                self._progress_hook(stream, chunk, bytes_remaining, stream.filesize, status_callback)

            yt = YouTube(url, on_progress_callback=on_progress)
            title = safe_filename(yt.title)

            if audio_itag:
                audio_stream = yt.streams.get_by_itag(audio_itag)
            else:
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
