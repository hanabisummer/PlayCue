from __future__ import annotations

import wave
from pathlib import Path

from .ffmpeg_utils import require_tool, run_command


def extract_audio_to_temp_wav(source_path: Path, temp_dir: Path, log_path: Path | None = None) -> Path:
    require_tool("ffmpeg")
    temp_dir.mkdir(parents=True, exist_ok=True)
    wav_path = temp_dir / f"{source_path.stem}_audio.wav"
    run_command(
        ["ffmpeg", "-y", "-i", str(source_path), "-vn", "-ac", "1", "-ar", "44100", str(wav_path)],
        log_path=log_path,
    )
    return wav_path


def analyze_rms(wav_path: Path, window_sec: float) -> list[dict]:
    with wave.open(str(wav_path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        framerate = wav.getframerate()
        if channels != 1 or sample_width not in {1, 2, 4}:
            raise ValueError("解析用WAVはモノラル、8/16/32bit PCMである必要があります")
        window_frames = max(1, int(framerate * window_sec))
        data = []
        index = 0
        while True:
            frames = wav.readframes(window_frames)
            if not frames:
                break
            rms = _rms_pcm(frames, sample_width)
            data.append({"start_sec": index * window_sec, "end_sec": (index + 1) * window_sec, "rms": rms})
            index += 1
        return data


def _rms_pcm(frames: bytes, sample_width: int) -> float:
    if not frames:
        return 0.0
    signed = sample_width != 1
    count = len(frames) // sample_width
    if count == 0:
        return 0.0
    total = 0.0
    max_abs = float(2 ** (8 * sample_width - 1))
    for i in range(count):
        sample = int.from_bytes(frames[i * sample_width : (i + 1) * sample_width], "little", signed=signed)
        if sample_width == 1:
            sample -= 128
            max_abs = 128.0
        total += sample * sample
    return (total / count) ** 0.5 / max_abs

