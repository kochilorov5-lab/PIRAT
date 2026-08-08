from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Directory containing the executable (or project root in source mode)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """Bundled resources root (PyInstaller _MEIPASS or project root)."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return app_dir()
    return Path(__file__).resolve().parent.parent


def web_dir() -> Path:
    return resource_dir() / "web"


def icon_path() -> Path:
    for candidate in (
        resource_dir() / "assets" / "pirat.ico",
        resource_dir() / "assets" / "pirat.png",
        app_dir() / "assets" / "pirat.ico",
        app_dir() / "assets" / "pirat.png",
    ):
        if candidate.is_file():
            return candidate
    return resource_dir() / "assets" / "pirat.ico"


def vendor_dll() -> Path:
    bundled = resource_dir() / "vendor" / "steam_api64.dll"
    if bundled.is_file():
        return bundled
    beside = app_dir() / "vendor" / "steam_api64.dll"
    return beside
