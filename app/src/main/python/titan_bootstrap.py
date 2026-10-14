# -*- coding: utf-8 -*-
"""Bootstrap TITAN PRO V80 modular engine inside Chaquopy Android APK.
Fixed: do NOT use path.stat().st_size (broken on Chaquopy AssetFinder).
"""
from __future__ import annotations

import os
import sys
import threading
import time
import traceback
import urllib.request
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

_started = False
_lock = threading.Lock()
_last_error = ""
_error_log = None
_fallback_started = False


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
    print(_last_error, flush=True)
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


def _file_len(path: Path) -> int:
    """Read length of a file. Chaquopy AssetFinder often breaks path.stat().st_size."""
    try:
        # Prefer reading a small prefix to prove the real file is present
        data = path.read_bytes()
        return len(data)
    except Exception:
        try:
            return path.stat().st_size
        except Exception:
            return 0


def _check_engine_present(here: Path) -> str:
    """Return empty string if OK, otherwise error description.

    IMPORTANT: never trust path.stat().st_size on Chaquopy — it often returns 0
    for files stored inside the APK assets.
    """
    runtime = here / "titan" / "runtime.py"
    try:
        content = runtime.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"titan/runtime.py cannot be read ({runtime}): {e}"

    if len(content) < 1000:
        return f"titan/runtime.py too small ({len(content)} bytes) at {runtime}"

    if "LAYER_ORDER" not in content:
        return f"titan/runtime.py does not look like the full engine (no LAYER_ORDER)"

    layers = here / "titan" / "layers"
    if not layers.is_dir():
        return "titan/layers/ directory missing"

    # Count layers without relying on rglob size (also can be flaky on assets)
    try:
        count = sum(1 for p in layers.rglob("*.py"))
    except Exception:
        count = 0
        # Fallback: try a few known critical files
        critical = [
            "core/bootstrap_storage.py",
            "web/flask_app.py",
            "hardening/v80_advanced_platform.py",
            "entry/main_entry.py",
        ]
        for rel in critical:
            p = layers / rel
            try:
                if len(p.read_text(encoding="utf-8", errors="replace")) > 100:
                    count += 1
            except Exception:
                pass
        if count >= 3:
            count = 80  # treat as present enough to try starting

    if count < 20:
        return f"Only {count} layer .py files found (expected 80+). Engine ZIP was not extracted correctly at build time."

    return ""


class _FallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        err = _last_error or "نامشخص - موتور کامل لود نشد"
        body = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TITAN V80</title>
<style>
body{{font-family:system-ui;background:#0b1220;color:#e2e8f0;margin:0;padding:24px;line-height:1.6}}
h1{{color:#38bdf8;font-size:1.4rem}}
.box{{background:#1e293b;border-radius:12px;padding:16px;margin:16px 0;border:1px solid #334155}}
pre{{white-space:pre-wrap;font-size:12px;color:#f87171;background:#0f172a;padding:12px;border-radius:8px;overflow:auto}}
.ok{{color:#4ade80}}
</style>
</head>
<body>
<h1>TITAN PRO V80</h1>
<div class="box">
<p class="ok">موتور کامل بالا نیامد — حالت پشتیبان فعال است.</p>
<p>این یعنی فایل‌های پایتون موتور یا وابستگی‌ها (numpy/pandas) داخل APK درست لود نشده‌اند.</p>
</div>
<div class="box">
<strong>آخرین خطا:</strong>
<pre>{err}</pre>
</div>
<div class="box">
<p>راه‌حل: از Actions یک بیلد تازه بگیرید و APK جدید را نصب کنید.</p>
</div>
</body>
</html>"""
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _start_fallback():
    global _fallback_started
    if _fallback_started:
        return
    _fallback_started = True
    try:
        server = HTTPServer(("127.0.0.1", 8080), _FallbackHandler)
        t = threading.Thread(target=server.serve_forever, name="titan-fallback", daemon=True)
        t.start()
        print("Fallback HTTP server started on 127.0.0.1:8080", flush=True)
    except Exception:
        _record_error("Fallback server failed")


def start_titan(files_dir: str) -> str:
    """Start the real TITAN V80 modular Flask engine in a background thread."""
    global _started, _error_log, _last_error
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

            # Diagnostic (Chaquopy-safe)
            missing = _check_engine_present(here)
            if missing:
                _last_error = "ENGINE INCOMPLETE: " + missing
                print(_last_error, flush=True)
                _start_fallback()
                _started = True
                return "fallback-incomplete"

            bs_path = here / "titan" / "layers" / "core" / "bootstrap_storage.py"
            if bs_path.is_file():
                try:
                    raw = bs_path.read_text(encoding="utf-8", errors="replace")
                    patched = _patch_bootstrap_storage(raw)
                    if patched != raw:
                        try:
                            bs_path.write_text(patched, encoding="utf-8")
                        except Exception:
                            pass  # assets may be read-only; patch is best-effort
                except Exception:
                    _record_error("patch bootstrap_storage")

            def _run():
                try:
                    from titan.runtime import load
                    load(str(here / "titan" / "runtime.py"), as_main=True)
                except Exception:
                    _record_error("TITAN runtime.load error")
                    _start_fallback()

            threading.Thread(target=_run, name="titan-v80-flask", daemon=True).start()
            _started = True
            return "started"
        except Exception:
            _record_error("TITAN bootstrap error")
            _start_fallback()
            _started = True
            return "fallback-error"


def wait_ready(url: str = "http://127.0.0.1:8080/api/v80/health", timeout: float = 120.0) -> bool:
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
                with urllib.request.urlopen(u, timeout=2.0) as resp:
                    if 200 <= getattr(resp, "status", 200) < 500:
                        return True
            except Exception:
                pass
        time.sleep(1.0)
    _start_fallback()
    return False


def last_error() -> str:
    return _last_error or ""
