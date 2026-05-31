from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, ttk
import tkinter as tk
import tkinter.font as tkfont

try:
    import psutil
except ImportError:  # pragma: no cover - optional runtime dep
    psutil = None

from playcue.config.loader import ConfigLoader
from playcue.config.serializer import (
    config_filename,
    login_bonus_config_to_dict,
    obs_config_to_dict,
)
from playcue.search.game_site_searcher import GameSiteSearcher
from playcue.ui.i18n import tr
from playcue.models import (
    GameConfig,
    LinkItem,
    LoginBonusConfig,
    OBSConfig,
)
from playcue.paths import config_dir

CONFIG_DIR = config_dir()


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
        self.game_args_var = tk.StringVar()
        self.active_process_name_var = tk.StringVar()
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

        ttk.Label(frame, text=tr("game_args")).pack(anchor=tk.W)
        ttk.Entry(frame, textvariable=self.game_args_var).pack(fill=tk.X, pady=(0, 2))
        ttk.Label(frame, text=tr("game_args_desc"), foreground="#9aa9c4", wraplength=560).pack(anchor=tk.W, pady=(0, 8))

        ttk.Label(frame, text=tr("active_process_name_label")).pack(anchor=tk.W)
        ttk.Entry(frame, textvariable=self.active_process_name_var).pack(fill=tk.X, pady=(0, 2))
        ttk.Label(frame, text=tr("active_process_name_desc"), foreground="#9aa9c4", wraplength=560).pack(anchor=tk.W, pady=(0, 8))

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
        self.game_args_var.set(config.game_args)
        self.active_process_name_var.set(config.active_process_name)
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
            messagebox.showinfo(tr("process_detect_title"), tr("process_detect_found", name=detected_name), parent=self.window)
            return
        messagebox.showwarning(tr("process_detect_title"), tr("process_detect_not_found"), parent=self.window)

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
            messagebox.showwarning(tr("input_error"), tr("game_input_error_name"), parent=self.window)
            return
        if not exe_path or not Path(exe_path).exists():
            messagebox.showwarning(tr("input_error"), tr("game_input_error_exe"), parent=self.window)
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
            "game_args": self.game_args_var.get().strip(),
            "launch_unelevated": self.config.launch_unelevated if self.config is not None else False,
            "process_name": process_name,
            "active_process_name": self.active_process_name_var.get().strip(),
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
        except (OSError, ValueError, json.JSONDecodeError):
            # Do not include exc — OSError strings may contain local absolute paths.
            messagebox.showerror(
                tr("game_create_error"),
                tr("config_save_failed", filename=config_path.name),
                parent=self.window,
            )
            return
        self.window.destroy()
