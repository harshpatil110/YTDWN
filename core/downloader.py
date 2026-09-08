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

    def _get_youtube_client(self, url, on_progress=None, max_retries=3):
        """
        Normalizes the URL and instantiates the YouTube client using the WEB client,
        which automatically handles PO-token generation (via Node.js) in pytubefix >= 10.11.0.
        Includes a retry mechanism.
        """
        from pytubefix.extract import video_id
        
        try:
            vid = video_id(url)
            normalized_url = f"https://www.youtube.com/watch?v={vid}"
        except Exception:
            logger.warning(f"Could not extract standard video_id from {url}. Using original url.")
            normalized_url = url
            
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    import time
                    logger.info(f"YouTube client initialization attempt {attempt}/{max_retries}...")
                    time.sleep(2 ** (attempt - 1))
                
                yt = YouTube(
                    normalized_url, 
                    client='WEB', 
                    on_progress_callback=on_progress
                )
                return yt
                
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt} failed: {type(e).__name__} - {str(e)}")
                
                error_str = str(e).lower()
                if "unavailable" in error_str or "private" in error_str or "login" in error_str or "age" in error_str:
                    break
        
        raise last_error

    def _progress_hook(self, stream, chunk, bytes_remaining, total_size, callback):
        if callback:
            try:
                percent = (1 - bytes_remaining / total_size) * 100
                callback("progress", f"Downloading... {int(percent)}%", percent)
            except Exception as e:
                logger.error(f"Error in progress hook: {e}")

    def fetch_streams(self, url, status_callback):
        try:
            logger.info(f"Starting metadata extraction for URL: {url}")
            status_callback("info", "Fetching streams...", 0)
            
            yt = self._get_youtube_client(url)
            logger.info("Metadata extraction successful.")

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
            error_msg = str(e)
            error_type = type(e).__name__
            logger.error(f"Failed to fetch streams: {error_type} - {error_msg}")
            
            # Map known exceptions to user-friendly messages
            user_friendly_msg = "Unable to fetch YouTube streams."
            if "BotDetection" in error_type or "bot" in error_msg.lower():
                user_friendly_msg += "\n\nYouTube rejected the automated request (Bot Detection). Please try again in a few moments."
            elif "403" in error_msg:
                user_friendly_msg += "\n\nHTTP 403 Forbidden. YouTube blocked access to this stream."
            elif "429" in error_msg:
                user_friendly_msg += "\n\nHTTP 429 Too Many Requests. You are being rate-limited by YouTube."
            elif "unavailable" in error_msg.lower() or "private" in error_msg.lower():
                user_friendly_msg += "\n\nThis video is private, deleted, or otherwise unavailable."
            elif "age" in error_msg.lower():
                user_friendly_msg += "\n\nThis video is age-restricted and requires authentication."
            elif "regex" in error_msg.lower() or "match" in error_msg.lower():
                user_friendly_msg += "\n\nFailed to parse YouTube page. The library may be outdated."
            else:
                user_friendly_msg += f"\n\nAn unexpected error occurred:\n{error_type}: {error_msg}"
                
            status_callback("error", user_friendly_msg, 0)


    def _download_stream_with_retry(self, url, stream_itag, output_path, filename, status_callback, on_progress):
        """
        Attempts to download a stream with SABR/PoToken retry logic and temp file cleanup.
        """
        from pytubefix.exceptions import SABRError
        
        last_error = None
        temp_file = os.path.join(output_path, filename)
        max_retries = 3
        
        for attempt in range(1, max_retries + 1):
            try:
                # Cleanup partial file
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                
                logger.info(f"Starting download attempt {attempt}/{max_retries} for itag {stream_itag}")
                yt = self._get_youtube_client(url, on_progress=on_progress)
                
                if stream_itag:
                    stream = yt.streams.get_by_itag(stream_itag)
                else:
                    raise ValueError("stream_itag is required for _download_stream_with_retry")
                    
                if not stream:
                    raise ValueError(f"Stream {stream_itag} no longer available.")
                
                stream.download(output_path=output_path, filename=filename)
                
                if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
                    raise IOError("Downloaded file is missing or empty.")
                    
                return True
                
            except SABRError as e:
                last_error = e
                logger.warning(f"SABR download failed on attempt {attempt}: {e}")
                if attempt < max_retries:
                    logger.info("Refreshing stream/token state...")
                    time.sleep(2)
            except Exception as e:
                last_error = e
                logger.warning(f"Download error on attempt {attempt}: {type(e).__name__} - {e}")
                if attempt < max_retries:
                    time.sleep(2)
                    
        # Clean up partial if completely failed
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
                
        raise last_error

    def download_video(self, url, status_callback, video_itag=None):
        try:
            from pytubefix.exceptions import SABRError
            logger.info(f"Starting video download for URL: {url}, itag: {video_itag}")
            status_callback("info", "Fetching video info...", 0)
            
            def on_progress(stream, chunk, bytes_remaining):
                self._progress_hook(stream, chunk, bytes_remaining, stream.filesize, status_callback)

            yt = self._get_youtube_client(url, on_progress=on_progress)
            title = safe_filename(getattr(yt, 'title', 'video'))
            
            if video_itag:
                video_stream = yt.streams.get_by_itag(video_itag)
            else:
                video_stream = yt.streams.filter(adaptive=True, only_video=True).order_by("resolution").desc().first()
            
            if not video_stream:
                logger.warning("Could not find video stream.")
                status_callback("error", "Could not find video stream.", 0)
                return
                
            actual_video_itag = video_stream.itag

            if video_stream.includes_audio_track:
                res = getattr(video_stream, 'resolution', 'Unknown')
                info_msg = f"Found: {getattr(yt, 'title', 'Unknown')}\nVideo: {res}"
                status_callback("info", info_msg, 0)
                
                final_output = os.path.join(self.download_path, f"{title}.mp4")
                status_callback("info", "Downloading Video...", 0)
                
                self._download_stream_with_retry(
                    url, actual_video_itag, self.download_path, os.path.basename(final_output), status_callback, on_progress
                )
                
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
                    
                actual_audio_itag = audio_stream.itag

                res = getattr(video_stream, 'resolution', 'Unknown')
                abr = getattr(audio_stream, 'abr', 'Unknown')
                info_msg = f"Found: {getattr(yt, 'title', 'Unknown')}\nVideo: {res} | Audio: {abr}"
                status_callback("info", info_msg, 0)
                
                temp_video = os.path.join(self.download_path, f"temp_video_{title}.mp4")
                temp_audio = os.path.join(self.download_path, f"temp_audio_{title}.m4a")
                final_output = os.path.join(self.download_path, f"{title}.mp4")

                status_callback("info", "Downloading Video Stream...", 0)
                self._download_stream_with_retry(
                    url, actual_video_itag, self.download_path, os.path.basename(temp_video), status_callback, on_progress
                )
                
                status_callback("info", "Downloading Audio Stream...", 0)
                self._download_stream_with_retry(
                    url, actual_audio_itag, self.download_path, os.path.basename(temp_audio), status_callback, on_progress
                )

                status_callback("info", "Merging Video and Audio...", 100)
                logger.info("Merging audio and video using FFmpeg...")
                merge_video_audio(temp_video, temp_audio, final_output, self.ffmpeg_path)

                if os.path.exists(temp_video): os.remove(temp_video)
                if os.path.exists(temp_audio): os.remove(temp_audio)

                logger.info("Merge complete.")
                status_callback("success", f"Successfully downloaded: {title}.mp4", 100)

        except Exception as e:
            logger.exception("Video download failed.")
            error_msg = str(e)
            if "SABRError" in type(e).__name__ or "PoToken INVALID" in error_msg:
                user_msg = "YTDWN could not download this stream because YouTube's current stream protection rejected the download request. Please try again or select another available quality."
            else:
                user_msg = f"Failed to download video: {type(e).__name__} - {e}"
            status_callback("error", user_msg, 0)

    def download_mp3(self, url, status_callback, audio_itag=None):
        try:
            from pytubefix.exceptions import SABRError
            logger.info(f"Starting audio download for URL: {url}, itag: {audio_itag}")
            status_callback("info", "Fetching audio info...", 0)
            
            def on_progress(stream, chunk, bytes_remaining):
                self._progress_hook(stream, chunk, bytes_remaining, stream.filesize, status_callback)

            yt = self._get_youtube_client(url, on_progress=on_progress)
            title = safe_filename(getattr(yt, 'title', 'audio'))

            if audio_itag:
                audio_stream = yt.streams.get_by_itag(audio_itag)
            else:
                audio_stream = yt.streams.filter(adaptive=True, only_audio=True).order_by("abr").desc().first()
            
            if not audio_stream:
                logger.warning("No audio stream found.")
                status_callback("error", "No audio stream found.", 0)
                return
                
            actual_audio_itag = audio_stream.itag

            abr = getattr(audio_stream, 'abr', 'Unknown')
            info_msg = f"Found: {getattr(yt, 'title', 'Unknown')}\nAudio: {abr}"
            status_callback("info", info_msg, 0)

            temp_audio = os.path.join(self.download_path, f"temp_audio_{title}.webm")
            final_output = os.path.join(self.download_path, f"{title}.mp3")

            status_callback("info", "Downloading Audio...", 0)
            
            self._download_stream_with_retry(
                url, actual_audio_itag, self.download_path, os.path.basename(temp_audio), status_callback, on_progress
            )

            status_callback("info", "Converting to MP3...", 100)
            logger.info("Converting audio to MP3 using FFmpeg...")
            convert_to_mp3(temp_audio, final_output, self.ffmpeg_path)

            if os.path.exists(temp_audio): os.remove(temp_audio)

            logger.info("Conversion complete.")
            status_callback("success", f"Successfully downloaded: {title}.mp3", 100)

        except Exception as e:
            logger.exception("Audio download failed.")
            error_msg = str(e)
            if "SABRError" in type(e).__name__ or "PoToken INVALID" in error_msg:
                user_msg = "YTDWN could not download this stream because YouTube's current stream protection rejected the download request. Please try again or select another available quality."
            else:
                user_msg = f"Failed to download audio: {type(e).__name__} - {e}"
            status_callback("error", user_msg, 0)
