"""Mewgent — Live Mewgenics Companion App.

Entry point: ``python -m src.main``
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from src.utils.config_loader import APP_DATA_DIR, PROJECT_ROOT, AppConfig, load_config
from src.utils.logging_setup import setup_logging

if getattr(sys, "frozen", False):
    _exe_dir = Path(sys.executable).parent
    if (_exe_dir / ".env").exists():
        load_dotenv(_exe_dir / ".env")
    else:
        load_dotenv(PROJECT_ROOT / ".env")
else:
    load_dotenv(PROJECT_ROOT / "src" / ".env")

log = logging.getLogger("mewgent.main")

PIDFILE = APP_DATA_DIR / "data" / "mewgent.pid"


def _kill_previous_instance() -> None:
    """Kill any previously running Mewgent instance using the PID file."""
    if not PIDFILE.exists():
        return
    try:
        old_pid = int(PIDFILE.read_text().strip())
        if old_pid == os.getpid():
            return
        import subprocess

        subprocess.run(
            ["taskkill", "/PID", str(old_pid), "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("Killed previous Mewgent instance (PID %d)", old_pid)
        time.sleep(0.3)
    except (ValueError, OSError):
        pass
    finally:
        PIDFILE.unlink(missing_ok=True)


def _write_pidfile() -> None:
    PIDFILE.parent.mkdir(parents=True, exist_ok=True)
    PIDFILE.write_text(str(os.getpid()))


def _remove_pidfile() -> None:
    PIDFILE.unlink(missing_ok=True)


def _resolve_save_path(cfg: AppConfig) -> Path | None:
    """Return the save file path from config, or auto-detect the most recent."""
    from src.data.save_reader import find_save_files

    if cfg.save_file.path:
        p = Path(cfg.save_file.path)
        if p.exists():
            return p
        log.warning("Configured save path does not exist: %s", p)

    saves = find_save_files()
    if not saves:
        log.warning("No Mewgenics save files found — save watcher disabled")
        return None

    best = max(saves, key=lambda p: p.stat().st_mtime)
    log.info("Auto-detected save file: %s", best)
    return best


def run_gui(cfg: AppConfig) -> None:
    """Main entry point with PySide6 overlay + React UI."""
    from PySide6.QtWidgets import QApplication

    from src.ui.bridge import OverlayBridge
    from src.ui.overlay_shell import OverlayShell

    app = QApplication(sys.argv)

    save_watcher = None
    if cfg.save_file.enabled:
        save_path = _resolve_save_path(cfg)
        if save_path:
            from src.capture.save_watcher import SaveWatcher

            save_watcher = SaveWatcher(
                save_path,
                poll_ms=cfg.save_file.poll_interval_ms,
            )

    bridge = OverlayBridge(cfg)
    overlay = OverlayShell(cfg, bridge, save_watcher=save_watcher)

    if cfg.update.check_url:
        from src.utils.update_checker import UpdateCheckerThread

        update_checker = UpdateCheckerThread(cfg.update.check_url, parent=bridge)
        update_checker.update_found.connect(bridge.on_update_found)
        update_checker.start()

    overlay.show()
    sys.exit(app.exec())


def run_dev_ui(cfg: AppConfig) -> None:
    """Launch the overlay with mock data for UI development.

    No capture pipeline, no Win32 calls — works on macOS and Windows.
    When no real save file is available, a MockSaveWatcher provides
    realistic fake data so every UI widget is populated.
    """
    from PySide6.QtWidgets import QApplication

    from src.ui.bridge import OverlayBridge
    from src.ui.overlay_shell import OverlayShell

    app = QApplication(sys.argv)

    save_watcher = None
    if cfg.save_file.enabled:
        save_path = _resolve_save_path(cfg)
        if save_path:
            from src.capture.save_watcher import SaveWatcher

            save_watcher = SaveWatcher(
                save_path,
                poll_ms=cfg.save_file.poll_interval_ms,
            )

    if save_watcher is None:
        from src.capture.mock_save_watcher import MockSaveWatcher

        save_watcher = MockSaveWatcher()
        log.info("No save file — using mock save data for dev UI")

    bridge = OverlayBridge(cfg)
    overlay = OverlayShell(cfg, bridge, dev_mode=True, save_watcher=save_watcher)

    if cfg.update.check_url:
        from src.utils.update_checker import UpdateCheckerThread

        update_checker = UpdateCheckerThread(cfg.update.check_url, parent=bridge)
        update_checker.update_found.connect(bridge.on_update_found)
        update_checker.start()

    overlay.show()
    log.info("Dev UI mode active — showing overlay with mock data")
    sys.exit(app.exec())


def main() -> None:
    cfg = load_config()
    log_path = str(APP_DATA_DIR / cfg.logging.file) if cfg.logging.file else None
    setup_logging(level=cfg.logging.level, log_file=log_path)
    from src.version import __version__

    log.info("Mewgent v%s starting", __version__)

    if "--dev-ui" in sys.argv:
        run_dev_ui(cfg)
        return

    _kill_previous_instance()
    _write_pidfile()

    try:
        run_gui(cfg)
    finally:
        _remove_pidfile()


if __name__ == "__main__":
    main()
