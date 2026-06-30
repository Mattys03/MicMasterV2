"""
MicMaster Pro — Preset Manager

Handles loading, saving, and listing audio processing presets.
"""

import json
import os
import sys
from pathlib import Path

# Installation directory (built-in read-only defaults)
if getattr(sys, 'frozen', False):
    # PyInstaller bundle — presets are inside _MEIPASS
    INSTALL_PRESETS_DIR = Path(sys._MEIPASS) / "presets"
else:
    INSTALL_PRESETS_DIR = Path(__file__).parent.parent / "presets"

# Persistent user directory
APPDATA_DIR = Path(os.getenv('APPDATA', os.path.expanduser('~'))) / "MicMaster Pro"
USER_PRESETS_DIR = APPDATA_DIR / "custom_presets"
CONFIG_FILE = APPDATA_DIR / "app_config.json"
def ensure_dirs():
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    USER_PRESETS_DIR.mkdir(parents=True, exist_ok=True)


def list_presets() -> list[dict]:
    """Return all available presets (built-in + custom)."""
    ensure_dirs()
    presets = []

    for folder in [INSTALL_PRESETS_DIR, USER_PRESETS_DIR]:
        if not folder.exists(): 
            continue
        for file in sorted(folder.glob("*.json")):
            if file.name == "app_config.json": continue
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                data["_filename"] = file.stem
                data["_path"] = str(file)
                data["_custom"] = folder == USER_PRESETS_DIR
                presets.append(data)
            except (json.JSONDecodeError, OSError):
                continue

    return presets


def load_preset(filename: str) -> dict | None:
    """Load a preset by filename (without extension)."""
    ensure_dirs()

    for folder in [INSTALL_PRESETS_DIR, USER_PRESETS_DIR]:
        path = folder / f"{filename}.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
    return None


def save_preset(name: str, settings: dict):
    """Save settings as a custom user preset."""
    ensure_dirs()

    slug = name.lower().replace(" ", "_")
    slug = "".join(c for c in slug if c.isalnum() or c == "_")

    data = {**settings, "name": name, "description": f"Preset personalizado: {name}"}

    path = USER_PRESETS_DIR / f"{slug}.json"
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    return str(path)


def delete_preset(filename: str) -> bool:
    """Delete a custom preset. Built-in presets cannot be deleted."""
    path = USER_PRESETS_DIR / f"{filename}.json"
    if path.exists():
        path.unlink()
        return True
    return False

def save_config(config: dict):
    ensure_dirs()
    CONFIG_FILE.write_text(json.dumps(config, indent=4, ensure_ascii=False), encoding="utf-8")

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except:
            return {}
    return {}
