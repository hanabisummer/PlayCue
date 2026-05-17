from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise FileNotFoundError(f"{name} が見つかりません。PATHに追加してください。")
    return path


def run_command(args: list[str], log_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if log_path:
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n$ " + subprocess.list2cmdline(args) + "\n")
            if result.stdout:
                f.write(result.stdout)
            if result.stderr:
                f.write(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"外部コマンドが失敗しました: {subprocess.list2cmdline(args)}")
    return result


def probe_duration_sec(video_path: Path) -> float:
    require_tool("ffprobe")
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video_path),
        ]
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def escape_filter_path(path: Path) -> str:
    text = str(path.resolve()).replace("\\", "/")
    return text.replace(":", "\\:").replace("'", "\\'")

