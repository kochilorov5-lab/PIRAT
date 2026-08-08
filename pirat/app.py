from __future__ import annotations

import threading

import webview

from pirat.i18n import all_strings
from pirat.paths import web_dir
from pirat.sessions import SessionManager
from pirat.steam_lib import (
    find_steam_path,
    get_active_account_id,
    is_steam_running,
    launch_steam as start_steam_client,
    list_steam_accounts,
    load_library,
)


class Api:
    def __init__(self) -> None:
        self.lang = "ru"
        self.manager = SessionManager()
        self._games_cache: list[dict] = []
        self._lock = threading.Lock()
        self._window: webview.Window | None = None
        self._is_maximized = False

    def attach_window(self, window: webview.Window) -> None:
        self._window = window
        self._is_maximized = bool(getattr(window, "maximized", False))

    def _native_is_maximized(self) -> bool | None:
        native = getattr(self._window, "native", None) if self._window else None
        if native is None:
            return None
        try:
            # WinForms: Normal=0, Minimized=1, Maximized=2
            return int(native.WindowState) == 2
        except Exception:
            return None

    def window_minimize(self) -> dict:
        if self._window is None:
            return {"ok": False}
        try:
            self._window.minimize()
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def window_toggle_maximize(self) -> dict:
        if self._window is None:
            return {"ok": False}
        try:
            native_max = self._native_is_maximized()
            is_max = self._is_maximized if native_max is None else native_max
            if is_max:
                self._window.restore()
                self._is_maximized = False
                return {"ok": True, "maximized": False}
            self._window.maximize()
            self._is_maximized = True
            return {"ok": True, "maximized": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def window_close(self) -> dict:
        try:
            self.manager.stop_all()
        except Exception:
            pass
        if self._window is not None:
            try:
                self._window.destroy()
            except Exception:
                try:
                    native = getattr(self._window, "native", None)
                    if native is not None:
                        native.Close()
                except Exception:
                    pass
        return {"ok": True}

    def window_is_maximized(self) -> dict:
        native_max = self._native_is_maximized()
        if native_max is not None:
            self._is_maximized = native_max
        return {"ok": True, "maximized": bool(self._is_maximized)}

    def window_get_bounds(self) -> dict:
        if self._window is None:
            return {"ok": False}
        return {
            "ok": True,
            "x": int(getattr(self._window, "x", 0) or 0),
            "y": int(getattr(self._window, "y", 0) or 0),
            "width": int(getattr(self._window, "width", 1180) or 1180),
            "height": int(getattr(self._window, "height", 760) or 760),
        }

    def window_set_bounds(self, x: int, y: int, width: int, height: int) -> dict:
        if self._window is None:
            return {"ok": False}
        min_w, min_h = 780, 560
        width_i = max(min_w, int(width))
        height_i = max(min_h, int(height))
        x_i = int(x)
        y_i = int(y)
        try:
            self._window.move(x_i, y_i)
        except Exception:
            pass
        try:
            self._window.resize(width_i, height_i)
        except Exception:
            return {"ok": False}
        return {"ok": True, "x": x_i, "y": y_i, "width": width_i, "height": height_i}

    def ready(self) -> dict:
        return {
            "ok": True,
            "lang": self.lang,
            "strings": all_strings(self.lang),
            "steam_path": str(find_steam_path() or ""),
            "steam_running": is_steam_running(),
            "creator": "PIRAT",
            "version": "1.0.0",
        }

    def set_language(self, lang: str) -> dict:
        self.lang = "ru" if lang == "ru" else "en"
        return {"ok": True, "lang": self.lang, "strings": all_strings(self.lang)}

    def refresh_library(self) -> dict:
        games = load_library()
        steam = find_steam_path()
        active_id = get_active_account_id(steam)
        accounts = list_steam_accounts(steam)
        payload = [
            {
                "app_id": g.app_id,
                "name": g.name,
                "cover": g.cover,
                "installed": g.installed,
                "owners": [
                    {
                        "id": o.account_id,
                        "name": o.persona_name,
                        "account_name": o.account_name,
                        "active": bool(active_id and o.account_id == active_id),
                    }
                    for o in g.owners
                ],
            }
            for g in games
        ]
        with self._lock:
            self._games_cache = payload
        return {
            "ok": True,
            "games": payload,
            "count": len(payload),
            "accounts": [
                {
                    "id": a.account_id,
                    "name": a.persona_name,
                    "account_name": a.account_name,
                    "active": bool(active_id and a.account_id == active_id),
                }
                for a in accounts
            ],
            "active_account_id": active_id,
            "steam_path": str(steam or ""),
            "steam_running": is_steam_running(),
        }

    def get_library(self) -> dict:
        with self._lock:
            if not self._games_cache:
                return self.refresh_library()
            return {
                "ok": True,
                "games": list(self._games_cache),
                "steam_path": str(find_steam_path() or ""),
                "steam_running": is_steam_running(),
            }

    def start_idle(self, app_id: int, name: str | None = None) -> dict:
        try:
            app_id_i = int(app_id)
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid_appid"}
        if app_id_i <= 0:
            return {"ok": False, "error": "invalid_appid"}
        if not is_steam_running():
            steam = find_steam_path()
            return {
                "ok": False,
                "error": "steam_required",
                "steam_path": str(steam or ""),
                "can_launch": steam is not None,
                "steam_running": False,
            }

        display = (name or "").strip() or self._name_for(app_id_i)
        result = self.manager.start(app_id_i, display)
        result["sessions"] = self._sessions_payload()
        result["steam_running"] = True
        return result

    def steam_status(self) -> dict:
        steam = find_steam_path()
        return {
            "ok": True,
            "steam_running": is_steam_running(),
            "steam_path": str(steam or ""),
            "can_launch": steam is not None,
        }

    def launch_steam(self) -> dict:
        result = start_steam_client()
        result["steam_running"] = is_steam_running()
        return result

    def stop_idle(self, app_id: int) -> dict:
        try:
            app_id_i = int(app_id)
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid_appid"}
        result = self.manager.stop(app_id_i)
        result["sessions"] = self._sessions_payload()
        return result

    def stop_all(self) -> dict:
        result = self.manager.stop_all()
        result["sessions"] = []
        return result

    def get_sessions(self) -> dict:
        return {
            "ok": True,
            "sessions": self._sessions_payload(),
            "steam_running": is_steam_running(),
        }

    def _sessions_payload(self) -> list[dict]:
        covers = {g["app_id"]: g.get("cover") for g in self._games_cache}
        sessions = self.manager.list_sessions()
        for session in sessions:
            session["cover"] = covers.get(session["app_id"])
        return sessions

    def _name_for(self, app_id: int) -> str:
        with self._lock:
            for game in self._games_cache:
                if game["app_id"] == app_id:
                    return game["name"]
        return f"App {app_id}"


def run() -> None:
    api = Api()
    index = web_dir() / "index.html"
    window = webview.create_window(
        title="Накрутка часов",
        url=index.as_uri(),
        js_api=api,
        width=1180,
        height=760,
        min_size=(780, 560),
        resizable=True,
        frameless=True,
        easy_drag=False,
        shadow=False,
        transparent=False,
        background_color="#071018",
    )
    api.attach_window(window)

    def on_closing() -> None:
        api.manager.stop_all()

    window.events.closing += on_closing
    webview.start(debug=False)
