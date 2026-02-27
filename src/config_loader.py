import json
import os
from pathlib import Path

def get_config_path():
    # Try to find config.json in root or current dir
    root_dir = Path(__file__).parent.parent
    config_path = root_dir / "config.json"
    if not config_path.exists():
        # Fallback to current working directory
        config_path = Path("config.json")
    return config_path

def load_config():
    path = get_config_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    # Default config
    return {
        "source_directory": str(Path.home() / "Downloads"),
        "destination_directory": str(Path.home() / "Downloads"),
        "file_extensions": {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
            "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"],
            "Videos": [".mp4", ".mkv", ".avi", ".mov"],
            "Music": [".mp3", ".wav", ".aac"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Code": [".py", ".js", ".html", ".css", ".json", ".cpp", ".c", ".java"]
        },
        "models": [],
        "clean_names": True,
        "backup_enabled": False
    }

def save_config(config):
    path = get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
