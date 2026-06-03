import os
import sys
import logging

def safe_filename(name):
    """
    Sanitize the filename by removing illegal characters.
    """
    if not name:
        return "Unknown_Video"
    return "".join(c for c in name if c not in r'\/:*?"<>|')

def get_default_download_path():
    r"""
    Get the default download path: C:\Users\<Current User>\Downloads\YouTube
    """
    # os.path.expanduser("~") gets the user's home directory across platforms
    base_path = os.path.join(os.path.expanduser("~"), "Downloads", "YouTube")
    return base_path

def ensure_directory(path):
    """
    Ensure the directory exists.
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def setup_logging():
    logger = logging.getLogger("YTDWN")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File handler
        log_dir = os.path.join(get_default_download_path(), "logs")
        try:
            ensure_directory(log_dir)
            fh = logging.FileHandler(os.path.join(log_dir, "ytdwn.log"))
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception:
            pass # fallback gracefully if log file can't be created
            
    return logger

def safe_format_name(mime_type):
    """
    Safely extract format from mime_type.
    """
    if not mime_type or not isinstance(mime_type, str):
        return "UNKNOWN"
    
    mime_type = mime_type.strip().lower()
    if 'mp4' in mime_type:
        return "MP4"
    elif 'webm' in mime_type:
        return "WEBM"
    elif 'm4a' in mime_type or 'mp4a' in mime_type:
        return "M4A"
    
    parts = mime_type.split('/')
    if len(parts) > 1:
        return parts[1].upper()
    return mime_type.upper()

def format_size(bytes_size):
    if not bytes_size:
        return "Unknown Size"
    try:
        bytes_size = float(bytes_size)
    except (ValueError, TypeError):
        return "Unknown Size"
        
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

def safe_get_stream_info(stream, is_video=True):
    """
    Safely extract and normalize stream information, handling missing metadata.
    """
    info = {
        "itag": getattr(stream, 'itag', None),
        "mime_type": getattr(stream, 'mime_type', ""),
        "format": safe_format_name(getattr(stream, 'mime_type', "")),
        "filesize": getattr(stream, 'filesize', 0),
        "filesize_str": format_size(getattr(stream, 'filesize', 0))
    }

    if is_video:
        info["resolution"] = getattr(stream, 'resolution', None) or "N/A"
        info["fps"] = getattr(stream, 'fps', None) or "N/A"
        info["codec"] = getattr(stream, 'video_codec', None) or "N/A"
    else:
        info["abr"] = getattr(stream, 'abr', None) or "N/A"
        info["codec"] = getattr(stream, 'audio_codec', None) or "N/A"

    return info
