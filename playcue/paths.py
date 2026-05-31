from __future__ import annotations

import sys
from pathlib import Path


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def config_dir() -> Path:
    return app_base_dir() / "configs"


def log_dir() -> Path:
    return app_base_dir() / "logs"


def play_history_log_file() -> Path:
    return log_dir() / "play_history.csv"


def play_time_summary_file() -> Path:
    return log_dir() / "play_time_summary.csv"


def backup_configs_dir() -> Path:
    return app_base_dir() / "backups" / "configs"


def login_bonus_history_file() -> Path:
    return log_dir() / "login_bonus_history.csv"


def script_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return app_base_dir() / "PlayCue.py"


def resolve_app_path(path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return (app_base_dir() / value).resolve()
