from __future__ import annotations

import ctypes
import os
import shlex
import subprocess
import webbrowser
from pathlib import Path
from tkinter import messagebox

from playcue.models import GameConfig, LinkItem


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


class GameLauncher:
    def launch_game(self, config: GameConfig) -> bool:
        """Return True if the game was launched (or has no exe configured).

        Returns False and shows an error dialog when the exe is configured but
        cannot be launched.  An empty game_exe is not an error — it means the
        game is launched externally and the watcher will detect the process.
        """
        if not config.game_exe:
            return True

        game_path = Path(config.game_exe)
        if not game_path.exists():
            messagebox.showerror("ゲーム起動エラー", f"exeが見つかりません: {game_path.name}")
            return False

        try:
            args = shlex.split(config.game_args, posix=False) if config.game_args else []
            if config.launch_unelevated and os.name == "nt" and _is_admin() and not args:
                subprocess.Popen(["explorer.exe", str(game_path)])
                return True
            subprocess.Popen([config.game_exe, *args], cwd=str(game_path.parent))
            return True
        except OSError:
            messagebox.showerror("ゲーム起動エラー", f"{config.game_name} の起動に失敗しました。")
            return False

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
