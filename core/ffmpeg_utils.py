import shutil
import subprocess
import os

def get_ffmpeg_path():
    """
    Locate FFmpeg executable.
    Returns path or None if not found.
    """
    return shutil.which("ffmpeg")

def merge_video_audio(video_path, audio_path, output_path, ffmpeg_path):
    """
    Merge video and audio files using FFmpeg.
    """
    cmd = [
        ffmpeg_path,
        "-y",               # Overwrite output file
        "-i", video_path,   # Input video
        "-i", audio_path,   # Input audio
        "-c:v", "copy",     # Copy video stream (no re-encode)
        "-c:a", "aac",      # Re-encode audio to aac (standard for mp4) or copy if compatible
        output_path
    ]
    
    # Run subprocess without showing window on Windows
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
    subprocess.run(cmd, check=True, startupinfo=startupinfo)

def convert_to_mp3(audio_path, output_path, ffmpeg_path):
    """
    Convert audio file to MP3 using FFmpeg.
    """
    cmd = [
        ffmpeg_path,
        "-y",
        "-i", audio_path,
        "-vn",              # No video
        "-acodec", "libmp3lame",
        "-q:a", "0",        # Best quality variable bitrate
        output_path
    ]

    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    subprocess.run(cmd, check=True, startupinfo=startupinfo)
