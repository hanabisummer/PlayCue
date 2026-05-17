from __future__ import annotations

from pathlib import Path

from .ffmpeg_utils import escape_filter_path, require_tool, run_command
from .source_guard import assert_safe_output_path


def render_final_video(
    video_clip: Path,
    voice_wav: Path | None,
    subtitle_file: Path | None,
    output_path: Path,
    config: dict,
    outputs_root: Path,
    log_path: Path | None = None,
) -> Path:
    require_tool("ffmpeg")
    assert_safe_output_path(video_clip, output_path, outputs_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    original_volume = str(config.get("original_audio_volume", 0.35))
    voice_volume = str(config.get("voice_volume", 1.0))

    if voice_wav and voice_wav.exists():
        temp_mixed = output_path.parent / f"{output_path.stem}_mixed.mp4"
        run_command(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_clip),
                "-i",
                str(voice_wav),
                "-filter_complex",
                f"[0:a]volume={original_volume}[a0];[1:a]volume={voice_volume}[a1];"
                "[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[aout]",
                "-map",
                "0:v",
                "-map",
                "[aout]",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                str(temp_mixed),
            ],
            log_path=log_path,
        )
        input_for_subtitle = temp_mixed
    else:
        input_for_subtitle = video_clip

    if subtitle_file and subtitle_file.exists() and subtitle_file.suffix.lower() == ".ass":
        run_command(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(input_for_subtitle),
                "-vf",
                f"ass='{escape_filter_path(subtitle_file)}'",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                str(output_path),
            ],
            log_path=log_path,
        )
    else:
        if input_for_subtitle != output_path:
            run_command(["ffmpeg", "-y", "-i", str(input_for_subtitle), "-c", "copy", str(output_path)], log_path=log_path)
    return output_path

