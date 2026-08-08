from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from pirat.paths import app_dir, is_frozen, vendor_dll


@dataclass
class IdleSession:
    app_id: int
    name: str
    started_at: float
    process: subprocess.Popen
    error: str | None = None

    def elapsed_seconds(self) -> float:
        return max(0.0, time.time() - self.started_at)

    def to_dict(self) -> dict:
        alive = self.process.poll() is None
        return {
            "app_id": self.app_id,
            "name": self.name,
            "started_at": self.started_at,
            "elapsed": self.elapsed_seconds(),
            "alive": alive,
            "error": self.error if alive else (self.error or "exited"),
        }


@dataclass
class SessionManager:
    _sessions: dict[int, IdleSession] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def list_sessions(self) -> list[dict]:
        with self._lock:
            dead: list[int] = []
            result: list[dict] = []
            for app_id, session in self._sessions.items():
                data = session.to_dict()
                if not data["alive"]:
                    dead.append(app_id)
                result.append(data)
            for app_id in dead:
                self._sessions.pop(app_id, None)
            return sorted(result, key=lambda s: s["started_at"])

    def is_running(self, app_id: int) -> bool:
        with self._lock:
            session = self._sessions.get(app_id)
            return bool(session and session.process.poll() is None)

    def start(self, app_id: int, name: str) -> dict:
        with self._lock:
            existing = self._sessions.get(app_id)
            if existing and existing.process.poll() is None:
                return {"ok": False, "error": "already_running", "session": existing.to_dict()}

            root = app_dir()
            dll = vendor_dll()
            log_dir = Path(os.environ.get("TEMP", str(root))) / "pirat_logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"idle_{app_id}_{int(time.time())}.log"

            env = os.environ.copy()
            env["PIRAT_STEAM_API"] = str(dll)
            env["SteamAppId"] = str(app_id)
            env["SteamGameId"] = str(app_id)
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

            if is_frozen():
                cmd = [sys.executable, "--idle", str(app_id)]
            else:
                cmd = [sys.executable, "-m", "pirat.idle_worker", "--idle", str(app_id)]

            log_handle = open(log_file, "w", encoding="utf-8", errors="ignore")
            proc = subprocess.Popen(
                cmd,
                cwd=str(root),
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
            )
            session = IdleSession(app_id=app_id, name=name, started_at=time.time(), process=proc)
            self._sessions[app_id] = session

        # Give SteamAPI a moment to init / fail
        time.sleep(1.2)
        with self._lock:
            session = self._sessions.get(app_id)
            if not session:
                return {"ok": False, "error": "missing"}
            code = session.process.poll()
            if code is not None:
                detail = ""
                try:
                    detail = log_file.read_text(encoding="utf-8", errors="ignore").strip()
                except Exception:
                    pass
                self._sessions.pop(app_id, None)
                return {"ok": False, "error": "failed_start", "detail": detail, "code": code}
            return {"ok": True, "session": session.to_dict()}

    def stop(self, app_id: int) -> dict:
        with self._lock:
            session = self._sessions.pop(app_id, None)
        if not session:
            return {"ok": False, "error": "not_found"}
        self._terminate(session.process)
        return {"ok": True, "elapsed": session.elapsed_seconds()}

    def stop_all(self) -> dict:
        with self._lock:
            items = list(self._sessions.values())
            self._sessions.clear()
        for session in items:
            self._terminate(session.process)
        return {"ok": True, "stopped": len(items)}

    @staticmethod
    def _terminate(proc: subprocess.Popen) -> None:
        if proc.poll() is not None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass