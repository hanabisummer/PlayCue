from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
from tkinter import Tk, messagebox, ttk
import tkinter as tk

from datetime import datetime  # re-export for tests

from playcue.config.loader import ConfigLoader
from playcue.search.game_site_searcher import GameSiteSearcher  # re-export for tests
from playcue.system.console import ConsoleController
from playcue.models import (
    GameConfig,
    LoginBonusSourceConfig,  # re-export for tests
)
from playcue.paths import (
    app_base_dir,
    config_dir,
    resolve_app_path,
    script_path,
)
from playcue.ui.app import ResidentPlayCueApp

BASE_DIR = app_base_dir()
CONFIG_DIR = config_dir()
ELEVATED_FLAG = "--elevated"
# example.json is a public sample config — never treat it as a real game entry.
EXAMPLE_CONFIG_NAME = "example.json"


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
        return ConfigLoader.load(resolve_app_path(args[0]))

    configs = ConfigLoader.list_configs()
    if not configs:
        raise FileNotFoundError(f"configs フォルダにJSON設定がありません: {CONFIG_DIR}")
    return choose_config(configs)


def resolve_configs(argv: list[str]) -> tuple[list[GameConfig], list[str]]:
    """Return (configs, warning_lines).

    Tolerates individual broken JSON files — errors are collected as
    warning_lines and the remaining valid configs are returned.
    Raises only when *no* valid config can be loaded.
    """
    args = [arg for arg in argv[1:] if arg != ELEVATED_FLAG]
    if args:
        config_path = resolve_app_path(args[0])
        config = ConfigLoader.load(config_path)
        return [config], []

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    result = ConfigLoader.list_configs_with_issues(CONFIG_DIR)
    # Filter out example.json — it is a public sample, not a personal game config.
    configs = [c for c in result.configs if c.config_file.name != EXAMPLE_CONFIG_NAME]
    error_issues = [i for i in result.issues if i.level == "error"]
    warning_lines = [f"- {i.file}: {i.message}" for i in error_issues]
    return configs, warning_lines


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
        script = str(script_path())
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
        configs, warning_lines = resolve_configs(sys.argv)
    except (OSError, ValueError, json.JSONDecodeError):
        root = Tk()
        root.withdraw()
        messagebox.showerror(
            "設定エラー",
            "読み込めるゲーム設定がありません。\nconfigs フォルダ内の JSON 設定を確認してください。",
        )
        root.destroy()
        return 1

    # 設定ゼロは異常ではなく「初回起動」。アプリを起動し、ResidentPlayCueApp が
    # セットアップウィザードを開く（playcue/ui/app.py の _open_initial_wizard）。
    # 致命的エラーで終了するのは、明示指定したファイルが壊れている場合のみ（上の except）。
    root = Tk()
    app = ResidentPlayCueApp(root, configs)
    if warning_lines:
        if configs:
            intro = "一部の設定ファイルを読み込めませんでした。"
            outro = "正常に読み込めた設定のみで起動します。"
        else:
            intro = "読み込めた設定ファイルがありませんでした。"
            outro = "新しいゲームを追加してください。"
        body = f"{intro}\n\n" + "\n".join(warning_lines) + f"\n\n{outro}"
        root.after(300, lambda: messagebox.showwarning("設定読み込み警告", body))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
