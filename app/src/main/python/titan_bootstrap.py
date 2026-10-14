# -*- coding: utf-8 -*-
"""Bootstrap TITAN PRO V80 inside Chaquopy.

Do NOT check filesystem paths for source files — Chaquopy AssetFinder paths
are not reliable. Just try importing and starting the engine.
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


def _patch_bootstrap_storage_if_possible() -> None:
    """Best-effort patch; assets may be read-only."""
    try:
        import titan.layers.core.bootstrap_storage as bs  # type: ignore
        # If we can import it, engine layers are present
        return
    except Exception:
        pass
    try:
        here = Path(__file__).resolve().parent
        bs_path = here / "titan" / "layers" / "core" / "bootstrap_storage.py"
        if not bs_path.is_file():
            return
        raw = bs_path.read_text(encoding="utf-8", errors="replace")
        text = raw.replace(
            "if android_storage_present:\n        raise RuntimeError(",
            "if False and android_storage_present:\n        raise RuntimeError(",
        )
        if text != raw:
            try:
                bs_path.write_text(text, encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass


class _FallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        err = _last_error or "موتور کامل لود نشد"
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
pre{{white-space:pre-wrap;font-size:11px;color:#f87171;background:#0f172a;padding:12px;border-radius:8px;overflow:auto;max-height:50vh}}
</style>
</head>
<body>
<h1>TITAN PRO V80</h1>
<div class="box">
<p>موتور کامل بالا نیامد — حالت پشتیبان.</p>
</div>
<div class="box">
<strong>خطا:</strong>
<pre>{err}</pre>
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
        threading.Thread(target=server.serve_forever, name="titan-fallback", daemon=True).start()
        print("Fallback server on :8080", flush=True)
    except Exception:
        _record_error("Fallback server failed")


def start_titan(files_dir: str) -> str:
    global _started, _error_log, _last_error
    with _lock:
        if _started:
            return "already-started"
        try:
            home_root = Path(files_dir).resolve()
            home = home_root / "MMM"
            home.mkdir(parents=True, exist_ok=True)
            for sub in ("data", "cache", "memory", "secrets"):
                (home / sub).mkdir(exist_ok=True)
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

            # --- Prove engine is importable (no Path/stat games) ---
            try:
                import titan  # noqa: F401
                from titan import runtime as titan_runtime  # noqa: F401
            except Exception:
                _record_error("Cannot import titan.runtime — engine not packaged in APK")
                _start_fallback()
                _started = True
                return "fallback-no-import"

            _patch_bootstrap_storage_if_possible()

            def _run():
                try:
                    from titan.runtime import load
                    # Prefer calling load with as_main so Flask starts
                    load(None, as_main=True)
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


def wait_ready(url: str = "http://127.0.0.1:8080/", timeout: float = 150.0) -> bool:
    deadline = time.time() + float(timeout)
    urls = [
        "http://127.0.0.1:8080/",
        "http://127.0.0.1:8080/api/v80/health",
        "http://127.0.0.1:8080/health",
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
