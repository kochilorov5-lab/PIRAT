from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
import winreg
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

STEAM_ID64_BASE = 76561197960265728
SKIP_APP_IDS = {
    228980,  # Steamworks Common Redistributables
}
STORE_DETAILS_URL = "https://store.steampowered.com/api/appdetails"


@dataclass(frozen=True)
class SteamAccount:
    account_id: int
    steam_id64: str
    persona_name: str
    account_name: str
    most_recent: bool = False


@dataclass(frozen=True)
class SteamGame:
    app_id: int
    name: str
    install_dir: str | None = None
    cover: str | None = None
    installed: bool = False
    owners: tuple[SteamAccount, ...] = ()


def find_steam_path() -> Path | None:
    """Locate Steam on any typical Windows install (registry first, then common paths)."""
    candidates: list[Path] = []

    for root, name in (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
    ):
        try:
            with winreg.OpenKey(root, name) as key:
                for value_name in ("SteamPath", "InstallPath"):
                    try:
                        value, _ = winreg.QueryValueEx(key, value_name)
                    except OSError:
                        continue
                    if value:
                        candidates.append(Path(str(value).replace("/", "\\")))
                try:
                    exe, _ = winreg.QueryValueEx(key, "SteamExe")
                    if exe:
                        candidates.append(Path(str(exe).replace("/", "\\")).parent)
                except OSError:
                    pass
        except OSError:
            pass

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local_app = os.environ.get("LOCALAPPDATA", "")
    for extra in (
        Path(program_files_x86) / "Steam",
        Path(program_files) / "Steam",
        Path(r"D:\Steam"),
        Path(r"E:\Steam"),
        Path(r"F:\Steam"),
        Path(r"G:\Steam"),
        Path(local_app) / "Steam" if local_app else None,
    ):
        if extra is not None:
            candidates.append(extra)

    seen: set[str] = set()
    for path in candidates:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if (resolved / "steam.exe").is_file():
            return resolved
    return None


def _parse_vdf_paths(text: str) -> list[Path]:
    paths: list[Path] = []
    for match in re.finditer(r'"path"\s+"([^"]+)"', text, flags=re.IGNORECASE):
        raw = match.group(1).replace("\\\\", "\\").replace("/", "\\")
        paths.append(Path(raw))
    return paths


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _extract_balanced_block(text: str, open_brace_index: int) -> str | None:
    """Return content inside `{...}` starting at open_brace_index."""
    if open_brace_index < 0 or open_brace_index >= len(text) or text[open_brace_index] != "{":
        return None
    depth = 0
    i = open_brace_index
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace_index + 1 : i]
        i += 1
    return None


def _iter_vdf_numbered_objects(text: str) -> list[tuple[str, str]]:
    """Parse top-level quoted keys with object bodies, brace-safe."""
    items: list[tuple[str, str]] = []
    for match in re.finditer(r'"([^"]+)"\s*\{', text):
        key = match.group(1)
        body = _extract_balanced_block(text, match.end() - 1)
        if body is None:
            continue
        items.append((key, body))
    return items


def _parse_acf(path: Path) -> SteamGame | None:
    try:
        text = _read_text(path)
    except OSError:
        return None

    app_id_m = re.search(r'"appid"\s+"(\d+)"', text, flags=re.IGNORECASE)
    name_m = re.search(r'"name"\s+"([^"]+)"', text, flags=re.IGNORECASE)
    dir_m = re.search(r'"installdir"\s+"([^"]+)"', text, flags=re.IGNORECASE)
    if not app_id_m or not name_m:
        return None

    install_dir = None
    if dir_m:
        install_dir = dir_m.group(1)
    return SteamGame(
        app_id=int(app_id_m.group(1)),
        name=name_m.group(1),
        install_dir=install_dir,
        installed=True,
    )


def is_steam_running() -> bool:
    try:
        import subprocess

        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq steam.exe", "/FO", "CSV", "/NH"],
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return "steam.exe" in out.lower()
    except Exception:
        return False


def launch_steam() -> dict:
    steam = find_steam_path()
    if steam is None:
        return {"ok": False, "error": "steam_missing", "steam_path": ""}
    if is_steam_running():
        return {
            "ok": True,
            "already_running": True,
            "steam_path": str(steam),
            "steam_running": True,
        }

    exe = steam / "steam.exe"
    if not exe.is_file():
        return {"ok": False, "error": "steam_missing", "steam_path": str(steam)}

    try:
        import subprocess

        flags = 0
        if hasattr(subprocess, "DETACHED_PROCESS"):
            flags |= subprocess.DETACHED_PROCESS
        if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            flags |= subprocess.CREATE_NEW_PROCESS_GROUP

        subprocess.Popen(
            [str(exe)],
            cwd=str(steam),
            close_fds=True,
            creationflags=flags,
        )
        return {
            "ok": True,
            "already_running": False,
            "steam_path": str(steam),
            "steam_running": False,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": "launch_failed",
            "detail": str(exc),
            "steam_path": str(steam),
        }


def list_steam_accounts(steam: Path | None = None) -> list[SteamAccount]:
    """All remembered Steam accounts on this PC (loginusers + userdata)."""
    steam = steam or find_steam_path()
    if not steam:
        return []

    by_id: dict[int, SteamAccount] = {}
    loginusers = steam / "config" / "loginusers.vdf"
    if loginusers.is_file():
        text = _read_text(loginusers)
        users_block = _extract_vdf_object_block(text, "users") or text
        for key, body in _iter_vdf_numbered_objects(users_block):
            if not re.fullmatch(r"\d{17}", key):
                continue
            account_id = int(key) - STEAM_ID64_BASE
            if account_id <= 0:
                continue
            persona = re.search(r'"PersonaName"\s+"([^"]*)"', body)
            account_name = re.search(r'"AccountName"\s+"([^"]*)"', body)
            most_recent = bool(re.search(r'"MostRecent"\s+"1"', body))
            auto_login = bool(re.search(r'"AutoLogin"\s+"1"', body))
            name = (persona.group(1).strip() if persona else "") or (
                account_name.group(1).strip() if account_name else ""
            ) or f"Account {account_id}"
            by_id[account_id] = SteamAccount(
                account_id=account_id,
                steam_id64=key,
                persona_name=name,
                account_name=(account_name.group(1) if account_name else ""),
                most_recent=most_recent or auto_login,
            )

    # Also pick up userdata folders (covers accounts missing from loginusers).
    userdata = steam / "userdata"
    if userdata.is_dir():
        for folder in userdata.iterdir():
            if not folder.is_dir() or not folder.name.isdigit():
                continue
            account_id = int(folder.name)
            if account_id <= 0 or account_id in by_id:
                continue
            # Skip Steam's non-user helper folders if any appear.
            if account_id < 1000:
                continue
            steam_id64 = str(account_id + STEAM_ID64_BASE)
            by_id[account_id] = SteamAccount(
                account_id=account_id,
                steam_id64=steam_id64,
                persona_name=f"Account {account_id}",
                account_name="",
                most_recent=False,
            )

    accounts = list(by_id.values())
    active = get_active_account_id(steam)
    accounts.sort(
        key=lambda a: (
            0 if active is not None and a.account_id == active else 1,
            0 if a.most_recent else 1,
            a.persona_name.casefold(),
        )
    )
    return accounts


def _collect_app_ids_from_apps_block(block: str | None) -> set[int]:
    if not block:
        return set()
    ids: set[int] = set()
    # Object-style: "730" { ... }
    ids.update(int(x) for x in re.findall(r'"(\d{1,10})"\s*\{', block))
    # Flat-style: "730" "0" / "730"\t\t"1"
    ids.update(int(x) for x in re.findall(r'"(\d{1,10})"\s+"[^"]*"', block))
    return {i for i in ids if i > 0} - SKIP_APP_IDS


def _account_owned_ids(steam: Path, account_id: int) -> set[int]:
    owned: set[int] = set()
    owned |= _localconfig_app_ids(steam, account_id)
    owned |= _sharedconfig_app_ids(steam, account_id)
    owned |= _userdata_librarycache_ids(steam, account_id)
    return owned - SKIP_APP_IDS


def get_active_account_id(steam: Path | None = None) -> int | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam\ActiveProcess") as key:
            value, _ = winreg.QueryValueEx(key, "ActiveUser")
            account_id = int(value)
            if account_id > 0:
                return account_id
    except OSError:
        pass

    steam = steam or find_steam_path()
    if not steam:
        return None
    loginusers = steam / "config" / "loginusers.vdf"
    if not loginusers.is_file():
        return None

    text = _read_text(loginusers)
    users_block = _extract_vdf_object_block(text, "users") or text
    best_id: int | None = None
    best_ts = -1
    for key, body in _iter_vdf_numbered_objects(users_block):
        if not re.fullmatch(r"\d{17}", key):
            continue
        account_id = int(key) - STEAM_ID64_BASE
        if re.search(r'"MostRecent"\s+"1"', body):
            return account_id
        ts_m = re.search(r'"Timestamp"\s+"(\d+)"', body)
        ts = int(ts_m.group(1)) if ts_m else 0
        if ts > best_ts:
            best_ts = ts
            best_id = account_id
    return best_id


def _cache_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PIRAT"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _meta_path() -> Path:
    return _cache_dir() / "app_meta.json"


def _load_meta_cache() -> dict[int, dict[str, str]]:
    path = _meta_path()
    # Migrate old name-only cache once.
    legacy = _cache_dir() / "app_names.json"
    cache: dict[int, dict[str, str]] = {}
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            for key, value in raw.items():
                app_id = int(key)
                if isinstance(value, dict):
                    name = str(value.get("name") or "")
                    app_type = str(value.get("type") or "").lower()
                    if name or app_type:
                        cache[app_id] = {"name": name, "type": app_type}
        except Exception:
            cache = {}
    elif legacy.is_file():
        try:
            raw = json.loads(legacy.read_text(encoding="utf-8"))
            for key, value in raw.items():
                if value:
                    cache[int(key)] = {"name": str(value), "type": ""}
        except Exception:
            pass
    return cache


def _save_meta_cache(mapping: dict[int, dict[str, str]]) -> None:
    path = _meta_path()
    payload = {
        str(app_id): {"name": meta.get("name", ""), "type": meta.get("type", "")}
        for app_id, meta in mapping.items()
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _fetch_app_meta(app_id: int) -> dict[str, str]:
    """Return name/type from Steam Store, with steamcmd.net fallback."""
    url = f"{STORE_DETAILS_URL}?{urllib.parse.urlencode({'appids': app_id, 'filters': 'basic'})}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PIRAT/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        entry = payload.get(str(app_id)) if isinstance(payload, dict) else None
        if entry and entry.get("success"):
            data = entry.get("data") or {}
            name = str(data.get("name") or "")
            app_type = str(data.get("type") or "").lower()
            if name or app_type:
                return {"name": name, "type": app_type}
    except Exception:
        pass

    try:
        alt = f"https://api.steamcmd.net/v1/info/{app_id}"
        req = urllib.request.Request(alt, headers={"User-Agent": "Mozilla/5.0 PIRAT/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        common = (((payload.get("data") or {}).get(str(app_id)) or {}).get("common") or {})
        name = str(common.get("name") or "")
        app_type = str(common.get("type") or "").lower()
        if name or app_type:
            return {"name": name, "type": app_type}
    except Exception:
        pass
    return {"name": "", "type": ""}


def ensure_app_meta(app_ids: set[int], force: bool = False) -> dict[int, dict[str, str]]:
    cache = {} if force else _load_meta_cache()
    missing = [
        app_id
        for app_id in sorted(app_ids)
        if app_id not in cache or not cache[app_id].get("type")
    ]
    if not missing:
        return cache

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_fetch_app_meta, app_id): app_id for app_id in missing}
        for future in as_completed(futures):
            app_id = futures[future]
            try:
                meta = future.result()
            except Exception:
                meta = {"name": "", "type": ""}
            if meta.get("name") or meta.get("type"):
                prev = cache.get(app_id, {})
                cache[app_id] = {
                    "name": meta.get("name") or prev.get("name", ""),
                    "type": meta.get("type") or prev.get("type", ""),
                }
            else:
                # Remember unknowns so we don't refetch forever in one session dump;
                # mark as non-game filterable empty type.
                cache.setdefault(app_id, {"name": "", "type": "unknown"})

    try:
        _save_meta_cache(cache)
    except Exception:
        pass
    return cache


def _is_game(meta: dict[str, str] | None) -> bool:
    if not meta:
        return False
    return str(meta.get("type") or "").lower() == "game"


def _extract_vdf_object_block(text: str, key: str) -> str | None:
    match = re.search(rf'"{re.escape(key)}"\s*\{{', text, flags=re.IGNORECASE)
    if not match:
        return None
    return _extract_balanced_block(text, match.end() - 1)


def _localconfig_app_ids(steam: Path, account_id: int) -> set[int]:
    path = steam / "userdata" / str(account_id) / "config" / "localconfig.vdf"
    if not path.is_file():
        return set()
    text = _read_text(path)
    # Prefer Software/Valve/Steam/apps when present.
    block = _extract_vdf_object_block(text, "apps")
    return _collect_app_ids_from_apps_block(block)


def _sharedconfig_app_ids(steam: Path, account_id: int) -> set[int]:
    path = steam / "userdata" / str(account_id) / "7" / "remote" / "sharedconfig.vdf"
    if not path.is_file():
        return set()
    text = _read_text(path)
    block = _extract_vdf_object_block(text, "apps") or _extract_vdf_object_block(text, "Apps")
    return _collect_app_ids_from_apps_block(block)


def _librarycache_app_ids(steam: Path) -> set[int]:
    root = steam / "appcache" / "librarycache"
    if not root.is_dir():
        return set()
    return {int(p.name) for p in root.iterdir() if p.is_dir() and p.name.isdigit()}


def _userdata_librarycache_ids(steam: Path, account_id: int) -> set[int]:
    root = steam / "userdata" / str(account_id) / "config" / "librarycache"
    if not root.is_dir():
        return set()
    ids: set[int] = set()
    for path in root.iterdir():
        stem = path.stem
        if stem.isdigit():
            ids.add(int(stem))
        elif path.is_dir() and path.name.isdigit():
            ids.add(int(path.name))
    return ids


def _local_cover(steam: Path, app_id: int) -> str | None:
    folder = steam / "appcache" / "librarycache" / str(app_id)
    for name in ("library_600x900.jpg", "library_600x900_2x.jpg", "header.jpg", "capsule_231x87.jpg"):
        path = folder / name
        if path.is_file():
            return path.resolve().as_uri()
    return None


def _cdn_cover(app_id: int) -> str:
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/library_600x900.jpg"


def load_installed() -> dict[int, SteamGame]:
    steam = find_steam_path()
    if not steam:
        return {}

    library_roots: list[Path] = [steam]
    for rel in (
        steam / "steamapps" / "libraryfolders.vdf",
        steam / "config" / "libraryfolders.vdf",
    ):
        if not rel.is_file():
            continue
        try:
            library_roots.extend(_parse_vdf_paths(_read_text(rel)))
        except OSError:
            pass

    games: dict[int, SteamGame] = {}
    seen_roots: set[str] = set()
    for root in library_roots:
        try:
            resolved = str(root.resolve()).lower()
        except OSError:
            resolved = str(root).lower()
        if resolved in seen_roots:
            continue
        seen_roots.add(resolved)
        apps = Path(root) / "steamapps"
        if not apps.is_dir():
            continue
        for acf in apps.glob("appmanifest_*.acf"):
            game = _parse_acf(acf)
            if game and game.app_id not in games:
                games[game.app_id] = game
    return games


def load_library() -> list[SteamGame]:
    """Full Steam library across remembered accounts (installed + not installed)."""
    steam = find_steam_path()
    if not steam:
        return []

    installed = load_installed()
    accounts = list_steam_accounts(steam)
    active_id = get_active_account_id(steam)

    owners_by_app: dict[int, list[SteamAccount]] = {}
    owned_ids: set[int] = set(installed)

    if accounts:
        for account in accounts:
            for app_id in _account_owned_ids(steam, account.account_id):
                owned_ids.add(app_id)
                bucket = owners_by_app.setdefault(app_id, [])
                if all(existing.account_id != account.account_id for existing in bucket):
                    bucket.append(account)
    else:
        # Single-user / incomplete loginusers fallback.
        if active_id:
            for app_id in _account_owned_ids(steam, active_id):
                owned_ids.add(app_id)
        owned_ids |= _librarycache_app_ids(steam)

    # Shared machine cache can reveal extra titles; keep them without inventing owners.
    owned_ids |= _librarycache_app_ids(steam)
    owned_ids -= SKIP_APP_IDS
    meta = ensure_app_meta(owned_ids)

    games: list[SteamGame] = []
    for app_id in owned_ids:
        info = meta.get(app_id)
        if not _is_game(info):
            continue

        if app_id in installed:
            base = installed[app_id]
            name = base.name
            installed_flag = True
            install_dir = base.install_dir
        else:
            name = (info or {}).get("name") or f"App {app_id}"
            installed_flag = False
            install_dir = None

        catalog_name = (info or {}).get("name") or ""
        if catalog_name and (not name or name.startswith("App ")):
            name = catalog_name

        owners = tuple(owners_by_app.get(app_id, ()))
        # Prefer active account first in UI tags.
        if owners and active_id is not None:
            owners = tuple(
                sorted(
                    owners,
                    key=lambda o: (0 if o.account_id == active_id else 1, o.persona_name.casefold()),
                )
            )

        cover = _local_cover(steam, app_id) or _cdn_cover(app_id)
        games.append(
            SteamGame(
                app_id=app_id,
                name=name,
                install_dir=install_dir,
                cover=cover,
                installed=installed_flag,
                owners=owners,
            )
        )

    return sorted(games, key=lambda g: g.name.casefold())
