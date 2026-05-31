from __future__ import annotations

import queue
import threading
from dataclasses import replace
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, ttk
import tkinter as tk

from playcue.ui.i18n import tr
from playcue.models import OBSConfig
from playcue.ui.theme import THEME


def _make_entry(parent: tk.Widget, textvariable: tk.StringVar, show: str | None = None) -> tk.Entry:
    """テーマカラーで選択ハイライトが見えるEntryを生成する。"""
    e = tk.Entry(
        parent,
        textvariable=textvariable,
        bg=THEME["panel"],
        fg=THEME["text"],
        insertbackground=THEME["text"],
        selectbackground=THEME["accent"],
        selectforeground=THEME["bg"],
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=THEME["border"],
        highlightcolor=THEME["accent"],
    )
    if show is not None:
        e.configure(show=show)
    return e


def _make_checkbutton(
    parent: tk.Widget,
    text: str,
    variable: tk.BooleanVar,
    **kwargs,
) -> tk.Checkbutton:
    """テーマカラーで視認性の高いCheckbuttonを生成する。"""
    return tk.Checkbutton(
        parent,
        text=text,
        variable=variable,
        bg=THEME["bg"],
        fg=THEME["text"],
        activebackground=THEME["panel_alt"],
        activeforeground=THEME["text"],
        selectcolor=THEME["panel_alt"],
        cursor="hand2",
        padx=4,
        pady=2,
        **kwargs,
    )


class OBSSettingsWindow:
    def __init__(self, parent: Tk, config: OBSConfig, on_saved):
        self.parent = parent
        self.config = config
        self.on_saved = on_saved
        self.window = tk.Toplevel(parent)
        self.window.title(tr("obs_settings"))
        self.enabled_var = tk.BooleanVar(value=config.enabled)
        self.exe_path_var = tk.StringVar(value=config.exe_path)
        self.process_name_var = tk.StringVar(value=config.process_name)
        self.websocket_host_var = tk.StringVar(value=config.websocket_host or "127.0.0.1")
        self.websocket_port_var = tk.StringVar(value=str(config.websocket_port))
        self.websocket_password_var = tk.StringVar(value=config.websocket_password)
        self.auto_launch_var = tk.BooleanVar(value=config.auto_launch)
        self.auto_start_recording_var = tk.BooleanVar(value=config.auto_start_recording_on_game_launch)
        self.auto_stop_recording_var = tk.BooleanVar(value=config.auto_stop_recording_on_game_exit)
        self._dependent_widgets: list[tk.Widget] = []
        self._test_result_label: ttk.Label | None = None
        self._build_ui()
        self.enabled_var.trace_add("write", self._on_enabled_changed)
        self._sync_dependent_state()
        self._fit_window_to_screen(540, 520)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # OBS有効/無効チェックボックス (v0.6-01)
        enable_frame = ttk.LabelFrame(frame, text=tr("obs_enable"))
        enable_frame.pack(fill=tk.X, pady=(0, 8))
        _make_checkbutton(
            enable_frame,
            text=tr("obs_enable"),
            variable=self.enabled_var,
        ).pack(anchor=tk.W, padx=6, pady=(4, 2))
        ttk.Label(
            enable_frame,
            text=tr("obs_enable_desc"),
            foreground="#9aa9c4",
            wraplength=480,
        ).pack(anchor=tk.W, padx=6, pady=(0, 6))

        ttk.Label(frame, text=tr("obs_exe_path")).pack(anchor=tk.W)
        exe_frame = ttk.Frame(frame)
        exe_frame.pack(fill=tk.X, pady=(0, 8))
        _make_entry(exe_frame, self.exe_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(exe_frame, text=tr("browse"), anchor=tk.W, command=self.browse_exe).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(frame, text=tr("process_name")).pack(anchor=tk.W)
        _make_entry(frame, self.process_name_var).pack(fill=tk.X, pady=(0, 10))

        websocket_frame = ttk.LabelFrame(frame, text=tr("websocket"))
        websocket_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(websocket_frame, text=tr("server_host")).pack(anchor=tk.W, padx=6, pady=(6, 0))
        _make_entry(websocket_frame, self.websocket_host_var).pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Label(websocket_frame, text=tr("server_port")).pack(anchor=tk.W, padx=6)
        _make_entry(websocket_frame, self.websocket_port_var).pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Label(websocket_frame, text=tr("server_password")).pack(anchor=tk.W, padx=6)
        _make_entry(websocket_frame, self.websocket_password_var, show="*").pack(
            fill=tk.X, padx=6, pady=(0, 6)
        )

        # OBS自動化 (v0.6-02 descriptions + disabled state)
        automation_frame = ttk.LabelFrame(frame, text=tr("obs_automation"))
        automation_frame.pack(fill=tk.X, pady=(0, 10))

        auto_launch_cb = _make_checkbutton(
            automation_frame,
            text=tr("obs_auto_launch"),
            variable=self.auto_launch_var,
        )
        auto_launch_cb.pack(anchor=tk.W, padx=6, pady=(4, 0))
        auto_launch_desc = ttk.Label(
            automation_frame,
            text=tr("obs_auto_launch_desc"),
            foreground="#9aa9c4",
            wraplength=480,
        )
        auto_launch_desc.pack(anchor=tk.W, padx=20, pady=(0, 4))

        auto_start_cb = _make_checkbutton(
            automation_frame,
            text=tr("obs_auto_start_recording"),
            variable=self.auto_start_recording_var,
        )
        auto_start_cb.pack(anchor=tk.W, padx=6, pady=(0, 0))
        auto_start_desc = ttk.Label(
            automation_frame,
            text=tr("obs_auto_start_recording_desc"),
            foreground="#9aa9c4",
            wraplength=480,
        )
        auto_start_desc.pack(anchor=tk.W, padx=20, pady=(0, 4))

        auto_stop_cb = _make_checkbutton(
            automation_frame,
            text=tr("obs_auto_stop_recording"),
            variable=self.auto_stop_recording_var,
        )
        auto_stop_cb.pack(anchor=tk.W, padx=6, pady=(0, 0))
        auto_stop_desc = ttk.Label(
            automation_frame,
            text=tr("obs_auto_stop_recording_desc"),
            foreground="#9aa9c4",
            wraplength=480,
        )
        auto_stop_desc.pack(anchor=tk.W, padx=20, pady=(0, 6))

        self._dependent_widgets = [auto_launch_cb, auto_start_cb, auto_stop_cb]

        button_row = ttk.Frame(frame)
        button_row.pack(fill=tk.X, pady=(0, 4))
        tk.Button(button_row, text=tr("update_settings"), anchor=tk.W, command=self.save).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        tk.Button(button_row, text=tr("obs_test_connection"), anchor=tk.W, command=self.test_connection).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0)
        )

        self._test_result_label = ttk.Label(frame, text="", foreground="#9aa9c4", wraplength=480)
        self._test_result_label.pack(anchor=tk.W)

    def _on_enabled_changed(self, *_args) -> None:
        self._sync_dependent_state()

    def _sync_dependent_state(self) -> None:
        state = tk.NORMAL if self.enabled_var.get() else tk.DISABLED
        for widget in self._dependent_widgets:
            widget.configure(state=state)

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
            messagebox.showwarning(tr("input_error"), tr("port_must_be_number"), parent=self.window)
            return
        if port <= 0:
            messagebox.showwarning(tr("input_error"), tr("port_must_be_positive"), parent=self.window)
            return
        if exe_path and not Path(exe_path).exists():
            messagebox.showwarning(tr("input_error"), tr("obs_exe_not_found"), parent=self.window)
            return

        updated = replace(
            self.config,
            enabled=self.enabled_var.get(),
            exe_path=exe_path,
            working_dir=str(Path(exe_path).parent) if exe_path else self.config.working_dir,
            process_name=process_name,
            websocket_host=host,
            websocket_port=port,
            websocket_password=self.websocket_password_var.get(),
            auto_launch=self.auto_launch_var.get(),
            auto_start_recording_on_game_launch=self.auto_start_recording_var.get(),
            auto_stop_recording_on_game_exit=self.auto_stop_recording_var.get(),
        )
        try:
            self.on_saved(updated)
        except OSError:
            # Do not include exc — OSError strings may contain local absolute paths.
            messagebox.showerror(tr("settings_update_error"), tr("config_save_failed", filename="obs_settings"), parent=self.window)
            return
        self.window.destroy()

    def test_connection(self) -> None:
        if not self.enabled_var.get():
            self._set_test_result(tr("obs_test_disabled"))
            return
        exe_path = self.exe_path_var.get().strip()
        if not exe_path:
            self._set_test_result(tr("obs_test_exe_missing"))
            return
        if not Path(exe_path).exists():
            self._set_test_result(tr("obs_test_exe_not_found"))
            return
        try:
            port = int(self.websocket_port_var.get().strip())
        except ValueError:
            self._set_test_result(tr("obs_test_port_invalid"))
            return
        if port <= 0:
            self._set_test_result(tr("obs_test_port_invalid"))
            return

        host = self.websocket_host_var.get().strip() or "127.0.0.1"
        password = self.websocket_password_var.get()
        self._set_test_result(tr("obs_test_running"))

        result_queue: queue.Queue[str] = queue.Queue()

        def worker() -> None:
            result_queue.put(self._run_obs_connection_test(host, port, password))

        def poll() -> None:
            try:
                result = result_queue.get_nowait()
            except queue.Empty:
                if self.window.winfo_exists():
                    self.window.after(100, poll)
                return
            self._set_test_result(result)

        threading.Thread(target=worker, daemon=True).start()
        self.window.after(100, poll)

    def _run_obs_connection_test(self, host: str, port: int, password: str) -> str:
        try:
            from obsws_python import ReqClient
        except ImportError:
            return tr("obs_test_failed")
        try:
            client = ReqClient(host=host, port=port, password=password, timeout=3)
            try:
                response = client.get_record_status()
                is_recording = bool(getattr(response, "output_active", getattr(response, "outputActive", False)))
                return tr("obs_test_connected_recording") if is_recording else tr("obs_test_connected_idle")
            except Exception:
                return tr("obs_test_failed")
        except Exception as exc:
            if "auth" in type(exc).__name__.lower():
                return tr("obs_test_auth_failed")
            return tr("obs_test_failed")

    def _set_test_result(self, message: str) -> None:
        if self._test_result_label is not None:
            self._test_result_label.configure(text=message)

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
