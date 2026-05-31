from __future__ import annotations

from playcue.models import LoginBonusConfig, LoginBonusSourceConfig, OBSConfig


def obs_config_to_dict(config: OBSConfig) -> dict[str, object]:
    return {
        "enabled": config.enabled,
        "auto_launch": config.auto_launch,
        "exe_path": config.exe_path,
        "working_dir": config.working_dir,
        "args": config.args,
        "process_name": config.process_name,
        "websocket_host": config.websocket_host,
        "websocket_port": config.websocket_port,
        "websocket_password": config.websocket_password,
        "connect_timeout_seconds": config.connect_timeout_seconds,
        "connect_retry_interval_seconds": config.connect_retry_interval_seconds,
        "auto_start_recording_on_game_launch": config.auto_start_recording_on_game_launch,
        "auto_stop_recording_on_game_exit": config.auto_stop_recording_on_game_exit,
    }


def login_bonus_config_to_dict(config: LoginBonusConfig) -> dict[str, object]:
    return {
        "enabled": config.enabled,
        "reset_time": config.reset_time,
        "game_screen": login_bonus_source_to_dict(config.game_screen),
        "web": login_bonus_source_to_dict(config.web),
    }


def login_bonus_source_to_dict(config: LoginBonusSourceConfig) -> dict[str, object]:
    return {
        "enabled": config.enabled,
        "window_title": config.window_title,
        "url": config.url,
        "claimed_patterns": list(config.claimed_patterns),
        "unclaimed_patterns": list(config.unclaimed_patterns),
        "timeout_seconds": config.timeout_seconds,
        "retry_interval_seconds": config.retry_interval_seconds,
        "ocr_languages": config.ocr_languages,
    }


def config_filename(game_name: str) -> str:
    safe_name = "".join(ch.lower() if ch.isalnum() else "_" for ch in game_name).strip("_")
    return f"{safe_name or 'game'}.json"
