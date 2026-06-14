from __future__ import annotations

import calendar
import csv
import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
from dataclasses import replace
from datetime import date, datetime, timedelta
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

from playcue.config.loader import ConfigLoader
from playcue.obs.obs_controller import OBSStatus
from playcue.launcher.game_launcher import GameLauncher
from playcue.login_bonus.checker import LoginBonusChecker
from playcue.login_bonus.logger import LoginBonusLogger
from playcue.logs import PlayTimeLogger
from playcue.obs.obs_controller import OBSController
from playcue.system.console import ConsoleController
from playcue.system.startup import StartupTaskController
from playcue.tracking.process_tracker import GameProcessWatcher
from playcue.ui import i18n
from playcue.ui.i18n import obs_status_text, tr
from playcue.ui.theme import THEME, OBS_STATUS_COLOR
from playcue.ui.config_wizard import ConfigWizard
from playcue.ui.obs_settings import OBSSettingsWindow
from playcue.models import GameConfig, LinkItem, OBSConfig
from playcue.paths import (
    backup_configs_dir,
    play_history_log_file,
    play_logs_db_file,
    play_time_summary_file,
)
from playcue.session import GameSession, SessionStore, finish_session, now_jst, start_session
from playcue.session.db import logger as session_db_logger
from playcue.session.dialog import ask_session_memo, default_memo

LOG_FILE = play_history_log_file()
SUMMARY_FILE = play_time_summary_file()


class _Tooltip:
    """ホバー時に全文を表示する軽量ツールチップ。ウィジェット破棄後も安全。"""

    _DELAY_MS = 700

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self._widget = widget
        self._text = text
        self._tip: tk.Toplevel | None = None
        self._after_id: str | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._after_id = self._widget.after(self._DELAY_MS, self._show)

    def _show(self) -> None:
        if self._tip is not None:
            return
        try:
            if not self._widget.winfo_exists():
                return
            x = self._widget.winfo_rootx() + 10
            y = self._widget.winfo_rooty() + self._widget.winfo_height()
        except tk.TclError:
            return
        self._tip = tk.Toplevel(self._widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self._tip,
            text=self._text,
            bg=THEME["panel_alt"],
            fg=THEME["text"],
            relief=tk.SOLID,
            borderwidth=1,
            padx=6,
            pady=4,
            justify=tk.LEFT,
            font=("", 9),
        ).pack()

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self._widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None


class ResidentPlayCueApp:
    def __init__(self, root: Tk, configs: list[GameConfig]):
        self.root = root
        self.configs = configs
        self.config: GameConfig | None = None
        # Use the first real config for UI defaults, or fall back to dataclass defaults.
        _ui = configs[0] if configs else GameConfig(game_name="", config_file=Path("."))
        self.obs_controller = OBSController(_ui.obs)
        self.launcher = GameLauncher()
        self.logger = PlayTimeLogger()
        # 攻略AIシステム用プレイログ基盤 (Phase 1)。DB が使えなくても本体は動かす。
        self.session: GameSession | None = None
        self.session_store: SessionStore | None = self._init_session_store()
        self.login_bonus_logger = LoginBonusLogger()
        self.login_bonus_checker = LoginBonusChecker()
        self.obs_prepare_running = False
        self.obs_recording_op_running = False
        self._history_cache: list[dict[str, object]] | None = None
        self._history_cache_mtime: float | None = None
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
        first_config = _ui

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
        self.obs_status_label: tk.Label | None = None
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
        if not configs:
            self.root.after(200, self._open_initial_wizard)

    def _open_initial_wizard(self) -> None:
        if self.closed:
            return
        messagebox.showinfo(tr("app_title"), tr("no_games_yet"))
        self.open_config_wizard()

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
        style.configure(
            "Treeview",
            background=THEME["panel"],
            foreground=THEME["text"],
            fieldbackground=THEME["panel"],
            rowheight=25,
        )
        style.configure("Treeview.Heading", background=THEME["panel_alt"], foreground=THEME["text"], relief=tk.FLAT)
        style.map(
            "Treeview",
            background=[("selected", THEME["accent"])],
            foreground=[("selected", THEME["bg"])],
        )

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
        _sorted_initial = self._sorted_configs_by_recent_play()
        _initial_most_recent = _sorted_initial[0].game_name if _sorted_initial else None
        for config in _sorted_initial:
            self._add_game_button(config, is_recent=config.game_name == _initial_most_recent)

        self.time_label = ttk.Label(outer, textvariable=self.time_var, style="Timer.TLabel")
        self.time_label.pack(pady=(0, 8), anchor=tk.W)

        obs_frame = ttk.Frame(outer)
        obs_frame.pack(fill=tk.X, pady=(0, 8))
        self.obs_status_label = tk.Label(
            obs_frame,
            textvariable=self.obs_status_var,
            bg=THEME["bg"],
            fg=THEME["muted"],
            anchor=tk.W,
        )
        self.obs_status_label.pack(anchor=tk.W)
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
        summary_menu.add_separator()
        summary_menu.add_command(label=tr("history_list"), command=self.open_play_history_view)
        menu_bar.add_cascade(label=tr("summary"), menu=summary_menu)
        self.root.config(menu=menu_bar)

    def set_language(self, language: str) -> None:
        i18n.set_language(language)
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
        self._rebuild_game_list()

    def _add_game_button(self, config: GameConfig, is_recent: bool = False) -> None:
        if self.game_list_body is None:
            return
        button_var = tk.StringVar(value=self._game_list_text(config, is_recent=is_recent))
        self.game_button_vars[config.game_name] = button_var
        bg = THEME["panel"] if is_recent else THEME["panel_alt"]
        button = tk.Button(
            self.game_list_body,
            textvariable=button_var,
            anchor=tk.W,
            justify=tk.LEFT,
            font=self.button_font,
            padx=10,
            pady=6,
            bg=bg,
            fg=THEME["text"],
            activebackground=THEME["accent"],
            activeforeground=THEME["bg"],
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=THEME["accent"] if is_recent else THEME["border"],
            cursor="hand2",
            command=lambda item=config: self.start_game(item),
        )
        button.bind("<MouseWheel>", self._scroll_game_list)
        button.pack(fill=tk.X, padx=3, pady=3)
        _Tooltip(button, self._game_list_full_text(config))

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
                messagebox.showwarning(tr("game_select_error"), tr("game_select_message"), parent=selector)
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
                messagebox.showwarning(tr("game_select_error"), tr("game_select_message"), parent=selector)
                return
            config = self.configs[selection[0]]
            if self.config is not None and self.config.config_file == config.config_file:
                messagebox.showwarning(tr("game_delete_error"), tr("game_delete_active_message"), parent=selector)
                return
            if not messagebox.askyesno(tr("delete_game"), tr("game_delete_confirm", game_name=config.game_name), parent=selector):
                return
            try:
                self._backup_config_file(config)
            except OSError:
                messagebox.showerror(tr("game_delete_error"), tr("game_delete_backup_failed"), parent=selector)
                return
            try:
                if config.config_file.exists():
                    config.config_file.unlink()
            except OSError:
                # Do not include exc — OSError strings may contain local absolute paths.
                messagebox.showerror(tr("game_delete_file_error"), tr("game_delete_file_failed"), parent=selector)
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
                    "enabled": obs_config.enabled,
                    "exe_path": obs_config.exe_path,
                    "working_dir": obs_config.working_dir,
                    "process_name": obs_config.process_name,
                    "websocket_host": obs_config.websocket_host,
                    "websocket_port": obs_config.websocket_port,
                    "websocket_password": obs_config.websocket_password,
                    "auto_launch": obs_config.auto_launch,
                    "launch_as_admin": obs_config.launch_as_admin,
                    "auto_start_recording_on_game_launch": obs_config.auto_start_recording_on_game_launch,
                    "auto_stop_recording_on_game_exit": obs_config.auto_stop_recording_on_game_exit,
                }
            )
            data["obs"] = current_obs
            with config.config_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        self.configs = [ConfigLoader.load(config.config_file) for config in self.configs]
        self.obs_controller = OBSController(obs_config)
        self._update_obs_status()

    def toggle_terminal(self) -> None:
        ConsoleController.set_visible(bool(self.terminal_visible_var.get()))

    def toggle_startup(self) -> None:
        enabled = bool(self.startup_enabled_var.get())
        try:
            StartupTaskController.set_enabled(enabled)
        except OSError:
            # Do not include exc — OSError strings may contain local absolute paths.
            self.startup_enabled_var.set(not enabled)
            messagebox.showerror(tr("startup_error"), tr("startup_set_failed"))

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
                    launch_as_admin=self.obs_controller.config.launch_as_admin,
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
        is_recording = self.obs_controller.status == OBSStatus.RECORDING
        is_connected = self.obs_controller.status == OBSStatus.CONNECTED
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
            messagebox.showwarning(tr("game_running_warning"), tr("game_running_message", game_name=self.config.game_name))
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
            messagebox.showwarning(tr("game_running_warning"), tr("game_running_message", game_name=self.config.game_name))
            return

        self.config = config
        self._update_obs_status()
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
        self.root.attributes("-alpha", config.opacity)
        self.opacity_var.set(config.opacity)
        self._set_waiting_ui(False)
        self._refresh_links()
        self._refresh_login_bonus_status()
        self._fit_window_to_screen(config.window_width, config.window_height)

        launched = self.launcher.launch_game(config)
        if not launched:
            self._reset_to_waiting_state()
            return
        if self.play_started:
            self._begin_session_log()
        if config.obs.auto_start_recording_on_game_launch and self.play_started:
            self.start_recording()
        self.launcher.open_links(config.auto_open_links)
        self._start_watcher(config)
        if self.play_started:
            self.start_login_bonus_check("game_screen")

    def _start_watcher(self, config: GameConfig) -> None:
        if not config.process_name:
            return
        if psutil is None:
            messagebox.showwarning(tr("process_monitor_disabled"), tr("process_monitor_disabled_message"))
            return
        self.watcher = GameProcessWatcher(
            config.process_name,
            self.on_game_exit,
            exe_path=config.game_exe,
            on_process_name_detected=lambda process_name: self._update_config_process_name(config, process_name),
            active_process_name=config.active_process_name,
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
        self._begin_session_log()
        if self.config.obs.auto_start_recording_on_game_launch:
            self.start_recording()
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
            self.root.after(1000, self._watch_process)

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
        source_config = LoginBonusChecker.source_config(self.config, source)
        if source_config is None or not source_config.enabled:
            return
        deadline = time.monotonic() + source_config.timeout_seconds
        self._retry_login_bonus_check(source, deadline)

    def _retry_login_bonus_check(self, source: str, deadline: float) -> None:
        if self.config is None:
            return
        source_config = LoginBonusChecker.source_config(self.config, source)
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
        except OSError:
            # Do not include exc — OSError strings may contain local absolute paths.
            messagebox.showerror(tr("log_save_error"), tr("log_save_error_message"))

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
            self.pause_var.set(tr("pause"))
            return
        self.elapsed_before_run = float(self.current_elapsed_seconds())
        self.paused = True
        self.pause_var.set(tr("resume"))

    def reset_timer(self) -> None:
        if self.config is None:
            return
        self.session_start = datetime.now()
        self.elapsed_before_run = 0.0
        self.run_started_at = time.monotonic()
        self.time_var.set(tr("play_time", time="00:00:00"))

    def _reset_to_waiting_state(self) -> None:
        """ゲーム起動失敗時に UI と内部状態を待機状態へ戻す。ログ・録画は保存しない。"""
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
        self._update_obs_status()
        self._refresh_links()
        self._refresh_login_bonus_status()
        self._set_waiting_ui(True)
        self.root.title(tr("app_title"))
        self.time_var.set(tr("play_time", time="00:00:00"))
        self._fit_window_to_screen(self.root.winfo_width(), self.root.winfo_height())

    def on_game_exit(self) -> None:
        self.stop_recording_for_game_exit()
        if self.play_started:
            self.save_log_once()
            self._finish_session_log(show_dialog=True)
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
        self._update_obs_status()
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
        self.root.state("normal")
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
            weekday_labels = ["月", "火", "水", "木", "金", "土", "日"] if i18n.UI_LANGUAGE == "ja" else list(calendar.day_abbr)
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
        self._rebuild_game_list()

    def _rebuild_game_list(self) -> None:
        if self.game_list_body is None:
            return
        for child in self.game_list_body.winfo_children():
            child.destroy()
        self.game_button_vars.clear()
        sorted_configs = self._sorted_configs_by_recent_play()
        most_recent = sorted_configs[0].game_name if sorted_configs else None
        for config in sorted_configs:
            is_recent = most_recent is not None and config.game_name == most_recent
            self._add_game_button(config, is_recent=is_recent)

    def _sorted_configs_by_recent_play(self) -> list[GameConfig]:
        """game_keyで重複排除し、直近プレイ順にソートしたconfig一覧。"""
        last_end_times = self._last_end_datetime_by_game()
        name_map = self._display_name_by_key()

        def _mtime(c: GameConfig) -> float:
            try:
                return c.config_file.stat().st_mtime if c.config_file.exists() else 0.0
            except OSError:
                return 0.0

        seen_keys: set[str] = set()
        unique: list[GameConfig] = []
        for config in sorted(self.configs, key=_mtime, reverse=True):
            key = config.get_game_key()
            if key not in seen_keys:
                seen_keys.add(key)
                unique.append(config)

        return sorted(
            unique,
            key=lambda c: last_end_times.get(name_map.get(c.get_game_key(), c.game_name), datetime.min),
            reverse=True,
        )

    def _game_list_text(self, config: GameConfig, is_recent: bool = False) -> str:
        """ゲーム一覧ボタンの短縮テキスト。詳細はツールチップで表示。"""
        seconds = self._last_play_seconds_by_game().get(config.game_name, 0)
        prefix = "★ " if is_recent else "  "
        name_line = f"{prefix}{config.game_name}"
        last_end_times = self._last_end_time_by_game()
        if config.game_name in last_end_times:
            sub_line = f"  {tr('last_play')}: {PlayTimeLogger.format_hhmmss(seconds)}"
        else:
            sub_line = f"  {tr('not_recorded')}"
        return f"{name_line}\n{sub_line}"

    def _game_list_full_text(self, config: GameConfig) -> str:
        """ツールチップ用の詳細テキスト（前回時間 + 終了日時）。"""
        seconds = self._last_play_seconds_by_game().get(config.game_name, 0)
        last_end_times = self._last_end_time_by_game()
        if config.game_name in last_end_times:
            end_str = last_end_times[config.game_name]
            return (
                f"{config.game_name}\n"
                f"{tr('last_play')}: {PlayTimeLogger.format_hhmmss(seconds)}\n"
                f"{tr('last_end')}: {end_str}"
            )
        return f"{config.game_name}\n{tr('not_recorded')}"

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

    def _invalidate_history_cache(self) -> None:
        self._history_cache = None
        self._history_cache_mtime = None

    def _history_rows(self) -> list[dict[str, object]]:
        """CSV 履歴を読み込んで返す。mtime が変わっていなければキャッシュを再利用する。"""
        if not LOG_FILE.exists():
            self._invalidate_history_cache()
            return []
        try:
            current_mtime = LOG_FILE.stat().st_mtime
        except OSError:
            self._invalidate_history_cache()
            return []
        if self._history_cache is not None and self._history_cache_mtime == current_mtime:
            return self._history_cache
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
                                "game_key": (row.get("game_key") or "").strip(),
                                "session_end": session_end,
                                "elapsed_seconds": elapsed_seconds,
                            }
                        )
        except OSError:
            self._invalidate_history_cache()
            return []
        self._history_cache = rows
        self._history_cache_mtime = current_mtime
        return rows

    @staticmethod
    def _game_key_from_row(row: dict[str, object]) -> str:
        """CSVの行からgame_keyを取得する。旧ログにはgame_key列がないためgame_nameで代替。"""
        key = str(row.get("game_key") or "").strip()
        if key:
            return key
        name = str(row.get("game_name") or "").strip().lower()
        return re.sub(r"\s+", "_", name) if name else "unknown"

    def _display_name_by_key(self) -> dict[str, str]:
        """game_key → 表示名のマッピングを返す。優先順: 現在のconfig > ログ最新行。"""
        latest_by_key: dict[str, tuple[datetime, str]] = {}
        for row in self._history_rows():
            key = self._game_key_from_row(row)
            session_end = row["session_end"]
            if isinstance(session_end, datetime):
                if key not in latest_by_key or session_end > latest_by_key[key][0]:
                    latest_by_key[key] = (session_end, str(row["game_name"]))

        result: dict[str, str] = {k: name for k, (_, name) in latest_by_key.items()}

        def _mtime(c: GameConfig) -> float:
            try:
                return c.config_file.stat().st_mtime if c.config_file.exists() else 0.0
            except OSError:
                return 0.0

        for config in sorted(self.configs, key=_mtime):
            result[config.get_game_key()] = config.game_name
        return result

    def open_play_history_view(self) -> None:
        window = tk.Toplevel(self.root)
        window.title(tr("history_list"))

        outer = ttk.Frame(window, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        cols = ("game", "start", "end", "time")
        tree_frame = ttk.Frame(outer)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        tree.heading("game", text=tr("history_col_game"))
        tree.heading("start", text=tr("history_col_start"))
        tree.heading("end", text=tr("history_col_end"))
        tree.heading("time", text=tr("history_col_time"))
        tree.column("game", width=200, minwidth=100, stretch=True)
        tree.column("start", width=155, minwidth=120, stretch=False)
        tree.column("end", width=155, minwidth=120, stretch=False)
        tree.column("time", width=90, minwidth=80, stretch=False)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        rows = self._read_history_for_view()
        if rows:
            for row in rows:
                tree.insert("", tk.END, values=(
                    row["game_name"],
                    row["session_start"],
                    row["session_end"],
                    row["elapsed_hhmmss"],
                ))
        else:
            tree.insert("", tk.END, values=(tr("no_history"), "", "", ""))

        window.update_idletasks()
        window.geometry("680x400")

    def _read_history_for_view(self) -> list[dict[str, str]]:
        if not LOG_FILE.exists():
            return []
        rows: list[tuple[datetime, dict[str, str]]] = []
        try:
            with LOG_FILE.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    game_name = (row.get("game_name") or "").strip()
                    session_start = (row.get("session_start") or "").strip()
                    session_end_str = (row.get("session_end") or "").strip()
                    elapsed_hhmmss = (row.get("elapsed_hhmmss") or "").strip()
                    if not game_name or not session_end_str:
                        continue
                    session_end_dt = self._parse_datetime(session_end_str)
                    if session_end_dt is None:
                        continue
                    rows.append((session_end_dt, {
                        "game_name": game_name,
                        "session_start": session_start,
                        "session_end": session_end_str,
                        "elapsed_hhmmss": elapsed_hhmmss,
                    }))
        except OSError:
            return []
        rows.sort(key=lambda item: item[0], reverse=True)
        return [data for _, data in rows[:50]]

    def _backup_config_file(self, config: GameConfig) -> None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest_dir = backup_configs_dir() / timestamp
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config.config_file, dest_dir / config.config_file.name)

    def _last_end_time_by_game(self) -> dict[str, str]:
        latest = self._last_end_datetime_by_game()
        return {
            game_name: session_end.strftime("%Y-%m-%d %H:%M:%S")
            for game_name, session_end in latest.items()
        }

    def _last_end_datetime_by_game(self) -> dict[str, datetime]:
        """表示名 → 最終セッション終了時刻。game_keyで統合済み。"""
        name_map = self._display_name_by_key()
        by_name: dict[str, datetime] = {}
        for row in self._history_rows():
            display = name_map.get(self._game_key_from_row(row), str(row["game_name"]))
            session_end = row["session_end"]
            if not isinstance(session_end, datetime):
                continue
            if display not in by_name or session_end > by_name[display]:
                by_name[display] = session_end
        return by_name

    def _last_play_seconds_by_game(self) -> dict[str, int]:
        """表示名 → 最終セッション経過秒数。game_keyで統合済み。"""
        name_map = self._display_name_by_key()
        latest: dict[str, tuple[datetime, int]] = {}
        for row in self._history_rows():
            display = name_map.get(self._game_key_from_row(row), str(row["game_name"]))
            session_end = row["session_end"]
            elapsed_seconds = int(row["elapsed_seconds"])
            if not isinstance(session_end, datetime):
                continue
            if display not in latest or session_end > latest[display][0]:
                latest[display] = (session_end, elapsed_seconds)
        return {name: secs for name, (_dt, secs) in latest.items()}

    def _play_seconds_by_game(self, days: int | None) -> dict[str, int]:
        """表示名 → 期間内累計秒数。game_keyで統合済み。"""
        cutoff = datetime.now() - timedelta(days=days) if days is not None else None
        name_map = self._display_name_by_key()
        totals: dict[str, int] = {}
        for row in self._history_rows():
            session_end = row["session_end"]
            if isinstance(session_end, datetime) and (cutoff is None or session_end >= cutoff):
                display = name_map.get(self._game_key_from_row(row), str(row["game_name"]))
                totals[display] = totals.get(display, 0) + int(row["elapsed_seconds"])
        if self.config is not None and (cutoff is None or self.session_start >= cutoff):
            display = name_map.get(self.config.get_game_key(), self.config.game_name)
            totals[display] = totals.get(display, 0) + self.current_elapsed_seconds()
        return totals

    def _play_seconds_by_game_on_date(self, selected_date: date) -> dict[str, int]:
        """表示名 → 指定日の累計秒数。game_keyで統合済み。"""
        name_map = self._display_name_by_key()
        totals: dict[str, int] = {}
        for row in self._history_rows():
            session_end = row["session_end"]
            if isinstance(session_end, datetime) and session_end.date() == selected_date:
                display = name_map.get(self._game_key_from_row(row), str(row["game_name"]))
                totals[display] = totals.get(display, 0) + int(row["elapsed_seconds"])
        if self.config is not None and self.session_start.date() == selected_date:
            display = name_map.get(self.config.get_game_key(), self.config.game_name)
            totals[display] = totals.get(display, 0) + self.current_elapsed_seconds()
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
        """表示名の順序リスト。game_keyで重複排除済み。"""
        names: list[str] = []
        seen: set[str] = set()
        seen_keys: set[str] = set()
        name_map = self._display_name_by_key()

        for config in self.configs:
            key = config.get_game_key()
            if key not in seen_keys:
                seen_keys.add(key)
                display = config.game_name
                if display not in seen:
                    names.append(display)
                    seen.add(display)

        for row in self._history_rows():
            key = self._game_key_from_row(row)
            if key not in seen_keys:
                seen_keys.add(key)
                display = name_map.get(key, str(row["game_name"]))
                if display not in seen:
                    names.append(display)
                    seen.add(display)

        if values is not None:
            for game_name in values:
                if game_name not in seen:
                    names.append(game_name)
                    seen.add(game_name)
        return names

    def _write_total_summary_csv(self) -> Path:
        SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
        game_names = self._summary_game_names()
        name_map = self._display_name_by_key()
        rows_by_end_time: dict[datetime, dict[str, int]] = {}
        for row in self._history_rows():
            session_end = row["session_end"]
            if not isinstance(session_end, datetime):
                continue
            display = name_map.get(self._game_key_from_row(row), str(row["game_name"]))
            end_time_row = rows_by_end_time.setdefault(session_end, {})
            end_time_row[display] = end_time_row.get(display, 0) + int(row["elapsed_seconds"])

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

    def _run_obs_op_async(self, op, on_done=None) -> bool:
        """OBS 操作をバックグラウンドスレッドで実行する。

        既に操作が進行中なら False を返して何もしない（連打防止）。
        op 完了後、on_done を root.after(0) 経由でメインスレッドで呼ぶ。
        """
        if self.obs_recording_op_running:
            return False
        self.obs_recording_op_running = True

        def worker() -> None:
            try:
                op()
            finally:
                if not self.closed:
                    self.root.after(0, _finish)
                else:
                    self.obs_recording_op_running = False

        def _finish() -> None:
            self.obs_recording_op_running = False
            self._update_obs_status()
            self._update_obs_controls()
            if on_done and not self.closed:
                on_done()

        threading.Thread(target=worker, daemon=True).start()
        return True

    def start_recording(self) -> None:
        self._run_obs_op_async(self.obs_controller.start_recording)

    def stop_recording(self) -> None:
        self._run_obs_op_async(self.obs_controller.stop_recording)

    def stop_recording_for_game_exit(self) -> None:
        if self.config is not None and self.config.obs.auto_stop_recording_on_game_exit:
            self._run_obs_op_async(
                lambda: self.obs_controller.stop_recording(only_if_started_by_app=True)
            )

    def _update_obs_status(self) -> None:
        status = self.obs_controller.status
        text = obs_status_text(status)
        if status == "recording":
            text = f"● {text}"
        self.obs_status_var.set(text)
        if self.obs_status_label is not None:
            color_key = OBS_STATUS_COLOR.get(status, "muted")
            self.obs_status_label.configure(fg=THEME.get(color_key, THEME["muted"]))

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
            # 終了検知前にアプリを閉じたため、メモ入力なしで unknown_end として保存。
            self._finish_session_log(show_dialog=False, status="unknown_end")
        self._stop_tray_icon()
        self.root.destroy()

    def _init_session_store(self) -> SessionStore | None:
        """play_logs.db を初期化する。失敗しても CSV ログと本体は継続する。"""
        try:
            store = SessionStore(play_logs_db_file())
            if store.init_db():
                return store
        except Exception:  # pragma: no cover - DB は補助機能のため握りつぶす
            session_db_logger.error("PlayCueDB failed to init store reason=init_error")
        return None

    def _begin_session_log(self) -> None:
        """プレイ計測開始と同じ瞬間にセッションを DB へ登録する（CSV と整合）。"""
        if self.config is None or self.session is not None:
            return
        try:
            started = now_jst()
            existing = (
                self.session_store.existing_session_ids(started.strftime("%Y%m%d"))
                if self.session_store is not None
                else ()
            )
            session = start_session(self.config, started_at=started, existing_ids=existing)
            self.session = session
            session_db_logger.info(
                "PlayCueSession started session_id=%s game_id=%s",
                session.session_id,
                session.game_id,
            )
            if self.session_store is not None:
                self.session_store.insert_session(session)
        except Exception:  # pragma: no cover - 補助機能。本体は落とさない。
            session_db_logger.error("PlayCueDB failed to begin session reason=begin_error")

    def _finish_session_log(self, *, show_dialog: bool, status: str = "finished") -> None:
        """セッションを終了させ、終了時メモを反映して DB を更新する。"""
        session = self.session
        if session is None:
            return
        self.session = None
        try:
            finish_session(session, now_jst(), status=status)
            memo = (
                ask_session_memo(self.root, session.game_name)
                if show_dialog
                else default_memo()
            )
            session.mode = memo.get("mode") or None
            session.build_or_deck_id = memo.get("build_or_deck_id") or None
            session.result = str(memo.get("result") or "unknown")
            session.score = memo.get("score") or None
            session.advice_id = memo.get("advice_id") or None
            session.memo = memo.get("memo") or None
            session.privacy_level = str(memo.get("privacy_level") or "local_only")
            session_db_logger.info(
                "PlayCueSession finished session_id=%s duration_sec=%s result=%s",
                session.session_id,
                session.duration_sec,
                session.result,
            )
            if self.session_store is not None:
                self.session_store.update_session_finish(
                    session.session_id,
                    {
                        "ended_at": session.ended_at,
                        "duration_sec": session.duration_sec,
                        "status": session.status,
                        "updated_at": session.updated_at,
                        "mode": session.mode,
                        "build_or_deck_id": session.build_or_deck_id,
                        "result": session.result,
                        "score": session.score,
                        "memo": session.memo,
                        "advice_id": session.advice_id,
                        "privacy_level": session.privacy_level,
                    },
                )
        except Exception:  # pragma: no cover - 補助機能。本体は落とさない。
            session_db_logger.error(
                "PlayCueDB failed to finish session session_id=%s reason=finish_error",
                session.session_id,
            )

    def save_log_once(self) -> None:
        if self.config is None or self.log_saved:
            return
        try:
            self.logger.save(self.config, self.session_start, self.current_elapsed_seconds())
            self.log_saved = True
            self._invalidate_history_cache()
        except OSError:
            # Do not include exc in the message — OSError strings contain local
            # absolute paths (e.g. "Permission denied: 'C:\\Users\\...\\logs\\...'")
            # which must not be shown to users or appear in bug reports.
            messagebox.showerror(tr("log_save_error"), tr("log_save_error_message"))
