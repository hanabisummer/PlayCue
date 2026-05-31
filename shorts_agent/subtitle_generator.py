from __future__ import annotations

import math
import wave
from pathlib import Path


def generate_srt(script_text: str, audio_path: Path | None, output_path: Path, max_chars_per_line: int = 18) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    chunks = _split_text(script_text, max_chars_per_line)
    duration = _audio_duration(audio_path) if audio_path and audio_path.exists() else _estimate_duration(script_text)
    per_chunk = max(1.5, duration / max(1, len(chunks)))
    lines = []
    current = 0.0
    for index, chunk in enumerate(chunks, start=1):
        start = current
        end = min(duration, current + per_chunk)
        lines.append(f"{index}\n{_fmt_srt(start)} --> {_fmt_srt(end)}\n{chunk}\n")
        current = end
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def generate_ass(script_text: str, audio_path: Path | None, output_path: Path, config: dict) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    chunks = _split_text(script_text, int(config.get("max_chars_per_line", 18)))
    duration = _audio_duration(audio_path) if audio_path and audio_path.exists() else _estimate_duration(script_text)
    per_chunk = max(1.5, duration / max(1, len(chunks)))
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{config.get('font_name', 'Noto Sans CJK JP')},{config.get('font_size', 72)},"
        f"&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,"
        f"{config.get('outline', 4)},{config.get('shadow', 2)},2,80,80,160,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = []
    current = 0.0
    for chunk in chunks:
        end = min(duration, current + per_chunk)
        ass_text = chunk.replace(chr(10), r"\N")
        events.append(f"Dialogue: 0,{_fmt_ass(current)},{_fmt_ass(end)},Default,,0,0,0,,{ass_text}")
        current = end
    output_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return output_path


def _split_text(text: str, max_chars: int) -> list[str]:
    clean = " ".join(line.strip() for line in text.splitlines() if line.strip())
    chunks = []
    for i in range(0, len(clean), max_chars):
        chunks.append(clean[i : i + max_chars])
    return chunks or [""]


def _audio_duration(audio_path: Path | None) -> float:
    if audio_path is None:
        return 0.0
    with wave.open(str(audio_path), "rb") as wav:
        return wav.getnframes() / float(wav.getframerate())


def _estimate_duration(text: str) -> float:
    return max(8.0, min(60.0, len(text) / 7.5))


def _fmt_srt(seconds: float) -> str:
    millis = int((seconds - math.floor(seconds)) * 1000)
    whole = int(seconds)
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"


def _fmt_ass(seconds: float) -> str:
    centis = int((seconds - math.floor(seconds)) * 100)
    whole = int(seconds)
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}.{centis:02d}"

