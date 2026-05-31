from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from playcue.models import GameConfig
from playcue.paths import app_base_dir, play_history_log_file


BASE_DIR = app_base_dir()
LOG_FILE = play_history_log_file()


class PlayTimeLogger:
    HEADER = [
        "session_start",
        "session_end",
        "date",
        "game_name",
        "elapsed_seconds",
        "elapsed_hhmmss",
        "config_file",
        "game_key",
        "process_name",
        "active_process_name",
        "game_exe_name",
    ]

    @staticmethod
    def format_hhmmss(seconds: int) -> str:
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def save(self, config: GameConfig, session_start: datetime, elapsed_seconds: int) -> None:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        exists = LOG_FILE.exists()
        session_end = datetime.now()
        with LOG_FILE.open("a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(self.HEADER)
            writer.writerow(
                [
                    session_start.strftime("%Y-%m-%d %H:%M:%S"),
                    session_end.strftime("%Y-%m-%d %H:%M:%S"),
                    session_end.strftime("%Y-%m-%d"),
                    config.game_name,
                    int(elapsed_seconds),
                    self.format_hhmmss(elapsed_seconds),
                    str(config.config_file.relative_to(BASE_DIR))
                    if config.config_file.is_relative_to(BASE_DIR)
                    else f"external:{config.config_file.name}",
                    config.get_game_key(),
                    config.process_name,
                    config.active_process_name,
                    Path(config.game_exe).name if config.game_exe else "",
                ]
            )
