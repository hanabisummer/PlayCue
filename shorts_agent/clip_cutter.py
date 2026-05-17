from __future__ import annotations

from pathlib import Path

from .ffmpeg_utils import require_tool, run_command
from .source_guard import assert_safe_output_path


def cut_clip(
    source_path: Path,
    start_sec: float,
    duration_sec: float,
    output_path: Path,
    config: dict,
    outputs_root: Path,
    log_path: Path | None = None,
) -> Path:
    require_tool("ffmpeg")
    assert_safe_output_path(source_path, output_path, outputs_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not config.get("overwrite_existing_outputs", False):
        return output_path
    run_command(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(start_sec),
            "-i",
            str(source_path),
            "-t",
            str(duration_sec),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(output_path),
        ],
        log_path=log_path,
    )
    return output_path

