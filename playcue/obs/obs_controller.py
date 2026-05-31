from __future__ import annotations

import ctypes
import os
import shlex
import subprocess
import threading
import time
from pathlib import Path
from tkinter import messagebox

from playcue.models import OBSConfig


class OBSStatus:
    """Internal OBS state codes.

    Using named constants instead of raw Japanese strings makes comparisons
    refactor-safe and language-independent.  The UI display layer converts
    these codes to human-readable strings via ``obs_status_text()``.
    """

    DISABLED            = "disabled"
    NOT_CONFIGURED      = "not_configured"
    NOT_RUNNING         = "not_running"
    STARTING            = "starting"
    CONNECTING          = "connecting"
    CONNECTED           = "connected"
    RECORDING           = "recording"
    RECORDING_NOT_READY = "recording_not_ready"
    DISCONNECTED        = "disconnected"
    ERROR               = "error"

try:
    import psutil
except ImportError:  # pragma: no cover - runtime fallback
    psutil = None

try:
    from obsws_python import ReqClient
except ImportError:  # pragma: no cover - runtime fallback
    ReqClient = None


class OBSController:
    def __init__(self, config: OBSConfig):
        self.config = config
        self.client = None
        self.status = OBSStatus.DISABLED
        self.recording_started_by_app = False
        if config.enabled:
            self.status = OBSStatus.NOT_RUNNING

    def prepare(
        self,
        launch_as_admin: bool = False,
        show_window: bool = False,
        show_errors: bool = True,
        connect_timeout_seconds: int | None = None,
    ) -> None:
        if not self.config.enabled:
            return
        if self.config.auto_launch:
            self.launch_obs(launch_as_admin=launch_as_admin, show_window=show_window, show_errors=show_errors)
        self.connect(show_errors=show_errors, timeout_seconds=connect_timeout_seconds)

    def launch_obs(self, launch_as_admin: bool = False, show_window: bool = False, show_errors: bool = True) -> None:
        if self._is_obs_running():
            self.status = OBSStatus.CONNECTING
            return

        if not self.config.exe_path:
            self.status = OBSStatus.NOT_CONFIGURED
            self._set_error("OBS exeパスが設定されていません。OBS設定から exeパスを確認してください。", show_errors)
            return
        exe_path = Path(self.config.exe_path)
        if not exe_path.exists():
            self.status = OBSStatus.NOT_CONFIGURED
            # Do not include the full path — it may contain the user's home directory.
            self._set_error("OBS exeが見つかりません。OBS設定から exeパスを確認してください。", show_errors)
            return

        try:
            self.status = OBSStatus.STARTING
            args = shlex.split(self.config.args, posix=False) if self.config.args else []
            if show_window:
                args = [arg for arg in args if arg.lower() not in {"--minimize-to-tray", "--startreplaybuffer"}]
            working_dir = self.config.working_dir or str(exe_path.parent)
            if launch_as_admin and os.name == "nt":
                result = ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",
                    self.config.exe_path,
                    subprocess.list2cmdline(args),
                    working_dir,
                    1,
                )
                if result <= 32:
                    raise OSError(f"ShellExecuteW failed: {result}")
            else:
                subprocess.Popen([self.config.exe_path, *args], cwd=working_dir)
        except OSError:
            # Do not include exc — OSError strings contain the local exe path.
            self._set_error("OBS の起動に失敗しました。", show_errors)

    def connect(self, show_errors: bool = True, timeout_seconds: int | None = None) -> bool:
        if not self.config.enabled:
            return False
        if ReqClient is None:
            self._set_error("obsws-python が未インストールのため、OBS連携を無効化します。", show_errors)
            return False

        self.status = OBSStatus.CONNECTING
        timeout = self.config.connect_timeout_seconds if timeout_seconds is None else max(1, timeout_seconds)
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() <= deadline:
            try:
                self.client = ReqClient(
                    host=self.config.websocket_host,
                    port=self.config.websocket_port,
                    password=self.config.websocket_password,
                    timeout=3,
                )
                if not self._wait_until_ready(deadline):
                    continue
                self.status = OBSStatus.RECORDING if self.is_recording() else OBSStatus.CONNECTED
                return True
            except Exception as exc:  # obsws-python raises multiple connection/auth errors
                last_error = exc
                time.sleep(self.config.connect_retry_interval_seconds)

        # Do not include last_error — auth failures may hint at password details.
        self._set_error("OBS WebSocket に接続できませんでした。", show_errors)
        return False

    def _wait_until_ready(self, deadline: float) -> bool:
        last_error: Exception | None = None
        while time.monotonic() <= deadline:
            try:
                assert self.client is not None
                self.client.get_record_status()
                return True
            except Exception as exc:
                last_error = exc
                self.status = OBSStatus.CONNECTING
                time.sleep(self.config.connect_retry_interval_seconds)
        if last_error is not None:
            self.client = None
        return False

    def is_recording(self) -> bool:
        if self.client is None:
            return False
        try:
            response = self.client.get_record_status()
            return bool(getattr(response, "output_active", getattr(response, "outputActive", False)))
        except Exception:
            self.client = None
            self.status = OBSStatus.DISCONNECTED
            return False

    def poll_status(self) -> bool:
        if not self.config.enabled:
            self.status = OBSStatus.DISABLED
            return False
        if self.client is None and not self.reconnect_once():
            self.status = OBSStatus.DISCONNECTED
            return False
        return self.is_connected()

    def reconnect_once(self) -> bool:
        if ReqClient is None:
            return False
        try:
            self.client = ReqClient(
                host=self.config.websocket_host,
                port=self.config.websocket_port,
                password=self.config.websocket_password,
                timeout=1,
            )
            return self.is_connected()
        except Exception:
            self.client = None
            return False

    def is_connected(self) -> bool:
        if self.client is None:
            self.status = OBSStatus.DISCONNECTED
            return False
        try:
            response = self.client.get_record_status()
            is_recording = bool(getattr(response, "output_active", getattr(response, "outputActive", False)))
            self.status = OBSStatus.RECORDING if is_recording else OBSStatus.CONNECTED
            return True
        except Exception:
            self.client = None
            self.status = OBSStatus.DISCONNECTED
            return False

    def start_recording(self, show_errors: bool = True) -> bool:
        if not self.config.enabled:
            self.status = OBSStatus.DISABLED
            return False
        if self.client is None and not self.connect():
            return False
        if self.is_recording():
            self.status = OBSStatus.RECORDING
            return True

        deadline = time.monotonic() + self.config.connect_timeout_seconds
        last_error: Exception | None = None
        while time.monotonic() <= deadline:
            try:
                self.client.start_record()
                self.recording_started_by_app = True
                self.status = OBSStatus.RECORDING
                return True
            except Exception as exc:
                last_error = exc
                self.status = OBSStatus.RECORDING_NOT_READY
                time.sleep(self.config.connect_retry_interval_seconds)
        self.status = OBSStatus.ERROR
        if show_errors:
            messagebox.showerror(
                "OBS録画エラー",
                "録画開始に失敗しました。OBSの録画設定または出力先を確認してください。",
            )
        return False

    def stop_recording(self, only_if_started_by_app: bool = False, show_errors: bool = True) -> bool:
        if not self.config.enabled:
            self.status = OBSStatus.DISABLED
            return False
        if only_if_started_by_app and not self.recording_started_by_app:
            return False
        if self.client is None and not self.connect():
            return False
        if not self.is_recording():
            self.status = OBSStatus.CONNECTED
            self.recording_started_by_app = False
            return True

        try:
            self.client.stop_record()
            self.recording_started_by_app = False
            self.status = OBSStatus.CONNECTED
            return True
        except Exception:
            self.status = OBSStatus.ERROR
            if show_errors:
                messagebox.showerror(
                    "OBS録画エラー",
                    "録画停止に失敗しました。OBS側で録画状態を確認してください。",
                )
            return False

    def _is_obs_running(self) -> bool:
        if not self.config.process_name or psutil is None:
            return False
        target = self.config.process_name.lower()
        for proc in psutil.process_iter(["name"]):
            try:
                if (proc.info.get("name") or "").lower() == target:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                continue
        return False

    def _set_error(self, message: str, show_error_dialog: bool = True) -> None:
        self.status = OBSStatus.ERROR
        if show_error_dialog and threading.current_thread() is threading.main_thread():
            messagebox.showerror('OBSエラー', message)
