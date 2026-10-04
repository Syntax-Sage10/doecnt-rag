"""Docent desktop launcher.

Starts the Streamlit server in a child process (it needs its own main thread for
signal handling) and shows it in a native window via pywebview. Falls back to the
default browser if no native webview is available.

Dev run:   python desktop/launcher.py
Packaged:  built by PyInstaller using docent.spec
"""
from __future__ import annotations

import multiprocessing as mp
import os
import socket
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

from platformdirs import user_cache_dir, user_data_dir, user_log_dir

APP_NAME = "Docent"
# Frozen: PyInstaller unpacks data to sys._MEIPASS. Dev: repo root.
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def _ensure_streams() -> None:
    """Windowed (no-console) builds have sys.stdout/stderr = None; give them a log file."""
    if sys.stdout is None or sys.stderr is None:
        log_dir = Path(user_log_dir(APP_NAME, appauthor=False))
        log_dir.mkdir(parents=True, exist_ok=True)
        log = open(log_dir / "docent.log", "a", buffering=1, encoding="utf-8")
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log


def _setup_environment() -> None:
    """Keep all user data in OS-appropriate folders, never inside the app bundle."""
    data = Path(user_data_dir(APP_NAME, appauthor=False))
    data.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("CHROMA_DIR", str(data / "chroma"))
    os.environ.setdefault(
        "HF_HOME", str(Path(user_cache_dir(APP_NAME, appauthor=False)) / "huggingface")
    )
    os.environ["ANONYMIZED_TELEMETRY"] = "False"        # ChromaDB
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))


def _serve(port: int) -> None:
    """Child process: run the Streamlit server (blocks until killed)."""
    _setup_environment()
    _ensure_streams()
    os.chdir(BASE_DIR)                                   # picks up .streamlit/config.toml
    from streamlit.web import bootstrap

    flags = {
        "server.port": port,
        "server.address": "127.0.0.1",                   # local only, never exposed to the LAN
        "server.headless": True,                         # don't open a browser tab
        "server.fileWatcherType": "none",
        "global.developmentMode": False,                 # required for packaged Streamlit
        "browser.gatherUsageStats": False,
    }
    bootstrap.load_config_options(flag_options=flags)
    bootstrap.run(str(BASE_DIR / "app.py"), False, [], flags)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_ready(port: int, proc: mp.Process, timeout: float = 120) -> bool:
    url = f"http://127.0.0.1:{port}/_stcore/health"
    deadline = time.time() + timeout
    while time.time() < deadline and proc.is_alive():
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def main() -> int:
    mp.freeze_support()                                  # needed for frozen Windows/macOS builds
    mp.set_start_method("spawn", force=True)
    _setup_environment()
    _ensure_streams()

    port = _free_port()
    server = mp.Process(target=_serve, args=(port,), daemon=True)
    server.start()
    try:
        if not _wait_ready(port, server):
            print("Docent server failed to start; see docent.log", file=sys.stderr)
            return 1
        url = f"http://127.0.0.1:{port}"
        try:
            import webview  # type: ignore[import-not-found]
        except ModuleNotFoundError:
            webview = None

        if webview is not None:
            webview.create_window(
                "Docent", url, width=1280, height=860, min_size=(900, 600)
            )
            webview.start()                              # blocks until the window closes
        else:
            print("pywebview unavailable; opening browser", file=sys.stderr)
            webbrowser.open(url)
            server.join()                                # run until the process is killed
    finally:
        if server.is_alive():
            server.terminate()
            server.join(5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
