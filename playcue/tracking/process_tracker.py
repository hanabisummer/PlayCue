from __future__ import annotations

import re
import time
from pathlib import Path

try:
    import psutil
except ImportError:  # pragma: no cover - runtime fallback
    psutil = None


class GameProcessWatcher:
    def __init__(
        self,
        process_name: str,
        on_exit,
        grace_seconds: int = 45,
        missing_threshold: int = 2,
        exe_path: str = "",
        on_process_name_detected=None,
        active_process_name: str = "",
        on_active=None,
    ):
        self.process_name = process_name.lower()
        self.process_names = self._parse_process_names(process_name)
        self.active_process_names = self._parse_process_names(active_process_name)
        self.on_exit = on_exit
        self.grace_seconds = grace_seconds
        self.missing_threshold = missing_threshold
        self.exe_path = str(Path(exe_path).resolve()).lower() if exe_path else ""
        self.on_process_name_detected = on_process_name_detected
        self.on_active = on_active
        self.started_at = time.monotonic()
        self.missing_count = 0
        self.seen_process = False
        self.seen_active_process = False
        self.stopped = False

    @staticmethod
    def _parse_process_names(process_name: str) -> set[str]:
        return {
            name.strip().lower()
            for name in re.split(r"[,;]", process_name)
            if name.strip()
        }

    def tick(self) -> None:
        if self.stopped or not self.process_name or psutil is None:
            return

        is_running, is_active = self._process_state()
        if is_active and not self.seen_active_process:
            self.seen_active_process = True
            if self.on_active:
                self.on_active()

        if self.active_process_names and not self.seen_active_process:
            if is_running:
                self.seen_process = True
                self.missing_count = 0
                return
            if self.seen_process:
                self.missing_count += 1
                if self.missing_count >= self.missing_threshold:
                    self.stopped = True
                    self.on_exit()
            return

        if self.active_process_names and self.seen_active_process:
            is_running = is_active

        if is_running:
            if not self.seen_process:
                self.seen_process = True
                # active_process_name 未設定時は process_name の初回検知で on_active を発火。
                # active_process_name 設定時は上の is_active ブロックで発火するためここでは不要。
                if not self.active_process_names and self.on_active:
                    self.on_active()
            self.missing_count = 0
            return

        if not self.seen_process and time.monotonic() - self.started_at < self.grace_seconds:
            return

        self.missing_count += 1
        if self.missing_count >= self.missing_threshold:
            self.stopped = True
            self.on_exit()

    def _process_state(self) -> tuple[bool, bool]:
        assert psutil is not None
        is_running = False
        is_active = False
        for proc in psutil.process_iter(["name", "exe"]):
            try:
                proc_name = proc.info.get("name") or ""
                proc_name_lower = proc_name.lower()
                if proc_name_lower in self.process_names:
                    is_running = True
                if proc_name_lower in self.active_process_names:
                    is_active = True
                proc_exe = proc.info.get("exe") or ""
                if self.exe_path and proc_exe and str(Path(proc_exe).resolve()).lower() == self.exe_path:
                    detected_name = proc_name.strip()
                    if (
                        not self.active_process_names
                        and len(self.process_names) == 1
                        and detected_name
                        and detected_name.lower() != self.process_name
                    ):
                        self.process_name = detected_name.lower()
                        self.process_names = {self.process_name}
                        if self.on_process_name_detected:
                            self.on_process_name_detected(detected_name)
                    is_running = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                continue
        return is_running, is_active
