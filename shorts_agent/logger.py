from __future__ import annotations

from datetime import datetime
from pathlib import Path


class ProcessingLogger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def warning(self, message: str) -> None:
        self._write("WARN", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def _write(self, level: str, message: str) -> None:
        line = f"{datetime.now().isoformat(timespec='seconds')} [{level}] {message}\n"
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line)

