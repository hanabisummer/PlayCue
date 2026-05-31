from __future__ import annotations

import os
import subprocess
import sys

from playcue.paths import script_path

_STARTUP_TASK_NAME = "PlayCue"


class StartupTaskController:
    @staticmethod
    def is_enabled() -> bool:
        if os.name != "nt":
            return False
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", _STARTUP_TASK_NAME],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0

    @staticmethod
    def set_enabled(enabled: bool) -> None:
        if os.name != "nt":
            return
        if enabled:
            command = StartupTaskController._task_command()
            result = subprocess.run(
                [
                    "schtasks",
                    "/Create",
                    "/SC",
                    "ONLOGON",
                    "/RL",
                    "HIGHEST",
                    "/TN",
                    _STARTUP_TASK_NAME,
                    "/TR",
                    command,
                    "/F",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            result = subprocess.run(
                ["schtasks", "/Delete", "/TN", _STARTUP_TASK_NAME, "/F"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0 and not StartupTaskController.is_enabled():
                return
        if result.returncode != 0:
            raise OSError((result.stderr or result.stdout or "タスクスケジューラ更新に失敗しました。").strip())

    @staticmethod
    def _task_command() -> str:
        if getattr(sys, "frozen", False):
            return subprocess.list2cmdline([sys.executable])
        return subprocess.list2cmdline([sys.executable, str(script_path())])
