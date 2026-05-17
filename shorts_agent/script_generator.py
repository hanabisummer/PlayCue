from __future__ import annotations

import re


def generate_youtube_script(analysis: dict, config: dict) -> dict:
    max_chars = int(config.get("max_script_length_chars", 350))
    summary = analysis.get("summary", "ゲーム中の盛り上がり場面。")
    angle = analysis.get("recommended_angle", "見どころを短く紹介する")
    narration = (
        "ここ、かなり注目なのだ。\n"
        f"{summary}\n"
        "音が大きくなっているところは、だいたい重要な展開が起きている合図なのだ。\n"
        f"今回は、{angle}のだ。\n"
        "短い場面だけど、流れが変わる瞬間として見てほしいのだ。"
    )
    narration = narration[:max_chars]
    return {
        "title_candidates": ["音量が跳ねた決定的瞬間", "ここから流れが変わるのだ"],
        "narration": narration,
        "description": re.sub(r"\s+", " ", summary).strip(),
        "hashtags": ["#ゲーム実況", "#攻略", "#Shorts"],
    }


def script_to_markdown(clip_id: str, script: dict) -> str:
    titles = "\n".join(f"- {title}" for title in script.get("title_candidates", []))
    hashtags = " ".join(script.get("hashtags", []))
    return (
        f"# {clip_id} 台本\n\n"
        f"## タイトル候補\n{titles}\n\n"
        f"## ナレーション\n{script.get('narration', '')}\n\n"
        f"## 概要欄\n{script.get('description', '')}\n\n"
        f"## ハッシュタグ\n{hashtags}\n"
    )

