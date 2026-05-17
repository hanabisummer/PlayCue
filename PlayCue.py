from __future__ import annotations

import csv
import ctypes
import json
import os
import shlex
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, ttk
import tkinter as tk
import tkinter.font as tkfont

try:
    import pystray
except ImportError:  # pragma: no cover - optional tray support
    pystray = None

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - optional tray support
    Image = None
    ImageDraw = None

try:
    import psutil
except ImportError:  # pragma: no cover - runtime fallback
    psutil = None

try:
    from obsws_python import ReqClient
except ImportError:  # pragma: no cover - runtime fallback
    ReqClient = None


BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "configs"
LOG_FILE = BASE_DIR / "logs" / "play_history.csv"
SUMMARY_FILE = BASE_DIR / "logs" / "play_time_summary.csv"
ELEVATED_FLAG = "--elevated"
SW_HIDE = 0
SW_SHOW = 5
STARTUP_TASK_NAME = "PlayCue"
UI_LANGUAGE = "ja"


TEXT = {
    "ja": {
        "app_title": "PlayCue",
        "waiting": "待機中",
        "playing": "プレイ中: {game_name}",
        "game_list_title": "ゲーム一覧（直近プレイ時間）",
        "play_time": "プレイ時間: {time}",
        "start_recording": "録画開始",
        "stop_recording": "録画停止",
        "links": "リンク",
        "start_recent": "直近にプレイしたゲームを起動",
        "reset_time": "現在のプレイ時間をリセット",
        "always_on_top": "最前面: {state}",
        "opacity": "透明度",
        "close": "閉じる",
        "settings": "設定",
        "add_game": "ゲーム追加",
        "edit_game": "ゲーム設定変更",
        "obs_settings": "OBS設定",
        "startup": "PC起動時に自動起動",
        "terminal": "ターミナル表示",
        "language": "言語",
        "summary": "集計",
        "days": "{days}日",
        "recent_summary_title": "直近{days}日プレイ時間",
        "total": "累計",
        "last_end_time": "前回終了時刻",
        "game_name": "ゲーム名",
        "game_exe_path": "ゲームexeパス",
        "browse": " 参照",
        "process_name": "プロセス名",
        "detect": " 検知",
        "display_name": "表示名",
        "url": "URL",
        "auto_launch": "自動起動",
        "add_link": " リンク追加",
        "remove_link": "削除",
        "create": " 作成",
        "update": " 更新",
        "select_game_to_edit": "変更するゲームを選択",
        "delete_game": "ゲーム削除",
        "select_game_to_delete": "削除するゲームを選択",
        "open": " 開く",
        "obs_exe_path": "OBS exeパス",
        "websocket": "Websocket",
        "server_host": "サーバーホスト",
        "server_port": "サーバーポート",
        "server_password": "サーバーパスワード",
        "update_settings": " 設定更新",
        "show": "表示",
        "exit": "終了",
        "not_recorded": "記録なし",
        "csv": "CSV",
    },
    "en": {
        "app_title": "PlayCue",
        "waiting": "Waiting",
        "playing": "Playing: {game_name}",
        "game_list_title": "Games (Last Play Time)",
        "play_time": "Play Time: {time}",
        "start_recording": "Start Recording",
        "stop_recording": "Stop Recording",
        "links": "Links",
        "start_recent": "Start Last Played Game",
        "reset_time": "Reset Current Play Time",
        "always_on_top": "Always On Top: {state}",
        "opacity": "Opacity",
        "close": "Close",
        "settings": "Settings",
        "add_game": "Add Game",
        "edit_game": "Edit Game Settings",
        "obs_settings": "OBS Settings",
        "startup": "Start with Windows",
        "terminal": "Show Terminal",
        "language": "Language",
        "summary": "Summary",
        "days": "{days} days",
        "recent_summary_title": "Last {days} Days Play Time",
        "total": "Total",
        "last_end_time": "Last End Time",
        "game_name": "Game Name",
        "game_exe_path": "Game exe Path",
        "browse": " Browse",
        "process_name": "Process Name",
        "detect": " Detect",
        "display_name": "Display Name",
        "url": "URL",
        "auto_launch": "Auto Launch",
        "add_link": " Add Link",
        "remove_link": "Delete",
        "create": " Create",
        "update": " Update",
        "select_game_to_edit": "Select a game to edit",
        "delete_game": "Delete Game",
        "select_game_to_delete": "Select a game to delete",
        "open": " Open",
        "obs_exe_path": "OBS exe Path",
        "websocket": "Websocket",
        "server_host": "Server Host",
        "server_port": "Server Port",
        "server_password": "Server Password",
        "update_settings": " Update Settings",
        "show": "Show",
        "exit": "Exit",
        "not_recorded": "No record",
        "csv": "CSV",
    },
}


OBS_STATUS_TEXT = {
    "OBS: 無効": {"ja": "OBS: 無効", "en": "OBS: Disabled"},
    "OBS: 未起動": {"ja": "OBS: 未起動", "en": "OBS: Not running"},
    "OBS: 起動済み": {"ja": "OBS: 起動済み", "en": "OBS: Running"},
    "OBS: 起動中": {"ja": "OBS: 起動中", "en": "OBS: Starting"},
    "OBS: 接続待ち": {"ja": "OBS: 接続待ち", "en": "OBS: Connecting"},
    "OBS: 録画中": {"ja": "OBS: 録画中", "en": "OBS: Recording"},
    "OBS: 接続済み": {"ja": "OBS: 接続済み", "en": "OBS: Connected"},
    "OBS: 準備待ち": {"ja": "OBS: 準備待ち", "en": "OBS: Waiting"},
    "OBS: 未接続": {"ja": "OBS: 未接続", "en": "OBS: Disconnected"},
    "OBS: 録画準備待ち": {"ja": "OBS: 録画準備待ち", "en": "OBS: Recording not ready"},
    "OBS: エラー": {"ja": "OBS: エラー", "en": "OBS: Error"},
}


def tr(key: str, **kwargs) -> str:
    text = TEXT.get(UI_LANGUAGE, TEXT["ja"]).get(key, TEXT["ja"].get(key, key))
    return text.format(**kwargs)


def obs_status_text(status: str) -> str:
    return OBS_STATUS_TEXT.get(status, {}).get(UI_LANGUAGE, status)


@dataclass(frozen=True)
class LinkItem:
    name: str
    url: str


@dataclass(frozen=True)
class OBSConfig:
    enabled: bool = False
    auto_launch: bool = False
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
    process_name: str = ""
    auto_close_on_game_exit: bool = False
    obs: OBSConfig = OBSConfig()
    auto_open_links: tuple[LinkItem, ...] = ()
    buttons: tuple[LinkItem, ...] = ()
    always_on_top: bool = True
    opacity: float = 0.9
    window_width: int = 360
    window_height: int = 420


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
            process_name=str(data.get("process_name", "")).strip(),
            auto_close_on_game_exit=bool(data.get("auto_close_on_game_exit", False)),
            obs=ConfigLoader._parse_obs(data.get("obs", {})),
            auto_open_links=ConfigLoader._parse_links(data.get("auto_open_links", [])),
            buttons=ConfigLoader._parse_links(data.get("buttons", [])),
            always_on_top=bool(data.get("always_on_top", True)),
            opacity=ConfigLoader._clamp_float(data.get("opacity", 0.9), 0.3, 1.0),
            window_width=ConfigLoader._positive_int(data.get("window_width", 360), 360),
            window_height=ConfigLoader._positive_int(data.get("window_height", 420), 420),
        )

    @staticmethod
    def list_configs(config_dir: Path = CONFIG_DIR) -> list[GameConfig]:
        configs: list[GameConfig] = []
        for path in sorted(config_dir.glob("*.json")):
            configs.append(ConfigLoader.load(path))
        return configs

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


class GameLauncher:
    def launch_game(self, config: GameConfig) -> None:
        if not config.game_exe:
            return

        game_path = Path(config.game_exe)
        if not game_path.exists():
            messagebox.showerror("ゲーム起動エラー", f"exeが見つかりません:\n{config.game_exe}")
            return

        try:
            args = shlex.split(config.game_args, posix=False) if config.game_args else []
            subprocess.Popen([config.game_exe, *args], cwd=str(game_path.parent))
        except OSError as exc:
            messagebox.showerror("ゲーム起動エラー", f"{config.game_name} の起動に失敗しました:\n{exc}")

    def open_links(self, links: tuple[LinkItem, ...]) -> None:
        for link in links:
            self.open_link(link)

    def open_link(self, link: LinkItem) -> None:
        try:
            if link.url.lower().startswith(("http://", "https://")):
                webbrowser.open(link.url)
                return
            if not Path(link.url).exists():
                messagebox.showerror("リンクエラー", f"ファイルが見つかりません:\n{link.url}")
                return
            os.startfile(link.url)  # type: ignore[attr-defined]
        except OSError as exc:
            messagebox.showerror("リンクエラー", f"{link.name} を開けませんでした:\n{exc}")


class OBSController:
    def __init__(self, config: OBSConfig):
        self.config = config
        self.client = None
        self.status = "OBS: 無効"
        self.recording_started_by_app = False
        if config.enabled:
            self.status = "OBS: 未起動"

    def prepare(self, launch_as_admin: bool = False, show_window: bool = False) -> None:
        if not self.config.enabled:
            return
        if self.config.auto_launch:
            self.launch_obs(launch_as_admin=launch_as_admin, show_window=show_window)
        self.connect()

    def launch_obs(self, launch_as_admin: bool = False, show_window: bool = False) -> None:
        if self._is_obs_running():
            self.status = "OBS: 起動済み"
            return

        if not self.config.exe_path:
            self._set_error("OBS exe_path が未設定です。")
            return
        exe_path = Path(self.config.exe_path)
        if not exe_path.exists():
            self._set_error(f"OBS exeが見つかりません:\n{self.config.exe_path}")
            return

        try:
            self.status = "OBS: 起動中"
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
        except OSError as exc:
            self._set_error(f"OBSの起動に失敗しました:\n{exc}")

    def connect(self) -> bool:
        if not self.config.enabled:
            return False
        if ReqClient is None:
            self._set_error("obsws-python が未インストールのため、OBS連携を無効化します。")
            return False

        self.status = "OBS: 接続待ち"
        deadline = time.monotonic() + self.config.connect_timeout_seconds
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
                self.status = "OBS: 録画中" if self.is_recording() else "OBS: 接続済み"
                return True
            except Exception as exc:  # obsws-python raises multiple connection/auth errors
                last_error = exc
                time.sleep(self.config.connect_retry_interval_seconds)

        self._set_error(f"OBS WebSocketへ接続できませんでした:\n{last_error}")
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
                self.status = "OBS: 準備待ち"
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
            self.status = "OBS: 未接続"
            return False

    def poll_status(self) -> bool:
        if not self.config.enabled:
            self.status = "OBS: 無効"
            return False
        if self.client is None and not self.reconnect_once():
            self.status = "OBS: 未接続"
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
            self.status = "OBS: 未接続"
            return False
        try:
            response = self.client.get_record_status()
            is_recording = bool(getattr(response, "output_active", getattr(response, "outputActive", False)))
            self.status = "OBS: 録画中" if is_recording else "OBS: 接続済み"
            return True
        except Exception:
            self.client = None
            self.status = "OBS: 未接続"
            return False

    def start_recording(self, show_errors: bool = True) -> bool:
        if not self.config.enabled:
            self.status = "OBS: 無効"
            return False
        if self.client is None and not self.connect():
            return False
        if self.is_recording():
            self.status = "OBS: 録画中"
            return True

        deadline = time.monotonic() + self.config.connect_timeout_seconds
        last_error: Exception | None = None
        while time.monotonic() <= deadline:
            try:
                self.client.start_record()
                self.recording_started_by_app = True
                self.status = "OBS: 録画中"
                return True
            except Exception as exc:
                last_error = exc
                self.status = "OBS: 録画準備待ち"
                time.sleep(self.config.connect_retry_interval_seconds)
        self.status = "OBS: エラー"
        if show_errors:
            messagebox.showerror("OBS録画エラー", f"録画開始に失敗しました:\n{last_error}")
        return False

    def stop_recording(self, only_if_started_by_app: bool = False, show_errors: bool = True) -> bool:
        if not self.config.enabled:
            self.status = "OBS: 無効"
            return False
        if only_if_started_by_app and not self.recording_started_by_app:
            return False
        if self.client is None and not self.connect():
            return False
        if not self.is_recording():
            self.status = "OBS: 接続済み"
            self.recording_started_by_app = False
            return True

        try:
            self.client.stop_record()
            self.recording_started_by_app = False
            self.status = "OBS: 接続済み"
            return True
        except Exception as exc:
            self.status = "OBS: エラー"
            if show_errors:
                messagebox.showerror("OBS録画エラー", f"録画停止に失敗しました:\n{exc}")
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

    def _set_error(self, message: str) -> None:
        self.status = "OBS: エラー"
        messagebox.showerror("OBSエラー", message)


class GameProcessWatcher:
    def __init__(
        self,
        process_name: str,
        on_exit,
        grace_seconds: int = 45,
        missing_threshold: int = 2,
        exe_path: str = "",
        on_process_name_detected=None,
    ):
        self.process_name = process_name.lower()
        self.on_exit = on_exit
        self.grace_seconds = grace_seconds
        self.missing_threshold = missing_threshold
        self.exe_path = str(Path(exe_path).resolve()).lower() if exe_path else ""
        self.on_process_name_detected = on_process_name_detected
        self.started_at = time.monotonic()
        self.missing_count = 0
        self.seen_process = False
        self.stopped = False

    def tick(self) -> None:
        if self.stopped or not self.process_name or psutil is None:
            return

        if self._is_running():
            self.seen_process = True
            self.missing_count = 0
            return

        if not self.seen_process and time.monotonic() - self.started_at < self.grace_seconds:
            return

        self.missing_count += 1
        if self.missing_count >= self.missing_threshold:
            self.stopped = True
            self.on_exit()

    def _is_running(self) -> bool:
        assert psutil is not None
        for proc in psutil.process_iter(["name", "exe"]):
            try:
                proc_name = proc.info.get("name") or ""
                if proc_name.lower() == self.process_name:
                    return True
                proc_exe = proc.info.get("exe") or ""
                if self.exe_path and proc_exe and str(Path(proc_exe).resolve()).lower() == self.exe_path:
                    detected_name = proc_name.strip()
                    if detected_name and detected_name.lower() != self.process_name:
                        self.process_name = detected_name.lower()
                        if self.on_process_name_detected:
                            self.on_process_name_detected(detected_name)
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                continue
        return False


class PlayTimeLogger:
    HEADER = [
        "session_start",
        "session_end",
        "date",
        "game_name",
        "elapsed_seconds",
        "elapsed_hhmmss",
        "config_file",
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
                    else str(config.config_file),
                ]
            )


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


def config_filename(game_name: str) -> str:
    safe_name = "".join(ch.lower() if ch.isalnum() else "_" for ch in game_name).strip("_")
    return f"{safe_name or 'game'}.json"


class ConsoleController:
    visible = True

    @staticmethod
    def set_visible(visible: bool) -> None:
        if os.name != "nt":
            return
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW if visible else SW_HIDE)
            ConsoleController.visible = visible

    @staticmethod
    def toggle() -> None:
        ConsoleController.set_visible(not ConsoleController.visible)


class StartupTaskController:
    @staticmethod
    def is_enabled() -> bool:
        if os.name != "nt":
            return False
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", STARTUP_TASK_NAME],
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
                    STARTUP_TASK_NAME,
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
                ["schtasks", "/Delete", "/TN", STARTUP_TASK_NAME, "/F"],
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
        return subprocess.list2cmdline([sys.executable, str(Path(__file__).resolve())])


class ConfigWizard:
    MAX_EXPANDED_LINK_ROWS = 2

    def __init__(self, parent: Tk, base_obs: OBSConfig, on_saved, config: GameConfig | None = None):
        self.parent = parent
        self.base_obs = base_obs
        self.on_saved = on_saved
        self.config = config
        self.window = tk.Toplevel(parent)
        self.window.title(tr("add_game") if config is None else tr("edit_game"))
        self.check_font = tkfont.nametofont("TkDefaultFont").copy()
        self.check_font.configure(size=self.check_font.cget("size") + 1)
        self.game_name_var = tk.StringVar()
        self.exe_path_var = tk.StringVar()
        self.process_name_var = tk.StringVar()
        self.link_rows: list[tuple[tk.StringVar, tk.StringVar, tk.BooleanVar, ttk.Frame]] = []
        self.links_frame: ttk.Frame | None = None
        self.links_body: ttk.Frame | None = None
        self.links_canvas: tk.Canvas | None = None
        self._build_ui()
        self._load_config(config)
        self._fit_window_to_screen(600, 520)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=tr("game_name")).pack(anchor=tk.W)
        ttk.Entry(frame, textvariable=self.game_name_var).pack(fill=tk.X, pady=(0, 8))

        ttk.Label(frame, text=tr("game_exe_path")).pack(anchor=tk.W)
        exe_frame = ttk.Frame(frame)
        exe_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Entry(exe_frame, textvariable=self.exe_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(exe_frame, text=tr("browse"), anchor=tk.W, command=self.browse_exe).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(frame, text=tr("process_name")).pack(anchor=tk.W)
        process_frame = ttk.Frame(frame)
        process_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Entry(process_frame, textvariable=self.process_name_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(process_frame, text=tr("detect"), anchor=tk.W, command=self.detect_process_name).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(frame, text=tr("links")).pack(anchor=tk.W)
        self.links_frame = ttk.Frame(frame)
        self.links_frame.pack(fill=tk.X, expand=False)
        self.links_canvas = tk.Canvas(self.links_frame, height=88, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.links_frame, orient=tk.VERTICAL, command=self.links_canvas.yview)
        self.links_body = ttk.Frame(self.links_canvas)
        self.links_body.bind("<Configure>", lambda _e: self.links_canvas.configure(scrollregion=self.links_canvas.bbox("all")))
        link_window = self.links_canvas.create_window((0, 0), window=self.links_body, anchor="nw")
        self.links_canvas.bind("<Configure>", lambda e: self.links_canvas.itemconfigure(link_window, width=e.width))
        self.links_canvas.bind("<Enter>", self._bind_links_mousewheel)
        self.links_canvas.bind("<Leave>", self._unbind_links_mousewheel)
        self.links_body.bind("<Enter>", self._bind_links_mousewheel)
        self.links_body.bind("<Leave>", self._unbind_links_mousewheel)
        self.links_canvas.configure(yscrollcommand=scrollbar.set)
        self.links_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        if self.config is None:
            self.add_link_row()

        button_frame = ttk.Frame(frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))
        tk.Button(button_frame, text=tr("add_link"), anchor=tk.W, command=lambda: self.add_link_row()).pack(
            fill=tk.X, pady=(0, 8)
        )
        action_text = tr("update") if self.config is not None else tr("create")
        tk.Button(button_frame, text=action_text, anchor=tk.W, command=self.save_config).pack(fill=tk.X)

    def browse_exe(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.window,
            title="ゲームexeを選択",
            filetypes=[("実行ファイル", "*.exe"), ("すべてのファイル", "*.*")],
        )
        if not path:
            return
        self.exe_path_var.set(path)
        self.process_name_var.set(Path(path).name)

    def add_link_row(self, name: str = "", url: str = "", auto_launch: bool = False) -> None:
        if self.links_body is None:
            return
        name_var = tk.StringVar(value=name)
        url_var = tk.StringVar(value=url)
        auto_launch_var = tk.BooleanVar(value=auto_launch)
        row = ttk.Frame(self.links_body)
        row.pack(fill=tk.X, pady=(0, 8))
        top_row = ttk.Frame(row)
        top_row.pack(fill=tk.X, pady=(0, 2))
        top_row.columnconfigure(1, weight=1)
        ttk.Label(top_row, text=tr("display_name"), width=10).grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        ttk.Entry(top_row, textvariable=name_var).grid(row=0, column=1, sticky=tk.EW, padx=(0, 8))
        tk.Checkbutton(
            top_row,
            text=tr("auto_launch"),
            variable=auto_launch_var,
            onvalue=True,
            offvalue=False,
            font=self.check_font,
            padx=4,
            pady=2,
        ).grid(
            row=0, column=2, sticky=tk.E
        )
        tk.Button(top_row, text=tr("remove_link"), command=lambda item=row: self.remove_link_row(item)).grid(
            row=0, column=3, sticky=tk.E, padx=(8, 0)
        )
        url_row = ttk.Frame(row)
        url_row.pack(fill=tk.X)
        url_row.columnconfigure(1, weight=1)
        ttk.Label(url_row, text=tr("url"), width=10).grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        ttk.Entry(url_row, textvariable=url_var).grid(row=0, column=1, sticky=tk.EW)
        self.link_rows.append((name_var, url_var, auto_launch_var, row))
        self._resize_links_canvas()
        if len(self.link_rows) > self.MAX_EXPANDED_LINK_ROWS:
            self.links_canvas.yview_moveto(1.0)
        self._fit_window_to_screen(max(600, self.window.winfo_width()), self.window.winfo_height())

    def remove_link_row(self, row: ttk.Frame) -> None:
        self.link_rows = [item for item in self.link_rows if item[3] is not row]
        row.destroy()
        if not self.link_rows:
            self.add_link_row()
            return
        self._resize_links_canvas()
        self._fit_window_to_screen(max(600, self.window.winfo_width()), self.window.winfo_height())

    def _bind_links_mousewheel(self, _event: tk.Event) -> None:
        if self.links_canvas is None:
            return
        self.links_canvas.bind_all("<MouseWheel>", self._scroll_links)

    def _unbind_links_mousewheel(self, _event: tk.Event) -> None:
        if self.links_canvas is None:
            return
        self.links_canvas.unbind_all("<MouseWheel>")

    def _scroll_links(self, event: tk.Event) -> str:
        if self.links_canvas is not None and event.delta:
            self.links_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _resize_links_canvas(self) -> None:
        if self.links_canvas is None:
            return
        self.window.update_idletasks()
        row_height = 88
        if self.links_body is not None:
            children = self.links_body.winfo_children()
            if children:
                row_height = max(row_height, max(child.winfo_reqheight() for child in children) + 8)
        visible_rows = min(max(1, len(self.link_rows)), self.MAX_EXPANDED_LINK_ROWS)
        height = row_height * visible_rows
        self.links_canvas.configure(height=height)

    def _load_config(self, config: GameConfig | None) -> None:
        if config is None:
            return
        self.game_name_var.set(config.game_name)
        self.exe_path_var.set(config.game_exe)
        self.process_name_var.set(config.process_name)
        auto_link_keys = {(link.name, link.url) for link in config.auto_open_links}
        loaded_link_keys: set[tuple[str, str]] = set()
        for link in config.buttons:
            link_key = (link.name, link.url)
            self.add_link_row(link.name, link.url, link_key in auto_link_keys)
            loaded_link_keys.add(link_key)
        for link in config.auto_open_links:
            link_key = (link.name, link.url)
            if link_key not in loaded_link_keys:
                self.add_link_row(link.name, link.url, True)
        if not self.link_rows:
            self.add_link_row()

    def _fit_window_to_screen(self, width: int, height: int) -> None:
        self.window.update_idletasks()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        requested_width = self.window.winfo_reqwidth()
        requested_height = self.window.winfo_reqheight()
        fitted_width = min(max(360, int(width), requested_width), screen_width)
        fitted_height = min(max(260, int(height), requested_height), max(260, screen_height - 80))
        parent_right = self.parent.winfo_rootx() + self.parent.winfo_width()
        if parent_right + 20 + fitted_width <= screen_width:
            x = parent_right + 20
        else:
            x = max(0, self.parent.winfo_rootx() - fitted_width - 20)
        y = max(0, min(self.parent.winfo_rooty(), screen_height - fitted_height))
        self.window.geometry(f"{fitted_width}x{fitted_height}+{x}+{y}")

    def detect_process_name(self) -> None:
        detected_name = self._detect_process_name()
        if detected_name:
            self.process_name_var.set(detected_name)
            messagebox.showinfo("プロセス検知", f"検知しました: {detected_name}", parent=self.window)
            return
        messagebox.showwarning("プロセス検知", "実行中の同一exeプロセスを検知できませんでした。", parent=self.window)

    def _detect_process_name(self) -> str:
        exe_path = self.exe_path_var.get().strip()
        if not exe_path or psutil is None:
            return ""
        target = str(Path(exe_path).resolve()).lower()
        for proc in psutil.process_iter(["name", "exe"]):
            try:
                proc_exe = proc.info.get("exe") or ""
                if proc_exe and str(Path(proc_exe).resolve()).lower() == target:
                    return (proc.info.get("name") or "").strip()
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                continue
        return ""

    def save_config(self) -> None:
        game_name = self.game_name_var.get().strip()
        exe_path = self.exe_path_var.get().strip()
        if not game_name:
            messagebox.showwarning("入力エラー", "ゲーム名を入力してください。", parent=self.window)
            return
        if not exe_path or not Path(exe_path).exists():
            messagebox.showwarning("入力エラー", "存在するゲームexeパスを入力してください。", parent=self.window)
            return

        process_name = self.process_name_var.get().strip() or Path(exe_path).name
        links = []
        auto_open_links = []
        for name, url, auto_launch, _row in self.link_rows:
            link = {"name": name.get().strip(), "url": url.get().strip()}
            if not link["name"] or not link["url"]:
                continue
            links.append(link)
            if auto_launch.get():
                auto_open_links.append(link)
        if self.config is None:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            config_path = CONFIG_DIR / config_filename(game_name)
            suffix = 2
            while config_path.exists():
                config_path = CONFIG_DIR / f"{Path(config_filename(game_name)).stem}_{suffix}.json"
                suffix += 1
        else:
            config_path = self.config.config_file

        data = {
            "game_name": game_name,
            "game_exe": exe_path,
            "game_args": "",
            "process_name": process_name,
            "auto_close_on_game_exit": False,
            "obs": obs_config_to_dict(self.config.obs if self.config is not None else self.base_obs),
            "auto_open_links": auto_open_links,
            "buttons": links,
            "always_on_top": self.config.always_on_top if self.config is not None else True,
            "opacity": self.config.opacity if self.config is not None else 0.9,
            "window_width": self.config.window_width if self.config is not None else 360,
            "window_height": self.config.window_height if self.config is not None else 420,
        }
        try:
            with config_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.on_saved(ConfigLoader.load(config_path))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("作成エラー", str(exc), parent=self.window)
            return
        self.window.destroy()


class OBSSettingsWindow:
    def __init__(self, parent: Tk, config: OBSConfig, on_saved):
        self.parent = parent
        self.config = config
        self.on_saved = on_saved
        self.window = tk.Toplevel(parent)
        self.window.title(tr("obs_settings"))
        self.exe_path_var = tk.StringVar(value=config.exe_path)
        self.process_name_var = tk.StringVar(value=config.process_name)
        self.websocket_host_var = tk.StringVar(value=config.websocket_host or "127.0.0.1")
        self.websocket_port_var = tk.StringVar(value=str(config.websocket_port))
        self.websocket_password_var = tk.StringVar(value=config.websocket_password)
        self._build_ui()
        self._fit_window_to_screen(520, 360)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=tr("obs_exe_path")).pack(anchor=tk.W)
        exe_frame = ttk.Frame(frame)
        exe_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Entry(exe_frame, textvariable=self.exe_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(exe_frame, text=tr("browse"), anchor=tk.W, command=self.browse_exe).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(frame, text=tr("process_name")).pack(anchor=tk.W)
        ttk.Entry(frame, textvariable=self.process_name_var).pack(fill=tk.X, pady=(0, 10))

        websocket_frame = ttk.LabelFrame(frame, text=tr("websocket"))
        websocket_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(websocket_frame, text=tr("server_host")).pack(anchor=tk.W, padx=6, pady=(6, 0))
        ttk.Entry(websocket_frame, textvariable=self.websocket_host_var).pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Label(websocket_frame, text=tr("server_port")).pack(anchor=tk.W, padx=6)
        ttk.Entry(websocket_frame, textvariable=self.websocket_port_var).pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Label(websocket_frame, text=tr("server_password")).pack(anchor=tk.W, padx=6)
        ttk.Entry(websocket_frame, textvariable=self.websocket_password_var, show="*").pack(
            fill=tk.X, padx=6, pady=(0, 6)
        )

        tk.Button(frame, text=tr("update_settings"), anchor=tk.W, command=self.save).pack(fill=tk.X)

    def browse_exe(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.window,
            title="OBS exeを選択",
            filetypes=[("実行ファイル", "*.exe"), ("すべてのファイル", "*.*")],
        )
        if not path:
            return
        self.exe_path_var.set(path)
        self.process_name_var.set(Path(path).name)

    def save(self) -> None:
        exe_path = self.exe_path_var.get().strip()
        process_name = self.process_name_var.get().strip() or Path(exe_path).name
        host = self.websocket_host_var.get().strip() or "127.0.0.1"
        try:
            port = int(self.websocket_port_var.get().strip())
        except ValueError:
            messagebox.showwarning("入力エラー", "サーバーポートは数値で入力してください。", parent=self.window)
            return
        if port <= 0:
            messagebox.showwarning("入力エラー", "サーバーポートは1以上で入力してください。", parent=self.window)
            return
        if exe_path and not Path(exe_path).exists():
            messagebox.showwarning("入力エラー", "存在するOBS exeパスを入力してください。", parent=self.window)
            return

        updated = replace(
            self.config,
            exe_path=exe_path,
            working_dir=str(Path(exe_path).parent) if exe_path else self.config.working_dir,
            process_name=process_name,
            websocket_host=host,
            websocket_port=port,
            websocket_password=self.websocket_password_var.get(),
        )
        try:
            self.on_saved(updated)
        except OSError as exc:
            messagebox.showerror("更新エラー", str(exc), parent=self.window)
            return
        self.window.destroy()

    def _fit_window_to_screen(self, width: int, height: int) -> None:
        self.window.update_idletasks()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        fitted_width = min(max(360, int(width), self.window.winfo_reqwidth()), screen_width)
        fitted_height = min(max(260, int(height), self.window.winfo_reqheight()), max(260, screen_height - 80))
        parent_right = self.parent.winfo_rootx() + self.parent.winfo_width()
        if parent_right + 20 + fitted_width <= screen_width:
            x = parent_right + 20
        else:
            x = max(0, self.parent.winfo_rootx() - fitted_width - 20)
        y = max(0, min(self.parent.winfo_rooty(), screen_height - fitted_height))
        self.window.geometry(f"{fitted_width}x{fitted_height}+{x}+{y}")


class ResidentPlayCueApp:
    def __init__(self, root: Tk, configs: list[GameConfig]):
        self.root = root
        self.configs = configs
        self.config: GameConfig | None = None
        self.obs_controller = OBSController(configs[0].obs)
        self.launcher = GameLauncher()
        self.logger = PlayTimeLogger()
        self.session_start = datetime.now()
        self.elapsed_before_run = 0.0
        self.run_started_at = 0.0
        self.paused = True
        self.log_saved = True
        self.watcher: GameProcessWatcher | None = None
        self.closed = False
        self.tray_icon = None
        self.tray_available = pystray is not None and Image is not None and ImageDraw is not None
        first_config = configs[0]

        self.topmost = first_config.always_on_top
        self.time_var = tk.StringVar(value=tr("play_time", time="00:00:00"))
        self.current_game_var = tk.StringVar(value=tr("waiting"))
        self.obs_status_var = tk.StringVar(value=obs_status_text(self.obs_controller.status))
        self.pause_var = tk.StringVar(value=tr("start_recent"))
        self.topmost_var = tk.StringVar()
        self.ui_title_label: ttk.Label | None = None
        self.opacity_label: ttk.Label | None = None
        self.close_button: ttk.Button | None = None
        self.terminal_visible_var = tk.BooleanVar(value=False)
        self.startup_enabled_var = tk.BooleanVar(value=StartupTaskController.is_enabled())
        self.opacity_var = tk.DoubleVar(value=first_config.opacity)
        self.game_list_frame: ttk.LabelFrame | None = None
        self.game_list_canvas: tk.Canvas | None = None
        self.game_list_body: ttk.Frame | None = None
        self.link_frame: ttk.LabelFrame | None = None
        self.link_canvas: tk.Canvas | None = None
        self.link_body: ttk.Frame | None = None
        self.obs_controls: ttk.Frame | None = None
        self.recording_start_button: ttk.Button | None = None
        self.recording_stop_button: ttk.Button | None = None
        self.reset_button: ttk.Button | None = None
        self.game_button_vars: dict[str, tk.StringVar] = {}
        default_font = tkfont.nametofont("TkDefaultFont")
        self.ui_font = default_font
        self.title_font = default_font.copy()
        self.title_font.configure(weight="bold")
        self.button_font = tkfont.nametofont("TkTextFont")

        self._build_ui(first_config)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Unmap>", self._on_unmap)
        self.root.attributes("-topmost", self.topmost)
        self.root.attributes("-alpha", first_config.opacity)
        self._fit_window_to_screen(first_config.window_width, first_config.window_height)
        self._update_topmost_label()
        self._update_timer()
        self._monitor_obs_status()
        self.root.after(100, self.prepare_obs_on_startup)

    def _build_ui(self, first_config: GameConfig) -> None:
        self.root.title(tr("app_title"))
        self._build_menu()

        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        self.ui_title_label = ttk.Label(outer, text=tr("app_title"), font=self.title_font)
        self.ui_title_label.pack(anchor=tk.W)
        ttk.Label(outer, textvariable=self.current_game_var, font=self.ui_font).pack(anchor=tk.W, pady=(2, 8))

        self.game_list_frame = ttk.LabelFrame(outer, text=tr("game_list_title"))
        self.game_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        list_canvas = tk.Canvas(self.game_list_frame, height=126, highlightthickness=0)
        self.game_list_canvas = list_canvas
        list_scrollbar = ttk.Scrollbar(self.game_list_frame, orient=tk.VERTICAL, command=list_canvas.yview)
        self.game_list_body = ttk.Frame(list_canvas)
        self.game_list_body.bind("<Configure>", lambda _e: list_canvas.configure(scrollregion=list_canvas.bbox("all")))
        list_window = list_canvas.create_window((0, 0), window=self.game_list_body, anchor="nw")
        list_canvas.bind("<Configure>", lambda e: list_canvas.itemconfigure(list_window, width=e.width))
        list_canvas.bind("<Enter>", lambda _e: list_canvas.bind_all("<MouseWheel>", self._scroll_game_list))
        list_canvas.bind("<Leave>", lambda _e: list_canvas.unbind_all("<MouseWheel>"))
        list_canvas.configure(yscrollcommand=list_scrollbar.set)
        list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        for config in self._sorted_configs_by_recent_play():
            self._add_game_button(config)

        self.time_label = ttk.Label(outer, textvariable=self.time_var, font=self.title_font)
        self.time_label.pack(pady=(0, 8), anchor=tk.W)

        obs_frame = ttk.Frame(outer)
        obs_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(obs_frame, textvariable=self.obs_status_var, font=self.ui_font).pack(anchor=tk.W)
        self.obs_controls = ttk.Frame(obs_frame)
        self.obs_controls.pack(fill=tk.X, pady=(3, 0))
        self.recording_start_button = ttk.Button(self.obs_controls, text=tr("start_recording"), command=self.start_recording)
        self.recording_start_button.pack(
            side=tk.LEFT, expand=True, fill=tk.X
        )
        self.recording_stop_button = ttk.Button(self.obs_controls, text=tr("stop_recording"), command=self.stop_recording)
        self.recording_stop_button.pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(6, 0)
        )

        self.link_frame = ttk.LabelFrame(outer, text=tr("links"))
        self.link_frame.pack(fill=tk.X, expand=False, pady=(0, 8))
        canvas = tk.Canvas(self.link_frame, height=1, highlightthickness=0)
        self.link_canvas = canvas
        scrollbar = ttk.Scrollbar(self.link_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.link_body = ttk.Frame(canvas)
        self.link_body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.link_body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        controls = ttk.Frame(outer)
        controls.pack(fill=tk.X)
        ttk.Button(controls, textvariable=self.pause_var, command=self.start_recent_game).pack(
            fill=tk.X
        )
        self.reset_button = ttk.Button(controls, text=tr("reset_time"), command=self.reset_timer)

        ttk.Button(outer, textvariable=self.topmost_var, command=self.toggle_topmost).pack(fill=tk.X, pady=(8, 4))
        self.opacity_label = ttk.Label(outer, text=tr("opacity"), font=self.ui_font)
        self.opacity_label.pack(anchor=tk.W)
        ttk.Scale(outer, from_=0.3, to=1.0, variable=self.opacity_var, command=self.change_opacity).pack(fill=tk.X)
        self.close_button = ttk.Button(outer, text=tr("close"), command=self.close)
        self.close_button.pack(fill=tk.X, pady=(10, 0))

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)
        settings_menu = tk.Menu(menu_bar, tearoff=False)
        language_menu = tk.Menu(settings_menu, tearoff=False)
        language_menu.add_command(label="日本語", command=lambda: self.set_language("ja"))
        language_menu.add_command(label="English", command=lambda: self.set_language("en"))
        settings_menu.add_cascade(label=tr("language"), menu=language_menu)
        settings_menu.add_command(label=tr("add_game"), command=self.open_config_wizard)
        settings_menu.add_command(label=tr("edit_game"), command=self.open_config_editor_selector)
        settings_menu.add_command(label=tr("delete_game"), command=self.open_config_delete_selector)
        settings_menu.add_command(label=tr("obs_settings"), command=self.open_obs_settings)
        settings_menu.add_checkbutton(
            label=tr("startup"),
            variable=self.startup_enabled_var,
            command=self.toggle_startup,
        )
        settings_menu.add_checkbutton(
            label=tr("terminal"),
            variable=self.terminal_visible_var,
            command=self.toggle_terminal,
        )
        menu_bar.add_cascade(label=tr("settings"), menu=settings_menu)

        summary_menu = tk.Menu(menu_bar, tearoff=False)
        for days in (1, 7, 30):
            summary_menu.add_command(label=tr("days", days=days), command=lambda value=days: self.show_summary(value))
        summary_menu.add_command(label=tr("total"), command=self.show_total_summary)
        menu_bar.add_cascade(label=tr("summary"), menu=summary_menu)
        menu_bar.add_command(label=tr("last_end_time"), command=self.show_last_end_times)
        self.root.config(menu=menu_bar)

    def set_language(self, language: str) -> None:
        global UI_LANGUAGE
        UI_LANGUAGE = language
        self._refresh_ui_language()

    def _refresh_ui_language(self) -> None:
        self.root.title(tr("app_title") if self.config is None else f"{self.config.game_name} - {tr('app_title')}")
        self._build_menu()
        if self.ui_title_label is not None:
            self.ui_title_label.configure(text=tr("app_title"))
        if self.game_list_frame is not None:
            self.game_list_frame.configure(text=tr("game_list_title"))
        if self.recording_start_button is not None:
            self.recording_start_button.configure(text=tr("start_recording"))
        if self.recording_stop_button is not None:
            self.recording_stop_button.configure(text=tr("stop_recording"))
        if self.link_frame is not None:
            self.link_frame.configure(text=tr("links"))
        if self.reset_button is not None:
            self.reset_button.configure(text=tr("reset_time"))
        if self.opacity_label is not None:
            self.opacity_label.configure(text=tr("opacity"))
        if self.close_button is not None:
            self.close_button.configure(text=tr("close"))
        self.pause_var.set(tr("start_recent"))
        self.current_game_var.set(tr("waiting") if self.config is None else tr("playing", game_name=self.config.game_name))
        self._update_topmost_label()
        self.time_var.set(tr("play_time", time=PlayTimeLogger.format_hhmmss(self.current_elapsed_seconds())))
        self._update_obs_status()

    def _add_game_button(self, config: GameConfig) -> None:
        if self.game_list_body is None:
            return
        button_var = tk.StringVar(value=self._game_list_text(config))
        self.game_button_vars[config.game_name] = button_var
        button = tk.Button(
            self.game_list_body,
            textvariable=button_var,
            anchor=tk.W,
            font=self.button_font,
            padx=6,
            pady=4,
            command=lambda item=config: self.start_game(item),
        )
        button.bind("<MouseWheel>", self._scroll_game_list)
        button.pack(fill=tk.X, padx=3, pady=3)

    def open_config_wizard(self) -> None:
        base_obs = self.configs[0].obs if self.configs else self.obs_controller.config
        ConfigWizard(self.root, base_obs, self.add_config)

    def add_config(self, config: GameConfig) -> None:
        self.configs.append(config)
        self._rebuild_game_list()

    def open_config_editor_selector(self) -> None:
        selector = tk.Toplevel(self.root)
        selector.title(tr("edit_game"))
        selector.geometry("320x260")
        frame = ttk.Frame(selector, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text=tr("select_game_to_edit")).pack(anchor=tk.W, pady=(0, 8))
        listbox = tk.Listbox(frame, height=8)
        listbox.pack(fill=tk.BOTH, expand=True)
        for config in self.configs:
            listbox.insert(tk.END, config.game_name)
        if self.configs:
            listbox.selection_set(0)

        def open_selected() -> None:
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("選択エラー", "ゲームを選択してください。", parent=selector)
                return
            config = self.configs[selection[0]]
            selector.destroy()
            ConfigWizard(self.root, config.obs, self.update_config, config=config)

        tk.Button(frame, text=tr("open"), anchor=tk.W, command=open_selected).pack(fill=tk.X, pady=(8, 0))
        listbox.bind("<Double-Button-1>", lambda _e: open_selected())

    def open_config_delete_selector(self) -> None:
        selector = tk.Toplevel(self.root)
        selector.title(tr("delete_game"))
        selector.geometry("320x260")
        frame = ttk.Frame(selector, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text=tr("select_game_to_delete")).pack(anchor=tk.W, pady=(0, 8))
        listbox = tk.Listbox(frame, height=8)
        listbox.pack(fill=tk.BOTH, expand=True)
        for config in self.configs:
            listbox.insert(tk.END, config.game_name)
        if self.configs:
            listbox.selection_set(0)

        def delete_selected() -> None:
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("選択エラー", "ゲームを選択してください。", parent=selector)
                return
            config = self.configs[selection[0]]
            if self.config is not None and self.config.config_file == config.config_file:
                messagebox.showwarning("削除エラー", "プレイ中のゲームは削除できません。", parent=selector)
                return
            if not messagebox.askyesno(tr("delete_game"), f"{config.game_name} の設定ファイルを削除しますか？", parent=selector):
                return
            try:
                if config.config_file.exists():
                    config.config_file.unlink()
            except OSError as exc:
                messagebox.showerror("削除エラー", str(exc), parent=selector)
                return
            self.configs = [item for item in self.configs if item.config_file != config.config_file]
            self._rebuild_game_list()
            selector.destroy()

        tk.Button(frame, text=tr("delete_game"), anchor=tk.W, command=delete_selected).pack(fill=tk.X, pady=(8, 0))
        listbox.bind("<Double-Button-1>", lambda _e: delete_selected())

    def update_config(self, config: GameConfig) -> None:
        for index, existing in enumerate(self.configs):
            if existing.config_file == config.config_file:
                self.configs[index] = config
                break
        else:
            self.configs.append(config)
        self._rebuild_game_list()

    def open_obs_settings(self) -> None:
        OBSSettingsWindow(self.root, self.obs_controller.config, self.update_obs_settings)

    def update_obs_settings(self, obs_config: OBSConfig) -> None:
        for config in self.configs:
            with config.config_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            current_obs = data.get("obs", {})
            if not isinstance(current_obs, dict):
                current_obs = {}
            current_obs.update(
                {
                    "exe_path": obs_config.exe_path,
                    "working_dir": obs_config.working_dir,
                    "process_name": obs_config.process_name,
                    "websocket_host": obs_config.websocket_host,
                    "websocket_port": obs_config.websocket_port,
                    "websocket_password": obs_config.websocket_password,
                }
            )
            data["obs"] = current_obs
            with config.config_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        self.configs = [ConfigLoader.load(config.config_file) for config in self.configs]
        self.obs_controller = OBSController(obs_config)
        self.obs_status_var.set(self.obs_controller.status)

    def toggle_terminal(self) -> None:
        ConsoleController.set_visible(bool(self.terminal_visible_var.get()))

    def toggle_startup(self) -> None:
        enabled = bool(self.startup_enabled_var.get())
        try:
            StartupTaskController.set_enabled(enabled)
        except OSError as exc:
            self.startup_enabled_var.set(not enabled)
            messagebox.showerror("自動起動設定エラー", str(exc))

    def prepare_obs_on_startup(self) -> None:
        self.obs_controller.prepare(launch_as_admin=True, show_window=True)
        self._update_obs_status()
        self._update_obs_controls()

    def _monitor_obs_status(self) -> None:
        if self.closed:
            return
        self.obs_controller.poll_status()
        self._update_obs_status()
        self._update_obs_controls()
        self.root.after(5000, self._monitor_obs_status)

    def _update_obs_controls(self) -> None:
        if self.obs_controls is None:
            return
        is_recording = self.obs_controller.status == "OBS: 録画中"
        is_connected = self.obs_controller.status == "OBS: 接続済み"
        if self.recording_start_button is not None:
            if is_connected and not self.recording_start_button.winfo_ismapped():
                self.recording_start_button.pack(side=tk.LEFT, expand=True, fill=tk.X)
            elif not is_connected:
                self.recording_start_button.pack_forget()
        if self.recording_stop_button is not None:
            if is_recording and not self.recording_stop_button.winfo_ismapped():
                self.recording_stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(6, 0))
            elif not is_recording:
                self.recording_stop_button.pack_forget()

    def start_recent_game(self) -> None:
        if self.config is not None:
            messagebox.showwarning("ゲーム実行中", f"{self.config.game_name} をプレイ中です。")
            return
        configs = self._sorted_configs_by_recent_play()
        if not configs:
            return
        self.start_game(configs[0])

    def _scroll_game_list(self, event) -> str:
        if self.game_list_canvas is None:
            return "break"
        delta = -1 if event.delta > 0 else 1
        self.game_list_canvas.yview_scroll(delta, "units")
        return "break"

    def start_game(self, config: GameConfig) -> None:
        if self.config is not None:
            messagebox.showwarning("ゲーム実行中", f"{self.config.game_name} をプレイ中です。")
            return

        self.config = config
        self.obs_status_var.set(self.obs_controller.status)
        self.session_start = datetime.now()
        self.elapsed_before_run = 0.0
        self.run_started_at = time.monotonic()
        self.paused = False
        self.log_saved = False
        self.current_game_var.set(tr("playing", game_name=config.game_name))
        if self.reset_button is not None and not self.reset_button.winfo_ismapped():
            self.reset_button.pack(fill=tk.X, pady=(6, 0))
        self.root.title(f"{config.game_name} - {tr('app_title')}")
        self._fit_window_to_screen(config.window_width, config.window_height)
        self.root.attributes("-alpha", config.opacity)
        self.opacity_var.set(config.opacity)
        self._set_waiting_ui(False)
        self._refresh_links()
        self._fit_window_to_screen(config.window_width, config.window_height)

        self.launcher.launch_game(config)
        if config.obs.auto_start_recording_on_game_launch:
            self.obs_controller.start_recording()
            self._update_obs_status()
        self.launcher.open_links(config.auto_open_links)
        self._start_watcher(config)

    def _start_watcher(self, config: GameConfig) -> None:
        if not config.process_name:
            return
        if psutil is None:
            messagebox.showwarning("監視無効", "psutil が未インストールのため、ゲーム終了検知を無効化します。")
            return
        self.watcher = GameProcessWatcher(
            config.process_name,
            self.on_game_exit,
            exe_path=config.game_exe,
            on_process_name_detected=lambda process_name: self._update_config_process_name(config, process_name),
        )
        self._watch_process()

    def _update_config_process_name(self, config: GameConfig, process_name: str) -> None:
        try:
            with config.config_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            data["process_name"] = process_name
            with config.config_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except (OSError, json.JSONDecodeError):
            return

    def _watch_process(self) -> None:
        if self.closed:
            return
        watcher = self.watcher
        if watcher is None:
            return
        watcher.tick()
        if self.watcher is watcher and not watcher.stopped:
            self.root.after(5000, self._watch_process)

    def _refresh_links(self) -> None:
        if self.link_body is None:
            return
        for child in self.link_body.winfo_children():
            child.destroy()
        if self.config is None:
            self._set_link_area_expanded(False)
            return
        has_links = bool(self.config.buttons)
        for link in self.config.buttons:
            ttk.Button(self.link_body, text=link.name, command=lambda item=link: self.launcher.open_link(item)).pack(
                fill=tk.X, padx=4, pady=3
            )
        self._set_link_area_expanded(has_links)

    def _set_link_area_expanded(self, expanded: bool) -> None:
        if self.link_frame is None or self.link_canvas is None:
            return
        self.link_canvas.configure(height=120 if expanded else 1)
        self.link_frame.pack_configure(fill=tk.BOTH if expanded else tk.X, expand=expanded)

    def _set_waiting_ui(self, waiting: bool) -> None:
        if self.game_list_frame is None:
            return
        if waiting:
            self.game_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8), before=self.time_label)
        else:
            self.game_list_frame.pack_forget()

    def current_elapsed_seconds(self) -> int:
        elapsed = self.elapsed_before_run
        if not self.paused:
            elapsed += time.monotonic() - self.run_started_at
        return int(elapsed)

    def _update_timer(self) -> None:
        if self.closed:
            return
        self.time_var.set(tr("play_time", time=PlayTimeLogger.format_hhmmss(self.current_elapsed_seconds())))
        self.root.after(1000, self._update_timer)

    def toggle_pause(self) -> None:
        if self.config is None:
            return
        if self.paused:
            self.paused = False
            self.run_started_at = time.monotonic()
            self.pause_var.set("一時停止")
            return
        self.elapsed_before_run = float(self.current_elapsed_seconds())
        self.paused = True
        self.pause_var.set("再開")

    def reset_timer(self) -> None:
        if self.config is None:
            return
        self.session_start = datetime.now()
        self.elapsed_before_run = 0.0
        self.run_started_at = time.monotonic()
        self.time_var.set(tr("play_time", time="00:00:00"))

    def on_game_exit(self) -> None:
        self.stop_recording_for_game_exit()
        self.save_log_once()
        self.config = None
        self.watcher = None
        self.session_start = datetime.now()
        self.elapsed_before_run = 0.0
        self.run_started_at = 0.0
        self.paused = True
        self.log_saved = True
        self.current_game_var.set(tr("waiting"))
        self.pause_var.set(tr("start_recent"))
        if self.reset_button is not None:
            self.reset_button.pack_forget()
        self.obs_status_var.set(self.obs_controller.status)
        self._refresh_links()
        self._set_waiting_ui(True)
        self._refresh_game_list()
        self.root.title(tr("app_title"))
        self.time_var.set(tr("play_time", time="00:00:00"))
        self._fit_window_to_screen(self.root.winfo_width(), self.root.winfo_height())

    def _on_unmap(self, _event) -> None:
        if self.closed or self.root.state() != "iconic":
            return
        self.minimize_to_tray()

    def minimize_to_tray(self) -> None:
        if not self.tray_available:
            return
        self.root.withdraw()
        if self.tray_icon is not None:
            return
        image = Image.new("RGB", (64, 64), "white")
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, 56, 56), fill="#2f6fed")
        draw.rectangle((28, 16, 36, 48), fill="white")
        menu = pystray.Menu(
            pystray.MenuItem(tr("show"), lambda _icon, _item: self.root.after(0, self.restore_from_tray)),
            pystray.MenuItem(tr("exit"), lambda _icon, _item: self.root.after(0, self.close)),
        )
        self.tray_icon = pystray.Icon("PlayCue", image, tr("app_title"), menu)
        self.tray_icon.run_detached()

    def restore_from_tray(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _stop_tray_icon(self) -> None:
        if self.tray_icon is None:
            return
        self.tray_icon.stop()
        self.tray_icon = None

    def show_summary(self, days: int) -> None:
        totals = self._play_seconds_by_game(days)
        lines = [
            f"{game_name}: {PlayTimeLogger.format_hhmmss(totals.get(game_name, 0))}"
            for game_name in self._summary_game_names(totals)
        ]
        messagebox.showinfo(tr("recent_summary_title", days=days), "\n".join(lines))

    def show_total_summary(self) -> None:
        totals = self._play_seconds_by_game(None)
        csv_path = self._write_total_summary_csv()
        lines = [
            f"{game_name}: {PlayTimeLogger.format_hhmmss(totals.get(game_name, 0))}"
            for game_name in self._summary_game_names(totals)
        ]
        messagebox.showinfo(tr("total"), "\n".join([*lines, "", f"{tr('csv')}: {csv_path}"]))

    def show_last_end_times(self) -> None:
        last_end_times = self._last_end_time_by_game()
        lines = [
            f"{game_name}: {last_end_times.get(game_name, tr('not_recorded'))}"
            for game_name in self._summary_game_names(last_end_times)
        ]
        messagebox.showinfo(tr("last_end_time"), "\n".join(lines))

    def _refresh_game_list(self) -> None:
        for config in self.configs:
            button_var = self.game_button_vars.get(config.game_name)
            if button_var is not None:
                button_var.set(self._game_list_text(config))
        self._rebuild_game_list()

    def _rebuild_game_list(self) -> None:
        if self.game_list_body is None:
            return
        for child in self.game_list_body.winfo_children():
            child.destroy()
        self.game_button_vars.clear()
        for config in self._sorted_configs_by_recent_play():
            self._add_game_button(config)

    def _sorted_configs_by_recent_play(self) -> list[GameConfig]:
        last_end_times = self._last_end_datetime_by_game()
        return sorted(
            self.configs,
            key=lambda config: last_end_times.get(config.game_name, datetime.min),
            reverse=True,
        )

    def _game_list_text(self, config: GameConfig) -> str:
        seconds = self._last_play_seconds_by_game().get(config.game_name, 0)
        return f" {config.game_name} ({PlayTimeLogger.format_hhmmss(seconds)})"

    def _fit_window_to_screen(self, width: int, height: int) -> None:
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        requested_width = self.root.winfo_reqwidth()
        requested_height = self.root.winfo_reqheight()
        fitted_width = min(max(240, int(width), requested_width), screen_width)
        fitted_height = min(max(260, int(height), requested_height), max(260, screen_height - 80))
        x = max(0, screen_width - fitted_width - 20)
        y = max(0, min(20, screen_height - fitted_height))
        self.root.geometry(f"{fitted_width}x{fitted_height}+{x}+{y}")

    def _history_rows(self) -> list[dict[str, object]]:
        if not LOG_FILE.exists():
            return []
        rows: list[dict[str, object]] = []
        try:
            with LOG_FILE.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    game_name = (row.get("game_name") or "").strip()
                    session_end = self._parse_datetime(row.get("session_end") or "")
                    elapsed_seconds = self._parse_seconds(row.get("elapsed_seconds") or "")
                    if game_name and session_end is not None and elapsed_seconds is not None:
                        rows.append(
                            {
                                "game_name": game_name,
                                "session_end": session_end,
                                "elapsed_seconds": elapsed_seconds,
                            }
                        )
        except OSError:
            return []
        return rows

    def _last_end_time_by_game(self) -> dict[str, str]:
        latest = self._last_end_datetime_by_game()
        return {
            game_name: session_end.strftime("%Y-%m-%d %H:%M:%S")
            for game_name, session_end in latest.items()
        }

    def _last_end_datetime_by_game(self) -> dict[str, datetime]:
        latest: dict[str, datetime] = {}
        for row in self._history_rows():
            game_name = str(row["game_name"])
            session_end = row["session_end"]
            if not isinstance(session_end, datetime):
                continue
            if game_name not in latest or session_end > latest[game_name]:
                latest[game_name] = session_end
        return latest

    def _last_play_seconds_by_game(self) -> dict[str, int]:
        latest: dict[str, tuple[datetime, int]] = {}
        for row in self._history_rows():
            game_name = str(row["game_name"])
            session_end = row["session_end"]
            elapsed_seconds = int(row["elapsed_seconds"])
            if not isinstance(session_end, datetime):
                continue
            if game_name not in latest or session_end > latest[game_name][0]:
                latest[game_name] = (session_end, elapsed_seconds)
        return {game_name: seconds for game_name, (_session_end, seconds) in latest.items()}

    def _play_seconds_by_game(self, days: int | None) -> dict[str, int]:
        cutoff = datetime.now() - timedelta(days=days) if days is not None else None
        totals: dict[str, int] = {}
        for row in self._history_rows():
            session_end = row["session_end"]
            if isinstance(session_end, datetime) and (cutoff is None or session_end >= cutoff):
                game_name = str(row["game_name"])
                totals[game_name] = totals.get(game_name, 0) + int(row["elapsed_seconds"])
        if self.config is not None and (cutoff is None or self.session_start >= cutoff):
            totals[self.config.game_name] = totals.get(self.config.game_name, 0) + self.current_elapsed_seconds()
        return totals

    def _summary_game_names(self, values: dict[str, object] | None = None) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()
        for config in self.configs:
            if config.game_name not in seen:
                names.append(config.game_name)
                seen.add(config.game_name)
        for row in self._history_rows():
            game_name = str(row["game_name"])
            if game_name not in seen:
                names.append(game_name)
                seen.add(game_name)
        if values is not None:
            for game_name in values:
                if game_name not in seen:
                    names.append(game_name)
                    seen.add(game_name)
        return names

    def _write_total_summary_csv(self) -> Path:
        SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
        game_names = self._summary_game_names()
        rows_by_end_time: dict[datetime, dict[str, int]] = {}
        for row in self._history_rows():
            session_end = row["session_end"]
            if not isinstance(session_end, datetime):
                continue
            game_name = str(row["game_name"])
            end_time_row = rows_by_end_time.setdefault(session_end, {})
            end_time_row[game_name] = end_time_row.get(game_name, 0) + int(row["elapsed_seconds"])

        with SUMMARY_FILE.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["プレイ終了時刻", *game_names])
            for session_end in sorted(rows_by_end_time):
                values = [
                    PlayTimeLogger.format_hhmmss(rows_by_end_time[session_end].get(game_name, 0))
                    if game_name in rows_by_end_time[session_end]
                    else ""
                    for game_name in game_names
                ]
                writer.writerow([session_end.strftime("%Y-%m-%d %H:%M:%S"), *values])
        return SUMMARY_FILE

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    @staticmethod
    def _parse_seconds(value: str) -> int | None:
        try:
            return max(0, int(value))
        except ValueError:
            return None

    def start_recording(self) -> None:
        self.obs_controller.start_recording()
        self._update_obs_status()

    def stop_recording(self) -> None:
        self.obs_controller.stop_recording()
        self._update_obs_status()

    def stop_recording_for_game_exit(self) -> None:
        if self.config is not None and self.config.obs.auto_stop_recording_on_game_exit:
            self.obs_controller.stop_recording(only_if_started_by_app=True)
            self._update_obs_status()

    def _update_obs_status(self) -> None:
        self.obs_status_var.set(obs_status_text(self.obs_controller.status))

    def toggle_topmost(self) -> None:
        self.topmost = not self.topmost
        self.root.attributes("-topmost", self.topmost)
        self._update_topmost_label()

    def _update_topmost_label(self) -> None:
        self.topmost_var.set(tr("always_on_top", state="ON" if self.topmost else "OFF"))

    def change_opacity(self, _value: str) -> None:
        value = max(0.3, min(1.0, float(self.opacity_var.get())))
        self.root.attributes("-alpha", value)

    def close(self) -> None:
        if self.watcher:
            self.watcher.stopped = True
        self.save_log_once()
        self.root.destroy()

    def save_log_once(self) -> None:
        if self.config is None or self.log_saved:
            return
        try:
            self.logger.save(self.config, self.session_start, self.current_elapsed_seconds())
            self.log_saved = True
        except OSError as exc:
            messagebox.showerror("ログ保存エラー", f"プレイ履歴を保存できませんでした:\n{exc}")


def choose_config(configs: list[GameConfig]) -> GameConfig | None:
    selected: dict[str, GameConfig | None] = {"config": None}
    root = Tk()
    root.title("ゲーム選択")
    root.geometry("360x300")
    frame = ttk.Frame(root, padding=12)
    frame.pack(fill=tk.BOTH, expand=True)
    ttk.Label(frame, text="起動するゲームを選択してください").pack(anchor=tk.W, pady=(0, 8))
    listbox = tk.Listbox(frame, height=8)
    listbox.pack(fill=tk.BOTH, expand=True)
    for config in configs:
        listbox.insert(tk.END, config.game_name)
    if configs:
        listbox.selection_set(0)

    def start() -> None:
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("選択エラー", "ゲームを選択してください。")
            return
        selected["config"] = configs[selection[0]]
        root.destroy()

    ttk.Button(frame, text="起動", command=start).pack(fill=tk.X, pady=(10, 0))
    listbox.bind("<Double-Button-1>", lambda _e: start())
    root.mainloop()
    return selected["config"]


def resolve_config(argv: list[str]) -> GameConfig | None:
    args = [arg for arg in argv[1:] if arg != ELEVATED_FLAG]
    if args:
        return ConfigLoader.load((BASE_DIR / args[0]).resolve() if not Path(args[0]).is_absolute() else Path(args[0]))

    configs = ConfigLoader.list_configs()
    if not configs:
        raise FileNotFoundError(f"configs フォルダにJSON設定がありません: {CONFIG_DIR}")
    return choose_config(configs)


def resolve_configs(argv: list[str]) -> list[GameConfig]:
    args = [arg for arg in argv[1:] if arg != ELEVATED_FLAG]
    if args:
        config_path = (BASE_DIR / args[0]).resolve() if not Path(args[0]).is_absolute() else Path(args[0])
        return [ConfigLoader.load(config_path)]

    configs = ConfigLoader.list_configs()
    if not configs:
        raise FileNotFoundError(f"configs フォルダにJSON設定がありません: {CONFIG_DIR}")
    return configs


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def relaunch_as_admin() -> bool:
    if os.name != "nt" or is_admin() or ELEVATED_FLAG in sys.argv:
        return False

    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = subprocess.list2cmdline([*sys.argv[1:], ELEVATED_FLAG])
    else:
        executable = sys.executable
        script = str(Path(__file__).resolve())
        params = subprocess.list2cmdline([script, *sys.argv[1:], ELEVATED_FLAG])

    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, str(BASE_DIR), 1)
    if result <= 32:
        ctypes.windll.user32.MessageBoxW(
            None,
            "管理者権限での再起動に失敗したため終了します。",
            "管理者権限エラー",
            0x10,
        )
    return True


def main() -> int:
    if relaunch_as_admin():
        return 0
    ConsoleController.set_visible(False)

    try:
        configs = resolve_configs(sys.argv)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        root = Tk()
        root.withdraw()
        messagebox.showerror("設定エラー", str(exc))
        root.destroy()
        return 1

    root = Tk()
    ResidentPlayCueApp(root, configs)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
