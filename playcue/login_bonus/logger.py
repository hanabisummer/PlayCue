from __future__ import annotations

import csv
from datetime import date, datetime, timedelta

from playcue.config.loader import ConfigLoader
from playcue.models import GameConfig
from playcue.paths import app_base_dir, login_bonus_history_file

_BASE_DIR = app_base_dir()
LOGIN_BONUS_LOG_FILE = login_bonus_history_file()


class LoginBonusLogger:
    HEADER = [
        "checked_at",
        "bonus_date",
        "game_name",
        "source",
        "status",
        "method",
        "evidence",
        "manual",
        "config_file",
    ]

    @staticmethod
    def bonus_date(now: datetime, reset_time: str) -> date:
        hour_text, minute_text = ConfigLoader._parse_reset_time(reset_time).split(":", 1)
        reset_at = now.replace(hour=int(hour_text), minute=int(minute_text), second=0, microsecond=0)
        if now < reset_at:
            return now.date() - timedelta(days=1)
        return now.date()

    def save(
        self,
        config: GameConfig,
        source: str,
        status: str,
        evidence: str = "",
        method: str = "manual",
        manual: bool = False,
    ) -> None:
        if status not in {"claimed", "unclaimed"}:
            return
        LOGIN_BONUS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        exists = LOGIN_BONUS_LOG_FILE.exists()
        now = datetime.now()
        bonus_date = self.bonus_date(now, config.login_bonus.reset_time)
        with LOGIN_BONUS_LOG_FILE.open("a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(self.HEADER)
            writer.writerow(
                [
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                    bonus_date.isoformat(),
                    config.game_name,
                    source,
                    status,
                    method,
                    evidence[:120],
                    "1" if manual else "0",
                    str(config.config_file.relative_to(_BASE_DIR))
                    if config.config_file.is_relative_to(_BASE_DIR)
                    else str(config.config_file),
                ]
            )

    def latest(self, config: GameConfig, source: str) -> dict[str, str] | None:
        if not LOGIN_BONUS_LOG_FILE.exists():
            return None
        today_bonus_date = self.bonus_date(datetime.now(), config.login_bonus.reset_time).isoformat()
        latest_row: dict[str, str] | None = None
        try:
            with LOGIN_BONUS_LOG_FILE.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    if (
                        (row.get("game_name") or "") == config.game_name
                        and (row.get("source") or "") == source
                        and (row.get("bonus_date") or "") == today_bonus_date
                    ):
                        latest_row = dict(row)
        except OSError:
            return None
        return latest_row
