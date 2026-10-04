"""Per-user settings stored outside the app bundle (e.g. the Gemini API key).

Location:  Windows %APPDATA%/Docent · macOS ~/Library/Application Support/Docent · Linux ~/.config/Docent
The file is created with owner-only permissions (0600) on POSIX systems.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from platformdirs import user_config_dir


def settings_path() -> Path:
    return Path(user_config_dir("Docent", appauthor=False)) / "settings.json"


def _read() -> dict:
    try:
        return json.loads(settings_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write(data: dict) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)


def load_api_key() -> str | None:
    return _read().get("gemini_api_key") or None


def save_api_key(key: str) -> None:
    data = _read()
    data["gemini_api_key"] = key
    _write(data)

def load_theme() -> str:
    mode = _read().get("theme", "Auto")
    return mode if mode in ("Auto", "Light", "Dark") else "Auto"


def save_theme(mode: str) -> None:
    data = _read()
    data["theme"] = mode
    _write(data)

    
def clear_api_key() -> None:
    data = _read()
    data.pop("gemini_api_key", None)
    _write(data)
