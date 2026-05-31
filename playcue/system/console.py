from __future__ import annotations

import ctypes
import os

_SW_HIDE = 0
_SW_SHOW = 5


class ConsoleController:
    visible = True

    @staticmethod
    def set_visible(visible: bool) -> None:
        if os.name != "nt":
            return
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, _SW_SHOW if visible else _SW_HIDE)
            ConsoleController.visible = visible

    @staticmethod
    def toggle() -> None:
        ConsoleController.set_visible(not ConsoleController.visible)
