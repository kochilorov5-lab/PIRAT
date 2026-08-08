from __future__ import annotations

import argparse
import ctypes
import os
import sys
import time
from pathlib import Path

from pirat.paths import vendor_dll


def _dll_path() -> Path:
    env = os.environ.get("PIRAT_STEAM_API")
    if env:
        return Path(env)
    return vendor_dll()


def _resolve_init(steam: ctypes.CDLL):
    # Some redistributables export only SteamAPI_InitSafe.
    for name in ("SteamAPI_Init", "SteamAPI_InitSafe"):
        try:
            fn = getattr(steam, name)
        except AttributeError:
            continue
        fn.restype = ctypes.c_bool
        fn.argtypes = []
        return fn
    raise AttributeError("SteamAPI_Init / SteamAPI_InitSafe not found in steam_api64.dll")


def run_idle(app_id: int) -> int:
    dll_file = _dll_path()
    if not dll_file.is_file():
        print(f"steam_api64.dll not found: {dll_file}", flush=True)
        return 2

    work = Path(os.environ.get("TEMP", ".")) / f"pirat_idle_{app_id}_{os.getpid()}"
    work.mkdir(parents=True, exist_ok=True)
    (work / "steam_appid.txt").write_text(str(app_id), encoding="ascii")

    os.environ["SteamAppId"] = str(app_id)
    os.environ["SteamGameId"] = str(app_id)
    os.chdir(work)

    try:
        steam = ctypes.CDLL(str(dll_file))
    except OSError as exc:
        print(f"Failed to load steam_api64.dll: {exc}", flush=True)
        return 3

    try:
        steam_init = _resolve_init(steam)
    except AttributeError as exc:
        print(str(exc), flush=True)
        return 5

    steam.SteamAPI_Shutdown.restype = None
    steam.SteamAPI_Shutdown.argtypes = []
    run_callbacks = None
    if hasattr(steam, "SteamAPI_RunCallbacks"):
        steam.SteamAPI_RunCallbacks.restype = None
        steam.SteamAPI_RunCallbacks.argtypes = []
        run_callbacks = steam.SteamAPI_RunCallbacks

    if not steam_init():
        print("SteamAPI_Init failed. Is Steam running and do you own this AppID?", flush=True)
        return 4

    print(f"PIRAT idle OK appid={app_id}", flush=True)
    try:
        while True:
            if run_callbacks is not None:
                run_callbacks()
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            steam.SteamAPI_Shutdown()
        except Exception:
            pass
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pirat-idle")
    parser.add_argument("--idle", type=int, required=True, help="Steam AppID to idle")
    args = parser.parse_args(argv)
    try:
        return run_idle(args.idle)
    except Exception as exc:
        print(f"idle crashed: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
