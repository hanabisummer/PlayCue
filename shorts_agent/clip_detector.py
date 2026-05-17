from __future__ import annotations


def detect_highlight_candidates(rms_data: list[dict], video_duration_sec: float, config: dict) -> list[dict]:
    if not rms_data:
        return []
    clip_duration = float(config.get("clip_duration_sec", 60))
    pre_peak = float(config.get("pre_peak_sec", 20))
    min_gap = float(config.get("min_gap_between_clips_sec", 90))
    max_clips = int(config.get("max_clips_per_video", 5))
    ignore_first = float(config.get("ignore_first_sec", 30))
    ignore_last = float(config.get("ignore_last_sec", 30))
    percentile = float(config.get("peak_threshold_percentile", 90))

    usable = [
        item
        for item in rms_data
        if item["start_sec"] >= ignore_first and item["end_sec"] <= max(0.0, video_duration_sec - ignore_last)
    ]
    if not usable:
        usable = rms_data
    threshold = _percentile([item["rms"] for item in usable], percentile)
    peaks = sorted((item for item in usable if item["rms"] > threshold), key=lambda x: x["rms"], reverse=True)
    if not peaks:
        max_rms = max(item["rms"] for item in usable)
        peaks = sorted((item for item in usable if item["rms"] == max_rms and max_rms > 0), key=lambda x: x["rms"], reverse=True)

    candidates: list[dict] = []
    for peak in peaks:
        peak_time = (peak["start_sec"] + peak["end_sec"]) / 2
        if any(abs(peak_time - existing["peak_time_sec"]) < min_gap for existing in candidates):
            continue
        start = max(0.0, min(peak_time - pre_peak, max(0.0, video_duration_sec - clip_duration)))
        end = min(video_duration_sec, start + clip_duration)
        candidates.append(
            {
                "candidate_id": len(candidates) + 1,
                "peak_time_sec": round(peak_time, 3),
                "start_time_sec": round(start, 3),
                "end_time_sec": round(end, 3),
                "duration_sec": round(end - start, 3),
                "rms_score": round(float(peak["rms"]), 6),
                "reason": "音量が大きいピーク区間",
            }
        )
        if len(candidates) >= max_clips:
            break
    return sorted(candidates, key=lambda x: x["start_time_sec"])


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((percentile / 100) * (len(ordered) - 1))))
    return ordered[index]
