from __future__ import annotations

import json
import re
from pathlib import Path

from playcue.models import (
    GameConfig,
    LinkItem,
    LoginBonusConfig,
    LoginBonusSourceConfig,
    OBSConfig,
)
from playcue.paths import config_dir as default_config_dir
from playcue.config.validator import ConfigLoadResult, ConfigValidationIssue


class ConfigLoader:
    @staticmethod
    def load(path: Path) -> GameConfig:
        if not path.exists():
            raise FileNotFoundError(f"設定ファイルが見つかりません: {path}")

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        game_name = str(data.get("game_name", "")).strip()
        if not game_name:
            raise ValueError("game_name は必須です")

        return GameConfig(
            game_name=game_name,
            config_file=path,
            game_exe=str(data.get("game_exe", "")).strip(),
            game_args=str(data.get("game_args", "")).strip(),
            launch_unelevated=bool(data.get("launch_unelevated", False)),
            process_name=str(data.get("process_name", "")).strip(),
            active_process_name=str(data.get("active_process_name", "")).strip(),
            game_id=str(data.get("game_id", "")).strip(),
            session_prefix=str(data.get("session_prefix", "")).strip(),
            auto_close_on_game_exit=bool(data.get("auto_close_on_game_exit", False)),
            obs=ConfigLoader._parse_obs(data.get("obs", {})),
            login_bonus=ConfigLoader._parse_login_bonus(data.get("login_bonus", {})),
            auto_open_links=ConfigLoader._parse_links(data.get("auto_open_links", [])),
            buttons=ConfigLoader._parse_links(data.get("buttons", [])),
            always_on_top=bool(data.get("always_on_top", True)),
            opacity=ConfigLoader._clamp_float(data.get("opacity", 0.9), 0.3, 1.0),
            window_width=ConfigLoader._positive_int(data.get("window_width", 360), 360),
            window_height=ConfigLoader._positive_int(data.get("window_height", 420), 420),
        )

    @staticmethod
    def list_configs(config_dir: Path | None = None) -> list[GameConfig]:
        directory = config_dir or default_config_dir()
        configs: list[GameConfig] = []
        for path in sorted(directory.glob("*.json")):
            configs.append(ConfigLoader.load(path))
        return configs

    @staticmethod
    def list_configs_with_issues(config_dir: Path | None = None) -> ConfigLoadResult:
        """Load all JSON configs in *config_dir*, tolerating individual failures.

        Unlike :meth:`list_configs`, this method never raises.  Files that
        cannot be loaded are recorded as ``"error"`` issues and skipped.
        Files that load but contain suspicious values (missing exe, malformed
        link URLs) are recorded as ``"warning"`` issues and still included in
        the result.

        Issue ``file`` fields contain the bare filename only — never an
        absolute path — so they are safe for display and logging.
        """
        directory = config_dir or default_config_dir()
        result = ConfigLoadResult()

        if not directory.exists():
            return result

        for path in sorted(directory.glob("*.json")):
            try:
                config = ConfigLoader.load(path)
            except json.JSONDecodeError:
                result.issues.append(ConfigValidationIssue(
                    level="error",
                    file=path.name,
                    field="",
                    message="JSON 形式が不正です",
                ))
                continue
            except ValueError:
                result.issues.append(ConfigValidationIssue(
                    level="error",
                    file=path.name,
                    field="game_name",
                    message="game_name が空です",
                ))
                continue
            except OSError:
                result.issues.append(ConfigValidationIssue(
                    level="error",
                    file=path.name,
                    field="",
                    message="ファイルを読み込めません",
                ))
                continue

            # Soft warnings — config is still usable but may fail at runtime.
            if config.game_exe and not Path(config.game_exe).exists():
                result.issues.append(ConfigValidationIssue(
                    level="warning",
                    file=path.name,
                    field="game_exe",
                    message="game_exe が見つかりません",
                ))

            for link in config.buttons:
                if not ConfigLoader._is_valid_url_or_path(link.url):
                    result.issues.append(ConfigValidationIssue(
                        level="warning",
                        file=path.name,
                        field="buttons.url",
                        message=f"リンク「{link.name}」の URL が不正です",
                    ))

            result.configs.append(config)

        return result

    @staticmethod
    def _is_valid_url_or_path(url: str) -> bool:
        """Return True if *url* looks like a usable link for PlayCue.

        Accepted formats:
        - ``http://`` / ``https://`` — standard web URLs
        - ``file://`` — local file via browser
        - ``steam://`` — Steam protocol links (e.g. store pages, game runs)
        - ``C:/…`` or ``C:\\…`` — Windows absolute file paths
        """
        lower = url.lower()
        if lower.startswith(("http://", "https://", "file://", "steam://")):
            return True
        # Windows absolute paths: drive letter followed by / or \
        if re.match(r"[a-z]:[/\\]", lower):
            return True
        return False

    @staticmethod
    def _parse_links(value: object) -> tuple[LinkItem, ...]:
        if not isinstance(value, list):
            return ()
        links: list[LinkItem] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            url = str(item.get("url", "")).strip()
            if name and url:
                links.append(LinkItem(name=name, url=url))
        return tuple(links)

    @staticmethod
    def _parse_obs(value: object) -> OBSConfig:
        if not isinstance(value, dict):
            return OBSConfig()
        return OBSConfig(
            enabled=bool(value.get("enabled", False)),
            auto_launch=bool(value.get("auto_launch", False)),
            launch_as_admin=bool(value.get("launch_as_admin", True)),
            exe_path=str(value.get("exe_path", "")).strip(),
            working_dir=str(value.get("working_dir", "")).strip(),
            args=str(value.get("args", "")).strip(),
            process_name=str(value.get("process_name", "obs64.exe")).strip(),
            websocket_host=str(value.get("websocket_host", "127.0.0.1")).strip(),
            websocket_port=ConfigLoader._positive_int(value.get("websocket_port", 4455), 4455),
            websocket_password=str(value.get("websocket_password", "")),
            connect_timeout_seconds=ConfigLoader._positive_int(value.get("connect_timeout_seconds", 30), 30),
            connect_retry_interval_seconds=ConfigLoader._positive_int(
                value.get("connect_retry_interval_seconds", 2), 2
            ),
            auto_start_recording_on_game_launch=bool(value.get("auto_start_recording_on_game_launch", False)),
            auto_stop_recording_on_game_exit=bool(value.get("auto_stop_recording_on_game_exit", False)),
        )

    @staticmethod
    def _parse_login_bonus(value: object) -> LoginBonusConfig:
        if not isinstance(value, dict):
            return LoginBonusConfig()
        reset_time = ConfigLoader._parse_reset_time(value.get("reset_time", "05:00"))
        default_claimed = ConfigLoader._parse_patterns(value.get("claimed_patterns", []))
        default_unclaimed = ConfigLoader._parse_patterns(value.get("unclaimed_patterns", []))
        return LoginBonusConfig(
            enabled=bool(value.get("enabled", False)),
            reset_time=reset_time,
            game_screen=ConfigLoader._parse_login_bonus_source(
                value.get("game_screen", {}),
                default_claimed,
                default_unclaimed,
                300,
            ),
            web=ConfigLoader._parse_login_bonus_source(
                value.get("web", {}),
                default_claimed,
                default_unclaimed,
                30,
            ),
        )

    @staticmethod
    def _parse_login_bonus_source(
        value: object,
        default_claimed: tuple[str, ...],
        default_unclaimed: tuple[str, ...],
        default_timeout: int,
    ) -> LoginBonusSourceConfig:
        if not isinstance(value, dict):
            value = {}
        claimed_patterns = ConfigLoader._parse_patterns(value.get("claimed_patterns", [])) or default_claimed
        unclaimed_patterns = ConfigLoader._parse_patterns(value.get("unclaimed_patterns", [])) or default_unclaimed
        return LoginBonusSourceConfig(
            enabled=bool(value.get("enabled", False)),
            window_title=str(value.get("window_title", "")).strip(),
            url=str(value.get("url", "")).strip(),
            claimed_patterns=claimed_patterns,
            unclaimed_patterns=unclaimed_patterns,
            timeout_seconds=ConfigLoader._positive_int(value.get("timeout_seconds", default_timeout), default_timeout),
            retry_interval_seconds=ConfigLoader._positive_int(value.get("retry_interval_seconds", 5), 5),
            ocr_languages=str(value.get("ocr_languages", "jpn+eng")).strip() or "jpn+eng",
        )

    @staticmethod
    def _parse_patterns(value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return ()
        patterns: list[str] = []
        for item in value:
            pattern = str(item).strip()
            if pattern:
                patterns.append(pattern)
        return tuple(patterns)

    @staticmethod
    def _parse_reset_time(value: object) -> str:
        text = str(value).strip()
        if not re.fullmatch(r"\d{1,2}:\d{2}", text):
            return "05:00"
        hour_text, minute_text = text.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
        return "05:00"

    @staticmethod
    def _clamp_float(value: object, minimum: float, maximum: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = maximum
        return max(minimum, min(maximum, number))

    @staticmethod
    def _positive_int(value: object, default: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return default
        return number if number > 0 else default
