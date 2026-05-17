from __future__ import annotations

from pathlib import Path

from .ffmpeg_utils import require_tool, run_command


def sample_frames(clip_path: Path, output_dir: Path, interval_sec: int, log_path: Path | None = None) -> list[Path]:
    require_tool("ffmpeg")
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "frame_%03d.jpg"
    run_command(["ffmpeg", "-y", "-i", str(clip_path), "-vf", f"fps=1/{interval_sec}", str(pattern)], log_path=log_path)
    return sorted(output_dir.glob("frame_*.jpg"))


def analyze_clip_content(clip_id: str, candidate: dict, frames: list[Path], config: dict) -> dict:
    return {
        "clip_id": clip_id,
        "summary": f"音量ピーク {candidate['peak_time_sec']} 秒付近の盛り上がり場面。",
        "highlight_points": [
            "音量が大きく、リアクションや重要イベントが起きている可能性が高い",
            "短いショート動画として切り出しやすい区間",
        ],
        "recommended_angle": "音量が上がった瞬間を起点に、何が起きたかを短く紹介する",
        "viewer_hook": "いまの場面、かなり見どころなのだ。",
        "content_warning": [],
        "sampled_frames": [str(path) for path in frames],
    }

