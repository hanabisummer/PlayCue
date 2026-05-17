from __future__ import annotations

from pathlib import Path

from .ffmpeg_utils import require_tool, run_command
from .source_guard import assert_safe_output_path


def format_for_shorts(input_clip: Path, output_clip: Path, mode: str, config: dict, outputs_root: Path, log_path: Path | None = None) -> Path:
    require_tool("ffmpeg")
    assert_safe_output_path(input_clip, output_clip, outputs_root)
    output_clip.parent.mkdir(parents=True, exist_ok=True)
    width, height = _parse_resolution(config.get("resolution", "1080x1920"))
    codec = config.get("video_codec", "libx264")
    audio_codec = config.get("audio_codec", "aac")
    crf = str(config.get("crf", 20))
    preset = str(config.get("preset", "medium"))

    if mode == "center_crop":
        vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={config.get('fps', 30)}"
    elif mode == "fit_with_padding":
        vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={config.get('fps', 30)}"
    else:
        vf = (
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},boxblur=20:1[bg];"
            f"[0:v]scale={width}:-1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps={config.get('fps', 30)}"
        )
        return _run_complex(input_clip, output_clip, vf, codec, audio_codec, crf, preset, log_path)

    run_command(
        ["ffmpeg", "-y", "-i", str(input_clip), "-vf", vf, "-c:v", codec, "-preset", preset, "-crf", crf, "-c:a", audio_codec, str(output_clip)],
        log_path=log_path,
    )
    return output_clip


def _run_complex(input_clip: Path, output_clip: Path, filter_complex: str, codec: str, audio_codec: str, crf: str, preset: str, log_path: Path | None) -> Path:
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_clip),
            "-filter_complex",
            filter_complex,
            "-c:v",
            codec,
            "-preset",
            preset,
            "-crf",
            crf,
            "-c:a",
            audio_codec,
            str(output_clip),
        ],
        log_path=log_path,
    )
    return output_clip


def _parse_resolution(value: str) -> tuple[int, int]:
    left, right = value.lower().split("x", 1)
    return int(left), int(right)

