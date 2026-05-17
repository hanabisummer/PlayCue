from __future__ import annotations

from pathlib import Path

import requests


def check_voicevox(engine_url: str) -> bool:
    try:
        response = requests.get(f"{engine_url.rstrip('/')}/speakers", timeout=5)
        return response.ok
    except requests.RequestException:
        return False


def synthesize_voice(text: str, output_wav: Path, speaker_id: int, config: dict) -> Path:
    engine_url = str(config.get("engine_url", "http://127.0.0.1:50021")).rstrip("/")
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    query_response = requests.post(
        f"{engine_url}/audio_query",
        params={"text": text, "speaker": speaker_id},
        timeout=20,
    )
    query_response.raise_for_status()
    query = query_response.json()
    for key in [
        "speedScale",
        "pitchScale",
        "intonationScale",
        "volumeScale",
        "prePhonemeLength",
        "postPhonemeLength",
    ]:
        snake = _camel_to_snake(key)
        if snake in config:
            query[key] = config[snake]
    synth_response = requests.post(
        f"{engine_url}/synthesis",
        params={"speaker": speaker_id},
        json=query,
        timeout=60,
    )
    synth_response.raise_for_status()
    output_wav.write_bytes(synth_response.content)
    return output_wav


def _camel_to_snake(value: str) -> str:
    result = ""
    for char in value:
        if char.isupper() and result:
            result += "_"
        result += char.lower()
    return result

