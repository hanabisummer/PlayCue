from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from shorts_agent.ai_analyzer import analyze_clip_content
from shorts_agent.audio_analyzer import analyze_rms, extract_audio_to_temp_wav
from shorts_agent.clip_cutter import cut_clip
from shorts_agent.clip_detector import detect_highlight_candidates
from shorts_agent.config import AgentConfig
from shorts_agent.ffmpeg_utils import probe_duration_sec, require_tool
from shorts_agent.final_renderer import render_final_video
from shorts_agent.logger import ProcessingLogger
from shorts_agent.metadata_writer import write_json
from shorts_agent.script_generator import generate_youtube_script, script_to_markdown
from shorts_agent.source_guard import collect_source_info, verify_source_unchanged
from shorts_agent.subtitle_generator import generate_ass, generate_srt
from shorts_agent.video_formatter import format_for_shorts
from shorts_agent.voicevox_client import check_voicevox, synthesize_voice


STAGES = {"detect", "cut", "script", "voice", "render", "all"}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = AgentConfig.load(Path(args.config) if args.config else None)
    if args.input:
        config = config.with_input(Path(args.input))
    if args.stage not in STAGES:
        raise ValueError(f"未知のstageです: {args.stage}")

    videos = config.input_videos()
    require_tool("ffmpeg")
    require_tool("ffprobe")
    if args.dry_run:
        return dry_run(config, videos)

    failures = 0
    for video in videos:
        try:
            process_video(video, config, args.stage)
        except Exception as exc:
            print(f"ERROR {video}: {exc}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="録画済みゲーム動画からショート動画を自動生成します。")
    parser.add_argument("--config", default=None, help="設定JSON")
    parser.add_argument("--input", default=None, help="入力動画またはフォルダ")
    parser.add_argument("--dry-run", action="store_true", help="動画生成せず安全確認のみ実行")
    parser.add_argument("--stage", default="all", choices=sorted(STAGES), help="実行ステージ")
    return parser.parse_args(argv)


def dry_run(config: AgentConfig, videos: list[Path]) -> int:
    print("dry-run")
    print(f"videos: {len(videos)}")
    for video in videos:
        output_root = build_output_root(video, config)
        print(f"- source: {video}")
        print(f"  output: {output_root}")
        print(f"  exists: {video.exists()}")
    ffmpeg_ok = bool(require_tool("ffmpeg"))
    ffprobe_ok = bool(require_tool("ffprobe"))
    print(f"ffmpeg: {ffmpeg_ok}")
    print(f"ffprobe: {ffprobe_ok}")
    vv = config.data["voicevox"]
    print(f"voicevox: {check_voicevox(vv['engine_url']) if vv.get('enabled', True) else 'disabled'}")
    return 0


def process_video(source_path: Path, config: AgentConfig, stage: str) -> None:
    output_root = build_output_root(source_path, config)
    create_dirs(output_root)
    logger = ProcessingLogger(output_root / "processing_log.txt")
    logger.info(f"start source={source_path}")
    source_info = collect_source_info(
        source_path,
        calculate_hash=bool(config.data["source_protection"].get("calculate_hash_before", True)),
    )
    write_json(output_root / "source_info.json", source_info)
    summary = {"source_video": str(source_path), "source_unchanged": False, "generated_clips": [], "errors": []}

    try:
        candidates = load_or_detect_candidates(source_path, output_root, config, stage, logger)
        if stage == "detect":
            return
        for idx, candidate in enumerate(candidates, start=1):
            clip_id = f"clip_{idx:03d}"
            try:
                item = process_clip(source_path, output_root, clip_id, candidate, config, stage, logger)
                summary["generated_clips"].append(item)
            except Exception as exc:
                logger.error(f"{clip_id}: {exc}")
                summary["errors"].append({"clip_id": clip_id, "error": str(exc)})
    finally:
        after = verify_source_unchanged(
            source_info,
            source_path,
            calculate_hash=bool(config.data["source_protection"].get("calculate_hash_after", True)),
        )
        summary.update(after)
        if not after["source_unchanged"]:
            logger.error("元動画のハッシュまたはサイズが変化しました")
            if config.data["source_protection"].get("fail_if_source_changed", True):
                summary["errors"].append({"source": "source_changed"})
        write_json(output_root / "summary.json", summary)
        logger.info(f"done source_unchanged={after['source_unchanged']}")


def load_or_detect_candidates(source_path: Path, output_root: Path, config: AgentConfig, stage: str, logger: ProcessingLogger) -> list[dict]:
    candidates_path = output_root / "candidates" / "volume_candidates.json"
    if candidates_path.exists() and stage != "all":
        import json

        return json.loads(candidates_path.read_text(encoding="utf-8"))

    duration = probe_duration_sec(source_path)
    logger.info(f"duration={duration}")
    wav_path = extract_audio_to_temp_wav(source_path, output_root / "temp", output_root / "processing_log.txt")
    rms = analyze_rms(wav_path, float(config.data["clip_detection"].get("volume_window_sec", 2)))
    candidates = detect_highlight_candidates(rms, duration, config.data["clip_detection"])
    write_json(candidates_path, candidates)
    logger.info(f"candidates={len(candidates)}")
    return candidates


def process_clip(source_path: Path, output_root: Path, clip_id: str, candidate: dict, config: AgentConfig, stage: str, logger: ProcessingLogger) -> dict:
    output_config = config.data["output"]
    clip_config = {**output_config, **config.data["video_output"]}
    raw_clip = output_root / "clips" / f"{clip_id}_raw.mp4"
    vertical_clip = output_root / "vertical" / f"{clip_id}_vertical.mp4"
    analysis_path = output_root / "analysis" / f"{clip_id}_analysis.json"
    script_path = output_root / "scripts" / f"{clip_id}_script.md"
    voice_path = output_root / "voice" / f"{clip_id}_zundamon.wav"
    srt_path = output_root / "subtitles" / f"{clip_id}.srt"
    ass_path = output_root / "subtitles" / f"{clip_id}.ass"
    final_path = output_root / "final" / f"{clip_id}_final.mp4"

    if stage in {"cut", "all", "script", "voice", "render"}:
        cut_clip(
            source_path,
            candidate["start_time_sec"],
            candidate["duration_sec"],
            raw_clip,
            clip_config,
            output_root,
            output_root / "processing_log.txt",
        )
        format_for_shorts(
            raw_clip,
            vertical_clip,
            config.data["video_output"].get("vertical_mode", "blur_background"),
            config.data["video_output"],
            output_root,
            output_root / "processing_log.txt",
        )
    if stage == "cut":
        return clip_summary(clip_id, raw_clip, vertical_clip, script_path, None, ass_path, final_path, candidate)

    analysis = analyze_clip_content(clip_id, candidate, [], config.data["ai_analysis"])
    write_json(analysis_path, analysis)
    script = generate_youtube_script(analysis, config.data["script_generation"])
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script_to_markdown(clip_id, script), encoding="utf-8")
    narration = script["narration"]
    if stage == "script":
        return clip_summary(clip_id, raw_clip, vertical_clip, script_path, None, ass_path, final_path, candidate)

    voice_result: Path | None = None
    if config.data["voicevox"].get("enabled", True):
        try:
            if check_voicevox(config.data["voicevox"]["engine_url"]):
                voice_result = synthesize_voice(
                    narration,
                    voice_path,
                    int(config.data["voicevox"].get("speaker_id", 3)),
                    config.data["voicevox"],
                )
                logger.info(f"{clip_id}: voice generated")
            else:
                logger.warning(f"{clip_id}: VOICEVOX未接続のため音声生成をスキップ")
        except Exception as exc:
            logger.warning(f"{clip_id}: VOICEVOX音声生成失敗: {exc}")
    if stage == "voice":
        return clip_summary(clip_id, raw_clip, vertical_clip, script_path, voice_result, ass_path, final_path, candidate)

    subtitle_config = config.data["subtitle"]
    generate_srt(narration, voice_result, srt_path, int(subtitle_config.get("max_chars_per_line", 18)))
    subtitle_file = generate_ass(narration, voice_result, ass_path, subtitle_config)
    render_final_video(
        vertical_clip,
        voice_result,
        subtitle_file if subtitle_config.get("burn_in", True) else None,
        final_path,
        config.data["final_mix"],
        output_root,
        output_root / "processing_log.txt",
    )
    return clip_summary(clip_id, raw_clip, vertical_clip, script_path, voice_result, subtitle_file, final_path, candidate)


def clip_summary(
    clip_id: str,
    raw_clip: Path,
    vertical_clip: Path,
    script_path: Path,
    voice_path: Path | None,
    subtitle_path: Path,
    final_path: Path,
    candidate: dict,
) -> dict:
    return {
        "clip_id": clip_id,
        "raw_clip": str(raw_clip),
        "vertical_clip": str(vertical_clip),
        "final_clip": str(final_path),
        "start_time_sec": candidate["start_time_sec"],
        "end_time_sec": candidate["end_time_sec"],
        "script": str(script_path),
        "voice": str(voice_path) if voice_path else None,
        "subtitle": str(subtitle_path),
    }


def build_output_root(source_path: Path, config: AgentConfig) -> Path:
    base = Path(config.data["output"].get("base_dir", "outputs"))
    if not base.is_absolute():
        base = Path.cwd() / base
    root = base / source_path.stem
    if config.data["output"].get("create_unique_output_dir", True):
        return unique_dir(root)
    return root


def unique_dir(path: Path) -> Path:
    if not path.exists():
        return path
    index = 2
    while True:
        candidate = path.with_name(f"{path.name}_{index:02d}")
        if not candidate.exists():
            return candidate
        index += 1


def create_dirs(output_root: Path) -> None:
    for name in ["candidates", "clips", "vertical", "analysis", "scripts", "voice", "subtitles", "temp", "final"]:
        (output_root / name).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())

