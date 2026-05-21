from __future__ import annotations

import calendar
import csv
import ctypes
import ctypes.wintypes
import json
import os
import queue
import re
import shlex
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, ttk
import tkinter as tk
import tkinter.font as tkfont

try:
    import pystray
except ImportError:  # pragma: no cover - optional tray support
    pystray = None

try:
    from PIL import Image, ImageDraw, ImageGrab
except ImportError:  # pragma: no cover - optional tray support
    Image = None
    ImageDraw = None
    ImageGrab = None

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional OCR support
    pytesseract = None

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
LOGIN_BONUS_LOG_FILE = BASE_DIR / "logs" / "login_bonus_history.csv"
ELEVATED_FLAG = "--elevated"
SW_HIDE = 0
SW_SHOW = 5
STARTUP_TASK_NAME = "PlayCue"
UI_LANGUAGE = "ja"

THEME = {
    "bg": "#10141f",
    "panel": "#171d2b",
    "panel_alt": "#20283a",
    "text": "#edf3ff",
    "muted": "#9aa9c4",
    "accent": "#21d4fd",
    "accent_active": "#55e6ff",
    "danger": "#ff4d6d",
    "danger_active": "#ff7891",
    "border": "#31405c",
}


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
        "login_bonus": "ログインボーナス",
        "login_bonus_status": "{game}: {source} {status}",
        "login_bonus_game_check": "ゲーム画面を判定",
        "login_bonus_web_check": "Webを開いて判定",
        "login_bonus_manual_claimed": "取得済みにする",
        "login_bonus_manual_unclaimed": "未取得にする",
        "login_bonus_game_source": "ゲーム画面",
        "login_bonus_web_source": "Web",
        "login_bonus_disabled": "ログインボーナス設定なし",
        "login_bonus_claimed": "取得済み",
        "login_bonus_unclaimed": "未取得",
        "login_bonus_unknown": "未判定",
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
        "summary": "プレイ時間",
        "days": "{days}日",
        "recent_summary_title": "直近{days}日プレイ時間",
        "total": "累計",
        "last_end_time": "前回終了",
        "calendar": "カレンダー",
        "previous_month": "前月",
        "next_month": "翌月",
        "calendar_daily_title": "{date}のプレイ時間",
        "game_name": "ゲーム名",
        "game_exe_path": "ランチャーexe または ゲームexe の場所",
        "game_exe_note": "※ゲームランチャーが存在する場合は優先してランチャーの場所を入力。ない場合はゲームexeの場所を入力",
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
        "find_game_sites": "リンク自動検索",
        "searching_game_sites": "検索中...",
        "game_sites_title": "攻略サイト候補",
        "no_game_name_for_search": "ゲーム名を入力してください。",
        "no_game_sites_found": "追加できる候補が見つかりませんでした。",
        "add_selected_sites": "選択したリンクを追加",
        "game_site_search_failed": "攻略サイト候補を取得できませんでした:\n{error}",
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
        "login_bonus": "Login Bonus",
        "login_bonus_status": "{game}: {source} {status}",
        "login_bonus_game_check": "Check Game Screen",
        "login_bonus_web_check": "Open Web and Check",
        "login_bonus_manual_claimed": "Mark Claimed",
        "login_bonus_manual_unclaimed": "Mark Unclaimed",
        "login_bonus_game_source": "Game Screen",
        "login_bonus_web_source": "Web",
        "login_bonus_disabled": "No login bonus settings",
        "login_bonus_claimed": "Claimed",
        "login_bonus_unclaimed": "Unclaimed",
        "login_bonus_unknown": "Unknown",
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
        "summary": "Play Time",
        "days": "{days} days",
        "recent_summary_title": "Last {days} Days Play Time",
        "total": "Total",
        "last_end_time": "Last End",
        "calendar": "Calendar",
        "previous_month": "Previous",
        "next_month": "Next",
        "calendar_daily_title": "Play Time on {date}",
        "game_name": "Game Name",
        "game_exe_path": "Launcher exe or Game exe Path",
        "game_exe_note": "If the game has a launcher, enter the launcher path first. Otherwise, enter the game exe path.",
        "browse": " Browse",
        "process_name": "Process Name",
        "detect": " Detect",
        "display_name": "Display Name",
        "url": "URL",
        "auto_launch": "Auto Launch",
        "add_link": " Add Link",
        "find_game_sites": "Auto Search Links",
        "searching_game_sites": "Searching...",
        "game_sites_title": "Game Site Candidates",
        "no_game_name_for_search": "Enter a game name first.",
        "no_game_sites_found": "No new candidates were found.",
        "add_selected_sites": "Add Selected Links",
        "game_site_search_failed": "Could not fetch game site candidates:\n{error}",
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


class SearchResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[tuple[str, str]] = []
        self._href = ""
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        if not href:
            return
        self._href = href
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._href:
            return
        title = " ".join("".join(self._text_parts).split())
        if title:
            self.results.append((title, self._href))
        self._href = ""
        self._text_parts = []


class GameSiteSearcher:
    SEARCH_URL = "https://duckduckgo.com/html/"
    QUERY_SUFFIXES = ("攻略", "wiki", "guide")
    EXCLUDED_DOMAINS = (
        "duckduckgo.com",
        "google.com",
        "bing.com",
        "yahoo.co.jp",
        "youtube.com",
        "youtu.be",
        "x.com",
        "twitter.com",
        "facebook.com",
        "instagram.com",
    )
    GUIDE_DOMAINS = (
        "game8.jp",
        "gamewith.jp",
        "altema.jp",
        "appmedia.jp",
        "kamigame.jp",
        "wikiwiki.jp",
        "w.atwiki.jp",
        "pcgamingwiki.com",
        "fandom.com",
    )
    INFO_DOMAINS = (
        "4gamer.net",
        "famitsu.com",
        "gamespark.jp",
        "automaton-media.com",
        "dengekionline.com",
        "gamer.ne.jp",
        "inside-games.jp",
        "ign.com",
        "gamespot.com",
    )
    HIGH_TRAFFIC_DOMAINS = (
        "store.steampowered.com",
        "steamcommunity.com",
        "playstation.com",
        "xbox.com",
        "nintendo.com",
        "reddit.com",
        "metacritic.com",
    )
    OFFICIAL_LINKS = {
        "ff14": {
            "ja": LinkItem("FINAL FANTASY XIV The Lodestone", "https://jp.finalfantasyxiv.com/lodestone/"),
            "en": LinkItem("FINAL FANTASY XIV The Lodestone", "https://na.finalfantasyxiv.com/lodestone/"),
        },
        "ffxiv": {
            "ja": LinkItem("FINAL FANTASY XIV The Lodestone", "https://jp.finalfantasyxiv.com/lodestone/"),
            "en": LinkItem("FINAL FANTASY XIV The Lodestone", "https://na.finalfantasyxiv.com/lodestone/"),
        },
        "finalfantasyxiv": {
            "ja": LinkItem("FINAL FANTASY XIV The Lodestone", "https://jp.finalfantasyxiv.com/lodestone/"),
            "en": LinkItem("FINAL FANTASY XIV The Lodestone", "https://na.finalfantasyxiv.com/lodestone/"),
        },
        "finalfantasy14": {
            "ja": LinkItem("FINAL FANTASY XIV The Lodestone", "https://jp.finalfantasyxiv.com/lodestone/"),
            "en": LinkItem("FINAL FANTASY XIV The Lodestone", "https://na.finalfantasyxiv.com/lodestone/"),
        },
    }

    @classmethod
    def search(cls, game_title: str, max_results: int = 5) -> tuple[LinkItem, ...]:
        collected: list[tuple[int, int, LinkItem]] = []
        seen: set[str] = set()
        seen_sites: set[str] = set()
        order = 0
        for link in cls._known_official_links(game_title):
            key = cls.normalized_url_key(link.url)
            site_key = cls.site_key(link.url)
            seen.add(key)
            seen_sites.add(site_key)
            collected.append((10000 + cls._language_score(link), order, link))
            order += 1
        for suffix in cls.QUERY_SUFFIXES:
            html = cls._fetch_html(f"{game_title} {suffix}")
            for title, href in cls._parse_html(html):
                link = cls._to_link(title, href)
                if link is None:
                    continue
                key = cls.normalized_url_key(link.url)
                if key in seen:
                    continue
                site_key = cls.site_key(link.url)
                if site_key in seen_sites:
                    continue
                seen.add(key)
                seen_sites.add(site_key)
                collected.append((cls._score(link), order, link))
                order += 1
        collected.sort(key=lambda item: (-item[0], item[1]))
        return tuple(item[2] for item in collected[:max_results])

    @classmethod
    def links_from_html(cls, html: str, max_results: int = 5) -> tuple[LinkItem, ...]:
        collected: list[tuple[int, int, LinkItem]] = []
        seen: set[str] = set()
        seen_sites: set[str] = set()
        for order, (title, href) in enumerate(cls._parse_html(html)):
            link = cls._to_link(title, href)
            if link is None:
                continue
            key = cls.normalized_url_key(link.url)
            if key in seen:
                continue
            site_key = cls.site_key(link.url)
            if site_key in seen_sites:
                continue
            seen.add(key)
            seen_sites.add(site_key)
            collected.append((cls._score(link), order, link))
        collected.sort(key=lambda item: (-item[0], item[1]))
        return tuple(item[2] for item in collected[:max_results])

    @classmethod
    def normalized_url_key(cls, url: str) -> str:
        parsed = urllib.parse.urlparse(url.strip())
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parsed.path.rstrip("/")
        return urllib.parse.urlunparse((parsed.scheme.lower(), netloc, path, "", parsed.query, ""))

    @staticmethod
    def site_key(url: str) -> str:
        netloc = urllib.parse.urlparse(url.strip()).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc

    @classmethod
    def _fetch_html(cls, query: str) -> str:
        params = urllib.parse.urlencode({"q": query})
        request = urllib.request.Request(
            f"{cls.SEARCH_URL}?{params}",
            headers={"User-Agent": "Mozilla/5.0 PlayCue"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.read().decode("utf-8", errors="replace")

    @staticmethod
    def _parse_html(html: str) -> list[tuple[str, str]]:
        parser = SearchResultParser()
        parser.feed(html)
        return parser.results

    @classmethod
    def _to_link(cls, title: str, href: str) -> LinkItem | None:
        url = cls._unwrap_url(href)
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        domain = parsed.netloc.lower()
        if any(domain == excluded or domain.endswith(f".{excluded}") for excluded in cls.EXCLUDED_DOMAINS):
            return None
        name = cls._clean_title(title)
        if not name:
            return None
        return LinkItem(name=name, url=urllib.parse.urlunparse(parsed._replace(fragment="")))

    @staticmethod
    def _unwrap_url(href: str) -> str:
        if href.startswith("//"):
            href = f"https:{href}"
        elif href.startswith("/"):
            href = f"https://duckduckgo.com{href}"
        parsed = urllib.parse.urlparse(href)
        if parsed.netloc.lower().endswith("duckduckgo.com"):
            query = urllib.parse.parse_qs(parsed.query)
            if query.get("uddg"):
                return query["uddg"][0]
        return href

    @staticmethod
    def _clean_title(title: str) -> str:
        title = re.sub(r"\s+", " ", title).strip()
        return title[:80]

    @classmethod
    def _score(cls, link: LinkItem) -> int:
        domain = cls.site_key(link.url)
        text = f"{link.name} {link.url}".lower()
        if cls._looks_official_forum(domain, text):
            score = 4000
        elif cls._looks_official_site(domain, text):
            score = 5000
        elif cls._domain_matches(domain, cls.GUIDE_DOMAINS):
            score = 3000
        elif cls._domain_matches(domain, cls.INFO_DOMAINS):
            score = 2000
        elif cls._domain_matches(domain, cls.HIGH_TRAFFIC_DOMAINS):
            score = 1000
        else:
            score = 0
        if any(keyword in text for keyword in ("攻略", "wiki", "guide", "walkthrough")):
            score += 100
        if any(keyword in text for keyword in ("official", "公式")):
            score += 50
        score += cls._language_score(link)
        return score

    @classmethod
    def _known_official_links(cls, game_title: str) -> tuple[LinkItem, ...]:
        key = re.sub(r"[^a-z0-9]+", "", game_title.lower())
        links = cls.OFFICIAL_LINKS.get(key)
        if not links:
            return ()
        return (links.get(UI_LANGUAGE) or links["en"],)

    @staticmethod
    def _language_score(link: LinkItem) -> int:
        parsed = urllib.parse.urlparse(link.url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        text = f"{link.name} {link.url}".lower()
        japanese = (
            domain.endswith(".jp")
            or domain.startswith(("jp.", "ja."))
            or "/jp/" in path
            or "/ja/" in path
            or any(keyword in text for keyword in ("日本", "公式", "攻略"))
        )
        english = (
            domain.startswith(("en.", "na.", "us."))
            or "/en/" in path
            or "/na/" in path
            or "/us/" in path
            or any(keyword in text for keyword in ("english", "official", "guide", "wiki"))
        )
        if UI_LANGUAGE == "ja":
            return 300 if japanese else -100 if english and not japanese else 0
        return 300 if english and not japanese else -100 if japanese else 0

    @staticmethod
    def _domain_matches(domain: str, domains: tuple[str, ...]) -> bool:
        return any(domain == item or domain.endswith(f".{item}") for item in domains)

    @staticmethod
    def _looks_official_forum(domain: str, text: str) -> bool:
        has_forum = any(keyword in text for keyword in ("forum", "forums", "community", "フォーラム"))
        has_official = any(keyword in text for keyword in ("official", "公式"))
        return has_forum and (has_official or domain.startswith(("forum.", "forums.", "community.")))

    @classmethod
    def _looks_official_site(cls, domain: str, text: str) -> bool:
        if cls._domain_matches(domain, cls.GUIDE_DOMAINS + cls.INFO_DOMAINS + cls.HIGH_TRAFFIC_DOMAINS):
            return False
        if any(keyword in text for keyword in ("forum", "forums", "community", "フォーラム")):
            return False
        return any(keyword in text for keyword in ("official site", "official website", "公式サイト", "公式ホームページ"))


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
    auto_close_on_game_exit: bool = False
    obs: OBSConfig = OBSConfig()
    login_bonus: LoginBonusConfig = LoginBonusConfig()
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
            launch_unelevated=bool(data.get("launch_unelevated", False)),
            process_name=str(data.get("process_name", "")).strip(),
            active_process_name=str(data.get("active_process_name", "")).strip(),
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
            if config.launch_unelevated and os.name == "nt" and is_admin() and not args:
                subprocess.Popen(["explorer.exe", str(game_path)])
                return
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

    def prepare(
        self,
        launch_as_admin: bool = False,
        show_window: bool = False,
        show_errors: bool = True,
        connect_timeout_seconds: int | None = None,
    ) -> None:
        if not self.config.enabled:
            return
        if self.config.auto_launch:
            self.launch_obs(launch_as_admin=launch_as_admin, show_window=show_window, show_errors=show_errors)
        self.connect(show_errors=show_errors, timeout_seconds=connect_timeout_seconds)

    def launch_obs(self, launch_as_admin: bool = False, show_window: bool = False, show_errors: bool = True) -> None:
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

    def connect(self, show_errors: bool = True, timeout_seconds: int | None = None) -> bool:
        if not self.config.enabled:
            return False
        if ReqClient is None:
            self._set_error("obsws-python が未インストールのため、OBS連携を無効化します。")
            return False

        self.status = "OBS: 接続待ち"
        timeout = self.config.connect_timeout_seconds if timeout_seconds is None else max(1, timeout_seconds)
        deadline = time.monotonic() + timeout
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
        if threading.current_thread() is threading.main_thread():
            messagebox.showerror('OBSエラー', message)


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
            self.seen_process = True
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
                    str(config.config_file.relative_to(BASE_DIR))
                    if config.config_file.is_relative_to(BASE_DIR)
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


class LoginBonusChecker:
    _ocr_available: bool | None = None

    def check(self, config: GameConfig, source_name: str) -> tuple[str, str, str]:
        source = self._source_config(config, source_name)
        if source is None or not config.login_bonus.enabled or not source.enabled:
            return "unknown", "", "disabled"
        text, method = self._read_source_text(source)
        if not text:
            return "unknown", "", method
        return self._match_text(text, source)

    @staticmethod
    def _source_config(config: GameConfig, source_name: str) -> LoginBonusSourceConfig | None:
        if source_name == "game_screen":
            return config.login_bonus.game_screen
        if source_name == "web":
            return config.login_bonus.web
        return None

    @staticmethod
    def _match_text(text: str, source: LoginBonusSourceConfig) -> tuple[str, str, str]:
        lowered = text.lower()
        for pattern in source.claimed_patterns:
            if pattern.lower() in lowered:
                return "claimed", pattern, "ocr"
        for pattern in source.unclaimed_patterns:
            if pattern.lower() in lowered:
                return "unclaimed", pattern, "ocr"
        return "unknown", text[:120], "ocr"

    def _read_source_text(self, source: LoginBonusSourceConfig) -> tuple[str, str]:
        if not self.is_ocr_available():
            return "", "ocr_unavailable"
        bbox = self._window_bbox(source.window_title)
        if bbox is None:
            return "", "window_not_found"
        try:
            image = ImageGrab.grab(bbox=bbox)
            text = pytesseract.image_to_string(image, lang=source.ocr_languages)
        except Exception:
            return "", "ocr_error"
        return text, "ocr"

    @classmethod
    def is_ocr_available(cls) -> bool:
        if pytesseract is None or ImageGrab is None:
            return False
        if cls._ocr_available is not None:
            return cls._ocr_available
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            cls._ocr_available = False
        else:
            cls._ocr_available = True
        return cls._ocr_available

    def _window_bbox(self, window_title: str) -> tuple[int, int, int, int] | None:
        if os.name != "nt":
            return None
        hwnd = self._find_window(window_title)
        if not hwnd:
            return None
        rect = ctypes.wintypes.RECT()
        if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        if rect.right <= rect.left or rect.bottom <= rect.top:
            return None
        return rect.left, rect.top, rect.right, rect.bottom

    def _find_window(self, window_title: str) -> int:
        user32 = ctypes.windll.user32
        if not window_title:
            return int(user32.GetForegroundWindow())
        needle = window_title.lower()
        matches: list[int] = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def enum_proc(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if needle in buffer.value.lower():
                matches.append(int(hwnd))
                return False
            return True

        user32.EnumWindows(enum_proc, 0)
        return matches[0] if matches else 0


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
        self.site_search_button: tk.Button | None = None
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
        ttk.Label(frame, text=tr("game_exe_note"), wraplength=560).pack(anchor=tk.W, pady=(0, 8))

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
        self.site_search_button = tk.Button(
            button_frame,
            text=tr("find_game_sites"),
            anchor=tk.W,
            command=self.find_game_sites,
        )
        self.site_search_button.pack(fill=tk.X, pady=(0, 8))
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

    def find_game_sites(self) -> None:
        game_title = self.game_name_var.get().strip()
        if not game_title:
            messagebox.showwarning(tr("game_sites_title"), tr("no_game_name_for_search"), parent=self.window)
            return
        if self.site_search_button is not None:
            self.site_search_button.configure(state=tk.DISABLED, text=tr("searching_game_sites"))
        result_queue: queue.Queue[tuple[tuple[LinkItem, ...], Exception | None]] = queue.Queue()

        def worker() -> None:
            try:
                links = GameSiteSearcher.search(game_title)
                result_queue.put((links, None))
            except Exception as exc:
                result_queue.put(((), exc))

        def poll_result() -> None:
            try:
                links, error = result_queue.get_nowait()
            except queue.Empty:
                if self.window.winfo_exists():
                    self.window.after(100, poll_result)
                return
            self._finish_game_site_search(links, error)

        threading.Thread(target=worker, daemon=True).start()
        self.window.after(100, poll_result)

    def _finish_game_site_search(self, links: tuple[LinkItem, ...], error: Exception | None) -> None:
        if self.site_search_button is not None:
            self.site_search_button.configure(state=tk.NORMAL, text=tr("find_game_sites"))
        if error is not None:
            messagebox.showerror(
                tr("game_sites_title"),
                tr("game_site_search_failed", error=str(error)),
                parent=self.window,
            )
            return
        existing_urls = self._existing_link_url_keys()
        existing_sites = self._existing_link_site_keys()
        candidates = tuple(
            link
            for link in links
            if GameSiteSearcher.normalized_url_key(link.url) not in existing_urls
            and GameSiteSearcher.site_key(link.url) not in existing_sites
        )
        if not candidates:
            messagebox.showinfo(tr("game_sites_title"), tr("no_game_sites_found"), parent=self.window)
            return
        self._show_game_site_candidates(candidates)

    def _existing_link_url_keys(self) -> set[str]:
        urls: set[str] = set()
        for _name_var, url_var, _auto_launch_var, _row in self.link_rows:
            url = url_var.get().strip()
            if url:
                urls.add(GameSiteSearcher.normalized_url_key(url))
        return urls

    def _existing_link_site_keys(self) -> set[str]:
        sites: set[str] = set()
        for _name_var, url_var, _auto_launch_var, _row in self.link_rows:
            url = url_var.get().strip()
            if url:
                sites.add(GameSiteSearcher.site_key(url))
        return sites

    def _show_game_site_candidates(self, links: tuple[LinkItem, ...]) -> None:
        dialog = tk.Toplevel(self.window)
        dialog.title(tr("game_sites_title"))
        dialog.transient(self.window)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        choices: list[tuple[tk.BooleanVar, LinkItem]] = []
        for link in links:
            checked = tk.BooleanVar(value=True)
            choices.append((checked, link))
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=(0, 8))
            tk.Checkbutton(row, variable=checked, onvalue=True, offvalue=False).pack(side=tk.LEFT)
            text = f"{link.name}\n{link.url}"
            ttk.Label(row, text=text, wraplength=520).pack(side=tk.LEFT, fill=tk.X, expand=True)

        def add_selected() -> None:
            added = False
            existing_urls = self._existing_link_url_keys()
            existing_sites = self._existing_link_site_keys()
            for checked, link in choices:
                key = GameSiteSearcher.normalized_url_key(link.url)
                site_key = GameSiteSearcher.site_key(link.url)
                if checked.get() and key not in existing_urls and site_key not in existing_sites:
                    self.add_link_row(link.name, link.url)
                    existing_urls.add(key)
                    existing_sites.add(site_key)
                    added = True
            dialog.destroy()
            if not added:
                messagebox.showinfo(tr("game_sites_title"), tr("no_game_sites_found"), parent=self.window)

        tk.Button(frame, text=tr("add_selected_sites"), anchor=tk.W, command=add_selected).pack(fill=tk.X)
        self._fit_child_window_to_screen(dialog, 600, 360)

    def _fit_child_window_to_screen(self, window: tk.Toplevel, width: int, height: int) -> None:
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        fitted_width = min(max(360, width, window.winfo_reqwidth()), screen_width)
        fitted_height = min(max(220, height, window.winfo_reqheight()), max(220, screen_height - 80))
        x = max(0, min(self.window.winfo_rootx() + 20, screen_width - fitted_width))
        y = max(0, min(self.window.winfo_rooty() + 20, screen_height - fitted_height))
        window.geometry(f"{fitted_width}x{fitted_height}+{x}+{y}")

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
            "launch_unelevated": self.config.launch_unelevated if self.config is not None else False,
            "process_name": process_name,
            "active_process_name": self.config.active_process_name if self.config is not None else "",
            "auto_close_on_game_exit": False,
            "obs": obs_config_to_dict(self.config.obs if self.config is not None else self.base_obs),
            "login_bonus": login_bonus_config_to_dict(
                self.config.login_bonus if self.config is not None else LoginBonusConfig()
            ),
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
        self.login_bonus_logger = LoginBonusLogger()
        self.login_bonus_checker = LoginBonusChecker()
        self.obs_prepare_running = False
        self.session_start = datetime.now()
        self.elapsed_before_run = 0.0
        self.run_started_at = 0.0
        self.paused = True
        self.play_started = False
        self.log_saved = True
        self.watcher: GameProcessWatcher | None = None
        self.closed = False
        self.tray_icon = None
        self.tray_icon_creating = False
        self.tray_available = pystray is not None and Image is not None and ImageDraw is not None
        first_config = configs[0]

        self.topmost = first_config.always_on_top
        self.time_var = tk.StringVar(value=tr("play_time", time="00:00:00"))
        self.current_game_var = tk.StringVar(value=tr("waiting"))
        self.obs_status_var = tk.StringVar(value=obs_status_text(self.obs_controller.status))
        self.login_bonus_status_var = tk.StringVar(value="")
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
        self.login_bonus_frame: ttk.LabelFrame | None = None
        self.login_bonus_game_check_button: ttk.Button | None = None
        self.login_bonus_game_claimed_button: ttk.Button | None = None
        self.login_bonus_game_unclaimed_button: ttk.Button | None = None
        self.login_bonus_web_check_button: ttk.Button | None = None
        self.login_bonus_web_claimed_button: ttk.Button | None = None
        self.login_bonus_web_unclaimed_button: ttk.Button | None = None
        self.obs_controls: ttk.Frame | None = None
        self.recording_start_button: ttk.Button | None = None
        self.recording_stop_button: ttk.Button | None = None
        self.reset_button: ttk.Button | None = None
        self.game_button_vars: dict[str, tk.StringVar] = {}
        default_font = tkfont.nametofont("TkDefaultFont")
        self.ui_font = default_font
        self.title_font = default_font.copy()
        self.title_font.configure(size=12, weight="bold")
        self.timer_font = default_font.copy()
        self.timer_font.configure(size=16, weight="bold")
        self.button_font = tkfont.nametofont("TkTextFont").copy()
        self.button_font.configure(weight="bold")

        self._configure_theme()
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

    def _configure_theme(self) -> None:
        self.root.configure(bg=THEME["bg"])
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=THEME["bg"], foreground=THEME["text"], fieldbackground=THEME["panel"])
        style.configure("TFrame", background=THEME["bg"])
        style.configure("Panel.TFrame", background=THEME["panel"])
        style.configure("TLabelframe", background=THEME["bg"], bordercolor=THEME["border"], relief=tk.SOLID)
        style.configure(
            "TLabelframe.Label",
            background=THEME["bg"],
            foreground=THEME["accent"],
            font=self.button_font,
        )
        style.configure("TLabel", background=THEME["bg"], foreground=THEME["text"])
        style.configure("Title.TLabel", background=THEME["bg"], foreground=THEME["accent"], font=self.title_font)
        style.configure("Muted.TLabel", background=THEME["bg"], foreground=THEME["muted"])
        style.configure("Timer.TLabel", background=THEME["bg"], foreground=THEME["accent_active"], font=self.timer_font)
        style.configure("TButton", background=THEME["panel_alt"], foreground=THEME["text"], borderwidth=0, padding=(10, 6))
        style.map("TButton", background=[("active", THEME["border"])], foreground=[("disabled", THEME["muted"])])
        style.configure("Accent.TButton", background=THEME["accent"], foreground=THEME["bg"])
        style.map("Accent.TButton", background=[("active", THEME["accent_active"])])
        style.configure("Danger.TButton", background=THEME["danger"], foreground=THEME["text"])
        style.map("Danger.TButton", background=[("active", THEME["danger_active"])])
        style.configure("TScale", background=THEME["bg"], troughcolor=THEME["panel_alt"])
        style.configure("Vertical.TScrollbar", background=THEME["panel_alt"], troughcolor=THEME["bg"])

    def _build_ui(self, first_config: GameConfig) -> None:
        self.root.title(tr("app_title"))
        self._build_menu()

        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        self.ui_title_label = ttk.Label(outer, text=tr("app_title"), style="Title.TLabel")
        self.ui_title_label.pack(anchor=tk.W)
        ttk.Label(outer, textvariable=self.current_game_var, style="Muted.TLabel").pack(anchor=tk.W, pady=(2, 10))

        self.game_list_frame = ttk.LabelFrame(outer, text=tr("game_list_title"))
        self.game_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        list_canvas = tk.Canvas(
            self.game_list_frame,
            height=138,
            bg=THEME["panel"],
            highlightthickness=1,
            highlightbackground=THEME["border"],
            bd=0,
        )
        self.game_list_canvas = list_canvas
        list_scrollbar = ttk.Scrollbar(self.game_list_frame, orient=tk.VERTICAL, command=list_canvas.yview)
        self.game_list_body = ttk.Frame(list_canvas, style="Panel.TFrame")
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

        self.time_label = ttk.Label(outer, textvariable=self.time_var, style="Timer.TLabel")
        self.time_label.pack(pady=(0, 8), anchor=tk.W)

        obs_frame = ttk.Frame(outer)
        obs_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(obs_frame, textvariable=self.obs_status_var, style="Muted.TLabel").pack(anchor=tk.W)
        self.obs_controls = ttk.Frame(obs_frame)
        self.obs_controls.pack(fill=tk.X, pady=(3, 0))
        self.recording_start_button = ttk.Button(
            self.obs_controls,
            text=tr("start_recording"),
            command=self.start_recording,
            style="Accent.TButton",
        )
        self.recording_start_button.pack(
            side=tk.LEFT, expand=True, fill=tk.X
        )
        self.recording_stop_button = ttk.Button(
            self.obs_controls,
            text=tr("stop_recording"),
            command=self.stop_recording,
            style="Danger.TButton",
        )
        self.recording_stop_button.pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(6, 0)
        )

        self.link_frame = ttk.LabelFrame(outer, text=tr("links"))
        self.link_frame.pack(fill=tk.X, expand=False, pady=(0, 8))
        canvas = tk.Canvas(
            self.link_frame,
            height=1,
            bg=THEME["panel"],
            highlightthickness=1,
            highlightbackground=THEME["border"],
            bd=0,
        )
        self.link_canvas = canvas
        scrollbar = ttk.Scrollbar(self.link_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.link_body = ttk.Frame(canvas, style="Panel.TFrame")
        self.link_body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.link_body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.login_bonus_frame = ttk.LabelFrame(outer, text=tr("login_bonus"))
        self.login_bonus_frame.pack(fill=tk.X, expand=False, pady=(0, 8))
        ttk.Label(self.login_bonus_frame, textvariable=self.login_bonus_status_var, style="Muted.TLabel").pack(
            anchor=tk.W, padx=4, pady=(3, 3)
        )
        login_game_row = ttk.Frame(self.login_bonus_frame)
        login_game_row.pack(fill=tk.X, padx=4, pady=(0, 3))
        self.login_bonus_game_check_button = ttk.Button(
            login_game_row,
            text=tr("login_bonus_game_check"),
            command=lambda: self.start_login_bonus_check("game_screen"),
        )
        self.login_bonus_game_check_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.login_bonus_game_claimed_button = ttk.Button(
            login_game_row,
            text=tr("login_bonus_manual_claimed"),
            command=lambda: self.set_login_bonus_manual("game_screen", "claimed"),
        )
        self.login_bonus_game_claimed_button.pack(side=tk.LEFT, padx=(4, 0))
        self.login_bonus_game_unclaimed_button = ttk.Button(
            login_game_row,
            text=tr("login_bonus_manual_unclaimed"),
            command=lambda: self.set_login_bonus_manual("game_screen", "unclaimed"),
        )
        self.login_bonus_game_unclaimed_button.pack(side=tk.LEFT, padx=(4, 0))
        login_web_row = ttk.Frame(self.login_bonus_frame)
        login_web_row.pack(fill=tk.X, padx=4, pady=(0, 4))
        self.login_bonus_web_check_button = ttk.Button(
            login_web_row,
            text=tr("login_bonus_web_check"),
            command=self.open_login_bonus_web,
        )
        self.login_bonus_web_check_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.login_bonus_web_claimed_button = ttk.Button(
            login_web_row,
            text=tr("login_bonus_manual_claimed"),
            command=lambda: self.set_login_bonus_manual("web", "claimed"),
        )
        self.login_bonus_web_claimed_button.pack(side=tk.LEFT, padx=(4, 0))
        self.login_bonus_web_unclaimed_button = ttk.Button(
            login_web_row,
            text=tr("login_bonus_manual_unclaimed"),
            command=lambda: self.set_login_bonus_manual("web", "unclaimed"),
        )
        self.login_bonus_web_unclaimed_button.pack(side=tk.LEFT, padx=(4, 0))
        self.login_bonus_frame.pack_forget()

        controls = ttk.Frame(outer)
        controls.pack(fill=tk.X)
        ttk.Button(controls, textvariable=self.pause_var, command=self.start_recent_game, style="Accent.TButton").pack(
            fill=tk.X
        )
        self.reset_button = ttk.Button(controls, text=tr("reset_time"), command=self.reset_timer)

        ttk.Button(outer, textvariable=self.topmost_var, command=self.toggle_topmost).pack(fill=tk.X, pady=(8, 4))
        self.opacity_label = ttk.Label(outer, text=tr("opacity"), style="Muted.TLabel")
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
        summary_menu.add_command(label=tr("last_end_time"), command=self.show_last_end_times)
        summary_menu.add_command(label=tr("calendar"), command=self.open_play_time_calendar)
        menu_bar.add_cascade(label=tr("summary"), menu=summary_menu)
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
        if self.login_bonus_frame is not None:
            self.login_bonus_frame.configure(text=tr("login_bonus"))
        if self.login_bonus_game_check_button is not None:
            self.login_bonus_game_check_button.configure(text=tr("login_bonus_game_check"))
        if self.login_bonus_web_check_button is not None:
            self.login_bonus_web_check_button.configure(text=tr("login_bonus_web_check"))
        for button in (self.login_bonus_game_claimed_button, self.login_bonus_web_claimed_button):
            if button is not None:
                button.configure(text=tr("login_bonus_manual_claimed"))
        for button in (self.login_bonus_game_unclaimed_button, self.login_bonus_web_unclaimed_button):
            if button is not None:
                button.configure(text=tr("login_bonus_manual_unclaimed"))
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
        self._refresh_login_bonus_status()

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
            padx=10,
            pady=7,
            bg=THEME["panel_alt"],
            fg=THEME["text"],
            activebackground=THEME["accent"],
            activeforeground=THEME["bg"],
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=THEME["border"],
            cursor="hand2",
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
        if self.closed or self.obs_prepare_running:
            return
        if not self.obs_controller.config.enabled:
            self._update_obs_status()
            self._update_obs_controls()
            return
        self.obs_prepare_running = True
        done_queue: queue.Queue[None] = queue.Queue()

        def worker() -> None:
            try:
                self.obs_controller.prepare(
                    launch_as_admin=True,
                    show_window=True,
                    show_errors=False,
                    connect_timeout_seconds=5,
                )
            finally:
                done_queue.put(None)

        def poll_done() -> None:
            self._update_obs_status()
            self._update_obs_controls()
            try:
                done_queue.get_nowait()
            except queue.Empty:
                if not self.closed:
                    self.root.after(200, poll_done)
                return
            self.obs_prepare_running = False

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(200, poll_done)

    def _monitor_obs_status(self) -> None:
        if self.closed:
            return
        if not self.obs_prepare_running:
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
        start_on_active_process = bool(config.process_name)
        self.session_start = datetime.now()
        self.elapsed_before_run = 0.0
        self.run_started_at = 0.0 if start_on_active_process else time.monotonic()
        self.paused = start_on_active_process
        self.play_started = not start_on_active_process
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
        self._refresh_login_bonus_status()
        self._fit_window_to_screen(config.window_width, config.window_height)

        self.launcher.launch_game(config)
        if config.obs.auto_start_recording_on_game_launch and self.play_started:
            self.obs_controller.start_recording()
            self._update_obs_status()
        self.launcher.open_links(config.auto_open_links)
        self._start_watcher(config)
        if self.play_started:
            self.start_login_bonus_check("game_screen")

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
            active_process_name=config.process_name,
            on_active=self.on_game_active,
        )
        self._watch_process()

    def on_game_active(self) -> None:
        if self.config is None or self.play_started:
            return
        self.session_start = datetime.now()
        self.elapsed_before_run = 0.0
        self.run_started_at = time.monotonic()
        self.paused = False
        self.play_started = True
        if self.config.obs.auto_start_recording_on_game_launch:
            self.obs_controller.start_recording()
            self._update_obs_status()
        self.start_login_bonus_check("game_screen")

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
            ttk.Button(
                self.link_body,
                text=link.name,
                command=lambda item=link: self.launcher.open_link(item),
                style="Accent.TButton",
            ).pack(
                fill=tk.X, padx=4, pady=3
            )
        self._set_link_area_expanded(has_links)

    def _refresh_login_bonus_status(self) -> None:
        if self.login_bonus_frame is None:
            return
        if self.config is None or not self.config.login_bonus.enabled:
            self.login_bonus_status_var.set(tr("login_bonus_disabled"))
            self._set_login_bonus_button_states(False, False)
            self.login_bonus_frame.pack_forget()
            return
        if not self.login_bonus_frame.winfo_ismapped():
            self.login_bonus_frame.pack(fill=tk.X, expand=False, pady=(0, 8))
        can_auto_check = LoginBonusChecker.is_ocr_available()
        self._set_login_bonus_button_states(
            self.config.login_bonus.game_screen.enabled and can_auto_check,
            self.config.login_bonus.web.enabled and can_auto_check,
        )
        game_status = self._login_bonus_display_status("game_screen")
        web_status = self._login_bonus_display_status("web")
        self.login_bonus_status_var.set(
            f"{tr('login_bonus_game_source')}: {game_status} / {tr('login_bonus_web_source')}: {web_status}"
        )

    def _set_login_bonus_button_states(self, game_auto: bool, web_auto: bool) -> None:
        game_enabled = self.config is not None and self.config.login_bonus.enabled and self.config.login_bonus.game_screen.enabled
        web_enabled = self.config is not None and self.config.login_bonus.enabled and self.config.login_bonus.web.enabled
        if self.login_bonus_game_check_button is not None:
            self.login_bonus_game_check_button.configure(state=tk.NORMAL if game_auto else tk.DISABLED)
        if self.login_bonus_web_check_button is not None:
            self.login_bonus_web_check_button.configure(state=tk.NORMAL if web_auto else tk.DISABLED)
        for button in (self.login_bonus_game_claimed_button, self.login_bonus_game_unclaimed_button):
            if button is not None:
                button.configure(state=tk.NORMAL if game_enabled else tk.DISABLED)
        for button in (self.login_bonus_web_claimed_button, self.login_bonus_web_unclaimed_button):
            if button is not None:
                button.configure(state=tk.NORMAL if web_enabled else tk.DISABLED)

    def _login_bonus_display_status(self, source: str) -> str:
        if self.config is None:
            return tr("login_bonus_unknown")
        row = self.login_bonus_logger.latest(self.config, source)
        if row is None:
            return tr("login_bonus_unknown")
        return self._login_bonus_status_text(row.get("status", "unknown"))

    def _login_bonus_status_text(self, status: str) -> str:
        return {
            "claimed": tr("login_bonus_claimed"),
            "unclaimed": tr("login_bonus_unclaimed"),
            "unknown": tr("login_bonus_unknown"),
        }.get(status, tr("login_bonus_unknown"))

    def open_login_bonus_web(self) -> None:
        if self.config is None:
            return
        source = self.config.login_bonus.web
        if source.url:
            self.launcher.open_link(LinkItem(name=tr("login_bonus"), url=source.url))
        self.start_login_bonus_check("web")

    def start_login_bonus_check(self, source: str) -> None:
        if self.config is None or not self.config.login_bonus.enabled:
            return
        source_config = LoginBonusChecker._source_config(self.config, source)
        if source_config is None or not source_config.enabled:
            return
        deadline = time.monotonic() + source_config.timeout_seconds
        self._retry_login_bonus_check(source, deadline)

    def _retry_login_bonus_check(self, source: str, deadline: float) -> None:
        if self.config is None:
            return
        source_config = LoginBonusChecker._source_config(self.config, source)
        if source_config is None:
            return
        status, evidence, method = self.login_bonus_checker.check(self.config, source)
        if status in {"claimed", "unclaimed"}:
            self._save_login_bonus_if_changed(source, status, evidence, method, manual=False)
            self._refresh_login_bonus_status()
            if status == "claimed":
                return
        if time.monotonic() >= deadline:
            self._refresh_login_bonus_status()
            return
        delay_ms = max(1, source_config.retry_interval_seconds) * 1000
        self.root.after(delay_ms, lambda: self._retry_login_bonus_check(source, deadline))

    def _save_login_bonus_if_changed(
        self,
        source: str,
        status: str,
        evidence: str,
        method: str,
        manual: bool,
    ) -> None:
        if self.config is None:
            return
        latest = self.login_bonus_logger.latest(self.config, source)
        if latest is not None and latest.get("status") == status and not manual:
            return
        try:
            self.login_bonus_logger.save(self.config, source, status, evidence, method, manual)
        except OSError as exc:
            messagebox.showerror("Login Bonus Error", str(exc))

    def set_login_bonus_manual(self, source: str, status: str) -> None:
        if self.config is None:
            return
        self._save_login_bonus_if_changed(source, status, "manual", "manual", manual=True)
        self._refresh_login_bonus_status()

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
        if not self.paused and self.run_started_at > 0:
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
        if self.play_started:
            self.save_log_once()
        self.config = None
        self.watcher = None
        self.session_start = datetime.now()
        self.elapsed_before_run = 0.0
        self.run_started_at = 0.0
        self.paused = True
        self.play_started = False
        self.log_saved = True
        self.current_game_var.set(tr("waiting"))
        self.pause_var.set(tr("start_recent"))
        if self.reset_button is not None:
            self.reset_button.pack_forget()
        self.obs_status_var.set(self.obs_controller.status)
        self._refresh_links()
        self._refresh_login_bonus_status()
        self._set_waiting_ui(True)
        self._refresh_game_list()
        self.root.title(tr("app_title"))
        self.time_var.set(tr("play_time", time="00:00:00"))
        self._fit_window_to_screen(self.root.winfo_width(), self.root.winfo_height())

    def _on_unmap(self, event) -> None:
        if event.widget is not self.root:
            return
        if self.closed or self.root.state() != "iconic":
            return
        self.minimize_to_tray()

    def minimize_to_tray(self) -> None:
        if not self.tray_available:
            return
        if self.tray_icon is not None or self.tray_icon_creating:
            self.root.withdraw()
            return
        self.tray_icon_creating = True
        try:
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
        finally:
            self.tray_icon_creating = False
        self.root.withdraw()

    def restore_from_tray(self) -> None:
        self._stop_tray_icon()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _stop_tray_icon(self) -> None:
        if self.tray_icon is None:
            return
        try:
            self.tray_icon.stop()
        finally:
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

    def open_play_time_calendar(self) -> None:
        selected_month = datetime.now().replace(day=1)
        window = tk.Toplevel(self.root)
        window.title(tr("calendar"))
        window.geometry("420x560")

        outer = ttk.Frame(window, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(outer)
        header.pack(fill=tk.X)
        month_var = tk.StringVar()
        ttk.Button(header, text=tr("previous_month"), command=lambda: shift_month(-1)).pack(side=tk.LEFT)
        ttk.Label(header, textvariable=month_var, anchor=tk.CENTER).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(header, text=tr("next_month"), command=lambda: shift_month(1)).pack(side=tk.RIGHT)

        calendar_frame = ttk.Frame(outer)
        calendar_frame.pack(fill=tk.X, pady=(8, 8))
        result_frame = ttk.Frame(outer)
        result_frame.pack(fill=tk.BOTH, expand=True)
        result_text = tk.Text(result_frame, height=10, wrap=tk.WORD)
        result_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=result_text.yview)
        result_text.configure(yscrollcommand=result_scrollbar.set)
        result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        result_text.insert(tk.END, tr("not_recorded"))
        result_text.configure(state=tk.DISABLED)

        def shift_month(delta: int) -> None:
            nonlocal selected_month
            month = selected_month.month + delta
            year = selected_month.year + ((month - 1) // 12)
            month = ((month - 1) % 12) + 1
            selected_month = selected_month.replace(year=year, month=month)
            render_month()

        def select_date(selected_date: date) -> None:
            totals = self._play_seconds_by_game_on_date(selected_date)
            if not totals:
                update_result(f"{tr('calendar_daily_title', date=selected_date.isoformat())}\n{tr('not_recorded')}")
                return
            lines = [
                f"{game_name}: {PlayTimeLogger.format_hhmmss(totals[game_name])}"
                for game_name in self._summary_game_names(totals)
                if game_name in totals
            ]
            update_result(f"{tr('calendar_daily_title', date=selected_date.isoformat())}\n" + "\n".join(lines))

        def update_result(text: str) -> None:
            result_text.configure(state=tk.NORMAL)
            result_text.delete("1.0", tk.END)
            result_text.insert(tk.END, text)
            result_text.configure(state=tk.DISABLED)

        def render_month() -> None:
            for child in calendar_frame.winfo_children():
                child.destroy()
            month_var.set(selected_month.strftime("%Y-%m"))
            today = date.today()
            recorded_dates = self._play_recorded_dates()
            weekday_labels = ["月", "火", "水", "木", "金", "土", "日"] if UI_LANGUAGE == "ja" else list(calendar.day_abbr)
            for column, label in enumerate(weekday_labels):
                ttk.Label(calendar_frame, text=label, anchor=tk.CENTER).grid(row=0, column=column, sticky="ew", padx=1, pady=1)
                calendar_frame.columnconfigure(column, weight=1)
            for row_index, week in enumerate(calendar.monthcalendar(selected_month.year, selected_month.month), start=1):
                for column, day in enumerate(week):
                    if day == 0:
                        ttk.Label(calendar_frame, text="").grid(row=row_index, column=column, sticky="nsew", padx=1, pady=1)
                        continue
                    selected_date = date(selected_month.year, selected_month.month, day)
                    state = tk.NORMAL if selected_date <= today and selected_date in recorded_dates else tk.DISABLED
                    ttk.Button(
                        calendar_frame,
                        text=str(day),
                        state=state,
                        command=lambda value=selected_date: select_date(value),
                    ).grid(row=row_index, column=column, sticky="nsew", padx=1, pady=1)
                calendar_frame.rowconfigure(row_index, weight=1)

        render_month()

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

    def _play_seconds_by_game_on_date(self, selected_date: date) -> dict[str, int]:
        totals: dict[str, int] = {}
        for row in self._history_rows():
            session_end = row["session_end"]
            if isinstance(session_end, datetime) and session_end.date() == selected_date:
                game_name = str(row["game_name"])
                totals[game_name] = totals.get(game_name, 0) + int(row["elapsed_seconds"])
        if self.config is not None and self.session_start.date() == selected_date:
            totals[self.config.game_name] = totals.get(self.config.game_name, 0) + self.current_elapsed_seconds()
        return totals

    def _play_recorded_dates(self) -> set[date]:
        dates: set[date] = set()
        for row in self._history_rows():
            session_end = row["session_end"]
            if isinstance(session_end, datetime):
                dates.add(session_end.date())
        if self.config is not None:
            dates.add(self.session_start.date())
        return dates

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
        if self.closed:
            return
        self.closed = True
        if self.watcher:
            self.watcher.stopped = True
        if self.play_started:
            self.save_log_once()
        self._stop_tray_icon()
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
