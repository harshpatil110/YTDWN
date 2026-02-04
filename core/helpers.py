import os
import sys

def safe_filename(name):
    """
    Sanitize the filename by removing illegal characters.
    """
    return "".join(c for c in name if c not in r'\/:*?"<>|')

def get_default_download_path():
    """
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
