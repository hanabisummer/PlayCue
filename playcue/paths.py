from __future__ import annotations

import os
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


def play_logs_db_file() -> Path:
    """ゲーム攻略AIシステム用プレイログ DB (``play_logs.db``) のパスを返す。

    優先順位:
    1. 環境変数 ``PLAYCUE_PLAY_LOGS_DB`` が設定されていればその値を使う。
       （例: ``g:\\game-llm\\data\\global\\play_logs.db`` を指定して
       PlayCue とは別ディレクトリにログを集約できる。）
    2. 未設定なら PlayCue 本体直下の ``data/global/play_logs.db``。

    既存の CSV ログ (``logs/``) とは独立した SQLite 正本ログの保存先で、
    絶対パスをコードに直書きせず、設定で差し替えられるようにしている。
    """
    override = os.environ.get("PLAYCUE_PLAY_LOGS_DB", "").strip()
    if override:
        return Path(override)
    return app_base_dir() / "data" / "global" / "play_logs.db"


def script_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return app_base_dir() / "PlayCue.py"


def resolve_app_path(path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return (app_base_dir() / value).resolve()
