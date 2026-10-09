from __future__ import annotations

import os
from pathlib import Path

WINDOWS_CANDIDATES = (
    Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
    / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"))
    / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome Beta/Application/chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome SxS/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"))
    / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
    / "Microsoft/Edge/Application/msedge.exe",
)


def locate_browser() -> Path:
    override = os.environ.get("RENDER_INSPECTOR_CHROME_PATH")
    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"RENDER_INSPECTOR_CHROME_PATH does not exist: {path}")
        return path
    for candidate in WINDOWS_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Chrome, Chromium, or Edge was not found")
