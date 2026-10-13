# -*- coding: utf-8 -*-
"""Bootstrap TITAN PRO V80 modular engine inside Chaquopy Android APK.

Uses app-private storage (filesDir/MMM) so no All-files permission is required.
Patches the hard-lock that would otherwise refuse Android when shared storage
is present but not writable.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import traceback
import urllib.request
from pathlib import Path

_started = False
_lock = threading.Lock()
_last_error = ""
_error_log = None


def _record_error(label: str) -> str:
    global _last_error
    details = traceback.format_exc()
    _last_error = f"{label}:\n{details}"
    try:
        if _error_log is not None:
            _error_log.parent.mkdir(parents=True, exist_ok=True)
            with _error_log.open("a", encoding="utf-8") as fp:
                fp.write("\n" + "=" * 70 + "\n" + _last_error + "\n")
    except Exception:
        pass
    print(_last_error)
    return _last_error


def _patch_bootstrap_storage(text: str) -> str:
    """Allow app-private TITAN_HOME on Android (disable shared-storage hard-fail)."""
    text = text.replace(
        "if android_storage_present:\n        raise RuntimeError(",
        "if False and android_storage_present:\n        raise RuntimeError(",
    )
    needle = (
        "candidates = (\n"
        "        TITAN_SHARED_STORAGE,\n"
        "        Path(\"/sdcard\"),\n"
        "        Path(\"/storage/self/primary\"),\n"
        "    )"
    )
    if needle in text:
        text = text.replace(
            needle,
            "# Patched for Android app private storage (Chaquopy)\n"
            "    _env_home = str(os.environ.get(\"TITAN_HOME\") or \"\").strip()\n"
            "    if _env_home:\n"
            "        try:\n"
            "            _p = Path(_env_home)\n"
            "            if _p.name != TITAN_FOLDER_NAME:\n"
            "                _p = _p / TITAN_FOLDER_NAME\n"
            "            _p.mkdir(parents=True, exist_ok=True)\n"
            "            (_p / \".titan_jjj_probe\").write_text(\"ok\", encoding=\"utf-8\")\n"
            "            (_p / \".titan_jjj_probe\").unlink(missing_ok=True)\n"
            "            return _p\n"
            "        except OSError:\n"
            "            pass\n"
            "    candidates = (\n"
            "        TITAN_SHARED_STORAGE,\n"
            "        Path(\"/sdcard\"),\n"
            "        Path(\"/storage/self/primary\"),\n"
            "    )",
        )
    return text


def start_titan(files_dir: str) -> str:
    """Start the real TITAN V80 modular Flask engine in a background thread."""
    global _started, _error_log
    with _lock:
        if _started:
            return "already-started"
        try:
            home_root = Path(files_dir).resolve()
            home = home_root / "MMM"
            home.mkdir(parents=True, exist_ok=True)
            (home / "data").mkdir(exist_ok=True)
            (home / "cache").mkdir(exist_ok=True)
            (home / "memory").mkdir(exist_ok=True)
            (home / "secrets").mkdir(exist_ok=True)
            _error_log = home / "data" / "android_bootstrap_errors.log"

            os.environ["TITAN_HOME"] = str(home_root)
            os.environ["TITAN_HOST"] = "127.0.0.1"
            os.environ["TITAN_PORT"] = "8080"
            os.environ["TITAN_OPEN_BROWSER"] = "0"
            os.environ["TITAN_ANALYSIS_ONLY"] = "1"
            os.environ["TITAN_LIVE_TRADING"] = "0"
            os.environ.setdefault("TMPDIR", str(home / "cache" / "tmp"))
            os.environ.setdefault("TEMP", str(home / "cache" / "tmp"))
            os.environ.setdefault("TMP", str(home / "cache" / "tmp"))
            os.environ["PYTHONUNBUFFERED"] = "1"

            here = Path(__file__).resolve().parent
            if str(here) not in sys.path:
                sys.path.insert(0, str(here))

            bs_path = here / "titan" / "layers" / "core" / "bootstrap_storage.py"
            if bs_path.is_file():
                raw = bs_path.read_text(encoding="utf-8", errors="replace")
                patched = _patch_bootstrap_storage(raw)
                if patched != raw:
                    bs_path.write_text(patched, encoding="utf-8")

            def _run():
                try:
                    from titan.runtime import load
                    load(str(here / "titan" / "runtime.py"), as_main=True)
                except Exception:
                    _record_error("TITAN runtime.load error")

            threading.Thread(target=_run, name="titan-v80-flask", daemon=True).start()
            _started = True
            return "started"
        except Exception:
            _record_error("TITAN bootstrap error")
            raise RuntimeError(_last_error)


def wait_ready(url: str = "http://127.0.0.1:8080/api/v80/health", timeout: float = 240.0) -> bool:
    deadline = time.time() + float(timeout)
    urls = [
        url,
        "http://127.0.0.1:8080/api/v80/health",
        "http://127.0.0.1:8080/",
        "http://127.0.0.1:8080/health",
        "http://localhost:8080/api/v80/health",
        "http://localhost:8080/",
    ]
    while time.time() < deadline:
        for u in urls:
            try:
                with urllib.request.urlopen(u, timeout=2.5) as resp:
                    if 200 <= getattr(resp, "status", 200) < 500:
                        return True
            except Exception:
                pass
        time.sleep(1.0)
    return False


def last_error() -> str:
    return _last_error or ""
