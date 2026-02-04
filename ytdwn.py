from pytubefix import YouTube
from pytubefix.cli import on_progress
import os
import subprocess
import shutil

DOWNLOAD_PATH = r"C:\Users\harsh\Downloads\YouTube"


def safe_filename(name):
    return "".join(c for c in name if c not in r'\/:*?"<>|')


def get_ffmpeg_path():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError(
            "FFmpeg not found. Make sure FFmpeg is installed and accessible."
        )
    return ffmpeg


def download_highest_video(url):
    yt = YouTube(url, on_progress_callback=on_progress)
    print(f"\nTitle: {yt.title}")

    video_stream = (
        yt.streams
        .filter(adaptive=True, only_video=True)
        .order_by("resolution")
        .desc()
        .first()
    )

    audio_stream = (
        yt.streams
        .filter(adaptive=True, only_audio=True)
        .order_by("abr")
        .desc()
        .first()
    )

    print(f"Video Resolution: {video_stream.resolution}")
    print(f"Audio Bitrate: {audio_stream.abr}")

    video_file = video_stream.download(
        output_path=DOWNLOAD_PATH, filename="video"
    )
    audio_file = audio_stream.download(
        output_path=DOWNLOAD_PATH, filename="audio"
    )

    output_file = os.path.join(
        DOWNLOAD_PATH,
        f"{safe_filename(yt.title)}.mp4"
    )

    ffmpeg_path = get_ffmpeg_path()
    print(f"Using FFmpeg at: {ffmpeg_path}")

    subprocess.run(
        [
            ffmpeg_path,
            "-y",
            "-i", video_file,
            "-i", audio_file,
            "-c:v", "copy",
            "-c:a", "aac",
            output_file
        ],
        check=True
    )

    os.remove(video_file)
    os.remove(audio_file)

    print("\n✅ Highest quality video downloaded & merged successfully!")


if __name__ == "__main__":
    print("=== YouTube Downloader ===")
    print("1. Highest Quality Video (4K / 2K supported)")
    print("2. Highest Quality MP3\n")

    choice = input("Enter your choice (1 or 2): ")
    url = input("Enter YouTube URL: ")

    if choice == "1":
        download_highest_video(url)
    else:
        print("Only video mode enabled in this version.")

