from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}


DEFAULT_CONFIG: dict[str, Any] = {
    "input": {"mode": "file", "path": "", "recursive": False},
    "output": {"base_dir": "outputs", "overwrite_existing_outputs": False, "create_unique_output_dir": True},
    "source_protection": {
        "enabled": True,
        "calculate_hash_before": True,
        "calculate_hash_after": True,
        "hash_algorithm": "sha256",
        "fail_if_source_changed": True,
        "forbid_output_to_source_dir": False,
        "forbid_same_input_output_path": True,
    },
    "clip_detection": {
        "method": "audio_peak",
        "clip_duration_sec": 60,
        "pre_peak_sec": 20,
        "post_peak_sec": 40,
        "min_gap_between_clips_sec": 90,
        "max_clips_per_video": 5,
        "min_clips_per_video": 1,
        "volume_window_sec": 2,
        "peak_threshold_percentile": 90,
        "ignore_first_sec": 30,
        "ignore_last_sec": 30,
    },
    "video_output": {
        "target_format": "mp4",
        "target_aspect": "vertical_9_16",
        "vertical_mode": "blur_background",
        "resolution": "1080x1920",
        "fps": 30,
        "video_codec": "libx264",
        "audio_codec": "aac",
        "crf": 20,
        "preset": "medium",
    },
    "ai_analysis": {"enabled": True, "provider": "openai", "model": "gpt-4.1-mini"},
    "script_generation": {
        "enabled": True,
        "language": "ja",
        "speaker": "zundamon",
        "max_script_length_chars": 350,
    },
    "voicevox": {
        "enabled": True,
        "engine_url": "http://127.0.0.1:50021",
        "speaker_id": 3,
        "speed_scale": 1.15,
        "pitch_scale": 0.0,
        "intonation_scale": 1.0,
        "volume_scale": 1.0,
        "pre_phoneme_length": 0.1,
        "post_phoneme_length": 0.1,
    },
    "subtitle": {
        "enabled": True,
        "format": "ass",
        "font_name": "Noto Sans CJK JP",
        "font_size": 72,
        "outline": 4,
        "shadow": 2,
        "position": "bottom",
        "max_chars_per_line": 18,
        "burn_in": True,
    },
    "final_mix": {"duck_original_audio": True, "original_audio_volume": 0.35, "voice_volume": 1.0},
    "logging": {"level": "INFO", "save_json_metadata": True, "save_text_log": True},
}


@dataclass
class AgentConfig:
    data: dict[str, Any] = field(default_factory=lambda: deep_merge({}, DEFAULT_CONFIG))

    @classmethod
    def load(cls, path: Path | None = None) -> "AgentConfig":
        if path is None:
            return cls()
        with path.open("r", encoding="utf-8") as f:
            user_config = json.load(f)
        return cls(deep_merge(DEFAULT_CONFIG, user_config))

    def with_input(self, input_path: Path) -> "AgentConfig":
        data = deep_merge({}, self.data)
        data["input"]["mode"] = "dir" if input_path.is_dir() else "file"
        data["input"]["path"] = str(input_path)
        return AgentConfig(data)

    def input_videos(self) -> list[Path]:
        raw_path = self.data["input"].get("path", "")
        if not raw_path:
            raise ValueError("input.path が未指定です")
        input_path = Path(raw_path).expanduser().resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"入力が見つかりません: {input_path}")
        if input_path.is_file():
            if input_path.suffix.lower() not in VIDEO_EXTENSIONS:
                raise ValueError(f"未対応の動画形式です: {input_path.suffix}")
            return [input_path]
        pattern = "**/*" if self.data["input"].get("recursive", False) else "*"
        videos = sorted(p for p in input_path.glob(pattern) if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS)
        if not videos:
            raise FileNotFoundError(f"対象動画が見つかりません: {input_path}")
        return videos


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

