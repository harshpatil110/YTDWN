import os
import time
from pytubefix import YouTube
from .helpers import safe_filename, ensure_directory, setup_logging, safe_get_stream_info
from .ffmpeg_utils import get_ffmpeg_path, merge_video_audio, convert_to_mp3

logger = setup_logging()

def extract_res_val(res_str):
    if not res_str: return 0
    return int(''.join(filter(str.isdigit, str(res_str))))

def extract_abr_val(abr_str):
    if not abr_str: return 0
    return int(''.join(filter(str.isdigit, str(abr_str))))

class Downloader:
    def __init__(self, download_path):
        self.download_path = download_path
        ensure_directory(self.download_path)
        self.ffmpeg_path = get_ffmpeg_path()
        if not self.ffmpeg_path:
            logger.error("FFmpeg not found.")
            raise FileNotFoundError("FFmpeg not found. Please ensure FFmpeg is installed and added to PATH.")
        logger.info(f"Downloader initialized. Download path: {self.download_path}")

    def _progress_hook(self, stream, chunk, bytes_remaining, total_size, callback):
        if callback:
            try:
                percent = (1 - bytes_remaining / total_size) * 100
                callback("progress", f"Downloading... {int(percent)}%", percent)
            except Exception as e:
                logger.error(f"Error in progress hook: {e}")

    def fetch_streams(self, url, status_callback):
        try:
            logger.info(f"Fetching streams for URL: {url}")
            status_callback("info", "Fetching streams...", 0)
            yt = YouTube(url)

            # Extract full video metadata
            video_info = {
                "title": getattr(yt, 'title', 'Unknown Title') or "Unknown Title",
                "author": getattr(yt, 'author', 'Unknown Author') or "Unknown Author",
                "length": getattr(yt, 'length', 0),
                "views": getattr(yt, 'views', 0),
                "publish_date": getattr(yt, 'publish_date', None),
                "thumbnail_url": getattr(yt, 'thumbnail_url', None)
            }
            logger.info(f"Fetched video metadata: {video_info['title']}")

            # Fetch Video Streams
            video_streams = yt.streams.filter(type="video")
            video_list = list(video_streams)
            video_list.sort(key=lambda s: extract_res_val(getattr(s, 'resolution', '')), reverse=True)
            
            unique_videos = []
            seen_video_res = set()
            for s in video_list:
                res = getattr(s, 'resolution', None)
                if res and res not in seen_video_res:
                    seen_video_res.add(res)
                    info = safe_get_stream_info(s, is_video=True)
                    unique_videos.append(info)

            logger.info(f"Extracted {len(unique_videos)} unique video streams.")

            # Fetch Audio Streams
            audio_streams = yt.streams.filter(only_audio=True)
            audio_list = list(audio_streams)
            audio_list.sort(key=lambda s: extract_abr_val(getattr(s, 'abr', '')), reverse=True)
            
            unique_audios = []
            seen_audio_abr = set()
            for s in audio_list:
                abr = getattr(s, 'abr', None)
                if abr and abr not in seen_audio_abr:
                    seen_audio_abr.add(abr)
                    info = safe_get_stream_info(s, is_video=False)
                    unique_audios.append(info)

            logger.info(f"Extracted {len(unique_audios)} unique audio streams.")

            # Package both streams and metadata
            payload = {
                "video_info": video_info,
                "video": unique_videos,
                "audio": unique_audios
            }
            status_callback("streams_fetched", payload, 100)
            
        except Exception as e:
            logger.exception("Failed to fetch streams")
            status_callback("error", f"Failed to fetch streams: {e}", 0)

    def download_video(self, url, status_callback, video_itag=None):
        try:
            logger.info(f"Starting video download for URL: {url}, itag: {video_itag}")
            status_callback("info", "Fetching video info...", 0)
            
            def on_progress(stream, chunk, bytes_remaining):
                self._progress_hook(stream, chunk, bytes_remaining, stream.filesize, status_callback)

            yt = YouTube(url, on_progress_callback=on_progress)
            title = safe_filename(getattr(yt, 'title', 'video'))
            
            if video_itag:
                video_stream = yt.streams.get_by_itag(video_itag)
            else:
                video_stream = yt.streams.filter(adaptive=True, only_video=True).order_by("resolution").desc().first()
            
            if not video_stream:
                logger.warning("Could not find video stream.")
                status_callback("error", "Could not find video stream.", 0)
                return

            if video_stream.includes_audio_track:
                res = getattr(video_stream, 'resolution', 'Unknown')
                info_msg = f"Found: {getattr(yt, 'title', 'Unknown')}\nVideo: {res}"
                status_callback("info", info_msg, 0)
                
                final_output = os.path.join(self.download_path, f"{title}.mp4")
                status_callback("info", "Downloading Video...", 0)
                logger.info(f"Downloading progressive stream to {final_output}")
                video_stream.download(output_path=self.download_path, filename=os.path.basename(final_output))
                logger.info("Download complete.")
                status_callback("success", f"Successfully downloaded: {title}.mp4", 100)
            else:
                # Need audio stream to merge
                audio_stream = yt.streams.filter(adaptive=True, only_audio=True).order_by("abr").desc().first()
                if not audio_stream:
                    audio_stream = yt.streams.filter(only_audio=True).first()
                
                if not audio_stream:
                    logger.warning("Could not find audio stream to merge.")
                    status_callback("error", "Could not find suitable audio stream to merge.", 0)
                    return

                res = getattr(video_stream, 'resolution', 'Unknown')
                abr = getattr(audio_stream, 'abr', 'Unknown')
                info_msg = f"Found: {getattr(yt, 'title', 'Unknown')}\nVideo: {res} | Audio: {abr}"
                status_callback("info", info_msg, 0)
                
                temp_video = os.path.join(self.download_path, f"temp_video_{title}.mp4")
                temp_audio = os.path.join(self.download_path, f"temp_audio_{title}.m4a")
                final_output = os.path.join(self.download_path, f"{title}.mp4")

                status_callback("info", "Downloading Video Stream...", 0)
                logger.info(f"Downloading adaptive video stream to {temp_video}")
                video_stream.download(output_path=self.download_path, filename=os.path.basename(temp_video))
                
                status_callback("info", "Downloading Audio Stream...", 0)
                logger.info(f"Downloading adaptive audio stream to {temp_audio}")
                audio_stream.download(output_path=self.download_path, filename=os.path.basename(temp_audio))

                status_callback("info", "Merging Video and Audio...", 100)
                logger.info("Merging audio and video using FFmpeg...")
                merge_video_audio(temp_video, temp_audio, final_output, self.ffmpeg_path)

                if os.path.exists(temp_video): os.remove(temp_video)
                if os.path.exists(temp_audio): os.remove(temp_audio)

                logger.info("Merge complete.")
                status_callback("success", f"Successfully downloaded: {title}.mp4", 100)

        except Exception as e:
            logger.exception("Video download failed.")
            status_callback("error", str(e), 0)

    def download_mp3(self, url, status_callback, audio_itag=None):
        try:
            logger.info(f"Starting audio download for URL: {url}, itag: {audio_itag}")
            status_callback("info", "Fetching audio info...", 0)
            
            def on_progress(stream, chunk, bytes_remaining):
                self._progress_hook(stream, chunk, bytes_remaining, stream.filesize, status_callback)

            yt = YouTube(url, on_progress_callback=on_progress)
            title = safe_filename(getattr(yt, 'title', 'audio'))

            if audio_itag:
                audio_stream = yt.streams.get_by_itag(audio_itag)
            else:
                audio_stream = yt.streams.filter(adaptive=True, only_audio=True).order_by("abr").desc().first()
            
            if not audio_stream:
                logger.warning("No audio stream found.")
                status_callback("error", "No audio stream found.", 0)
                return

            abr = getattr(audio_stream, 'abr', 'Unknown')
            info_msg = f"Found: {getattr(yt, 'title', 'Unknown')}\nAudio: {abr}"
            status_callback("info", info_msg, 0)

            temp_audio = os.path.join(self.download_path, f"temp_audio_{title}.webm")
            final_output = os.path.join(self.download_path, f"{title}.mp3")

            status_callback("info", "Downloading Audio...", 0)
            logger.info(f"Downloading audio stream to {temp_audio}")
            audio_stream.download(output_path=self.download_path, filename=os.path.basename(temp_audio))

            status_callback("info", "Converting to MP3...", 100)
            logger.info("Converting audio to MP3 using FFmpeg...")
            convert_to_mp3(temp_audio, final_output, self.ffmpeg_path)

            if os.path.exists(temp_audio): os.remove(temp_audio)

            logger.info("Conversion complete.")
            status_callback("success", f"Successfully downloaded: {title}.mp3", 100)

        except Exception as e:
            logger.exception("Audio download failed.")
            status_callback("error", str(e), 0)
