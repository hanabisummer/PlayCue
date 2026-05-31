from __future__ import annotations

import ctypes
import ctypes.wintypes
import os

from playcue.models import GameConfig, LoginBonusSourceConfig

try:
    from PIL import ImageGrab
except ImportError:  # pragma: no cover - optional OCR support
    ImageGrab = None

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional OCR support
    pytesseract = None


class LoginBonusChecker:
    _ocr_available: bool | None = None

    def check(self, config: GameConfig, source_name: str) -> tuple[str, str, str]:
        source = self.source_config(config, source_name)
        if source is None or not config.login_bonus.enabled or not source.enabled:
            return "unknown", "", "disabled"
        text, method = self._read_source_text(source)
        if not text:
            return "unknown", "", method
        return self._match_text(text, source)

    @staticmethod
    def source_config(config: GameConfig, source_name: str) -> LoginBonusSourceConfig | None:
        """Return the LoginBonusSourceConfig for the given source name, or None."""
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
