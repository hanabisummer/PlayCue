from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LinkItem:
    name: str
    url: str


@dataclass(frozen=True)
class LoginBonusSourceConfig:
    enabled: bool = False
    window_title: str = ""
    url: str = ""
    claimed_patterns: tuple[str, ...] = ()
    unclaimed_patterns: tuple[str, ...] = ()
    timeout_seconds: int = 30
    retry_interval_seconds: int = 5
    ocr_languages: str = "jpn+eng"


@dataclass(frozen=True)
class LoginBonusConfig:
    enabled: bool = False
    reset_time: str = "05:00"
    game_screen: LoginBonusSourceConfig = LoginBonusSourceConfig(timeout_seconds=300)
    web: LoginBonusSourceConfig = LoginBonusSourceConfig(timeout_seconds=30)


@dataclass(frozen=True)
class OBSConfig:
    enabled: bool = False
    auto_launch: bool = False
    launch_as_admin: bool = True
    exe_path: str = ""
    working_dir: str = ""
    args: str = ""
    process_name: str = "obs64.exe"
    websocket_host: str = "127.0.0.1"
    websocket_port: int = 4455
    websocket_password: str = ""
    connect_timeout_seconds: int = 30
    connect_retry_interval_seconds: int = 2
    auto_start_recording_on_game_launch: bool = False
    auto_stop_recording_on_game_exit: bool = False


@dataclass(frozen=True)
class GameConfig:
    game_name: str
    config_file: Path
    game_exe: str = ""
    game_args: str = ""
    launch_unelevated: bool = False
    process_name: str = ""
    active_process_name: str = ""
    game_id: str = ""
    session_prefix: str = ""
    auto_close_on_game_exit: bool = False
    obs: OBSConfig = OBSConfig()
    login_bonus: LoginBonusConfig = LoginBonusConfig()
    auto_open_links: tuple[LinkItem, ...] = ()
    buttons: tuple[LinkItem, ...] = ()
    always_on_top: bool = True
    opacity: float = 0.9
    window_width: int = 360
    window_height: int = 420

    def get_game_key(self) -> str:
        """安定したゲーム識別キーを返す。active_process_name → process_name → game_name の優先順。"""
        for raw in (self.active_process_name, self.process_name):
            if raw and raw.strip():
                for part in re.split(r"[,;]", raw):
                    name = part.strip().lower()
                    if name:
                        return name
        normalized = re.sub(r"\s+", "_", self.game_name.strip().lower())
        return normalized or "unknown"

    def get_game_id(self) -> str:
        """攻略AIログ用のゲームID。明示設定 ``game_id`` 優先、なければ ``get_game_key()``。"""
        if self.game_id and self.game_id.strip():
            return self.game_id.strip()
        return self.get_game_key()
