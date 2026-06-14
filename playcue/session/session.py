"""セッションID生成とセッション状態モデル。

Phase 1 では画像認識・RAG・LLM 連携は扱わず、1プレイ単位の開始/終了/
プレイ時間/終了時メモだけを表現する。タイムゾーンは Asia/Tokyo 固定。
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Iterable

try:  # Python 3.9+ 標準。Windows でデータ未配置の場合に備えて fallback する。
    from zoneinfo import ZoneInfo

    _JST = ZoneInfo("Asia/Tokyo")
except Exception:  # pragma: no cover - tzdata 不在環境向けフォールバック
    _JST = timezone(timedelta(hours=9), name="JST")

if TYPE_CHECKING:  # 循環 import 回避（実行時は models を import しない）
    from playcue.models import GameConfig

DEFAULT_PREFIX = "GAME"

VALID_RESULTS = ("win", "lose", "clear", "failed", "draw", "unknown")
VALID_PRIVACY_LEVELS = ("local_only", "sanitized", "exportable")


def now_jst() -> datetime:
    """Asia/Tokyo のタイムゾーン付き現在時刻。"""
    return datetime.now(_JST)


def _to_jst(value: datetime) -> datetime:
    """naive な datetime は JST とみなし、aware ならそのまま JST へ変換する。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=_JST)
    return value.astimezone(_JST)


def _derive_prefix(game_id: str) -> str:
    """``game_id`` からセッションIDの接頭辞を決定的に導出する。

    ルール:
      0. 英数字以外を除いた ``game_id`` が5文字以内なら、母音を落とさず
         そのまま（大文字化）使う。
      1. それ以外は区切り (英数字以外) で単語に分割する。
      2. 各単語の先頭3文字を取り出す。
      3. 母音 (a/e/i/o/u) を落とす。ただし単語の先頭1文字が母音でも残す。
      4. 連結して大文字化し、先頭5文字までに切り詰める。

    例:
        "rip"            -> 5文字以内         -> "RIP"
        "shadowverse-wb" -> ["sha","wb"]     -> ["sh","wb"]  -> "SHWB"
        "ff7-rebirth"    -> ["ff7","reb"]    -> ["ff7","rb"] -> "FF7RB"
        "elden-ring"     -> ["eld","rin"]    -> ["eld","rn"] -> "ELDRN"

    空になる場合（例: 空文字）は ``DEFAULT_PREFIX`` を返す。
    """
    vowels = frozenset("aeiou")
    cleaned = re.sub(r"[^0-9a-zA-Z]", "", game_id)
    if len(cleaned) <= 5:
        return cleaned.upper() or DEFAULT_PREFIX

    chars: list[str] = []
    for word in re.split(r"[^0-9a-zA-Z]+", game_id):
        if not word:
            continue
        for index, ch in enumerate(word[:3]):
            # 先頭1文字は母音でも残し、それ以外の母音だけ落とす。
            if index == 0 or ch.lower() not in vowels:
                chars.append(ch)
    prefix = "".join(chars)[:5].upper()
    return prefix or DEFAULT_PREFIX


def generate_session_id(
    game_id: str,
    started_at: datetime,
    *,
    prefix: str | None = None,
    existing_ids: Iterable[str] = (),
) -> str:
    """``<PREFIX>-YYYYMMDD-HHMMSS`` 形式のセッションIDを生成する。

    Args:
        game_id: ゲーム識別子。``prefix`` 未指定時の接頭辞導出元。
        started_at: セッション開始時刻（naive は JST とみなす）。
        prefix: 明示する接頭辞。空/None なら ``game_id`` から導出。
        existing_ids: 既存セッションID。同秒衝突時は ``-01``/``-02`` を付与する。

    Returns:
        既存と衝突しない一意なセッションID。
    """
    resolved_prefix = (prefix or "").strip().upper() or _derive_prefix(game_id)
    timestamp = _to_jst(started_at).strftime("%Y%m%d-%H%M%S")
    base = f"{resolved_prefix}-{timestamp}"

    existing = set(existing_ids)
    if base not in existing:
        return base
    # 同秒起動の衝突対策: -01, -02, ... を付与する。
    for suffix in range(1, 100):
        candidate = f"{base}-{suffix:02d}"
        if candidate not in existing:
            return candidate
    # 100 件衝突は現実的に起きないが、最後の砦としてマイクロ秒を足す。
    return f"{base}-{_to_jst(started_at).strftime('%f')}"


@dataclass
class GameSession:
    """1プレイ単位のセッション情報。``sessions`` テーブルの1行に対応する。"""

    session_id: str
    game_id: str
    game_name: str
    started_at: str
    ended_at: str | None = None
    duration_sec: int | None = None
    mode: str | None = None
    build_or_deck_id: str | None = None
    result: str = "unknown"
    score: str | None = None
    memo: str | None = None
    advice_id: str | None = None
    privacy_level: str = "local_only"
    status: str = "started"
    created_at: str = ""
    updated_at: str = ""

    def to_row(self) -> dict[str, object]:
        """SQLite 保存用の dict に変換する。"""
        return asdict(self)


def start_session(
    game: "GameConfig",
    *,
    started_at: datetime | None = None,
    existing_ids: Iterable[str] = (),
) -> GameSession:
    """ゲーム起動時の開始セッションを生成する（DB 保存はしない）。"""
    start = _to_jst(started_at) if started_at is not None else now_jst()
    game_id = game.get_game_id()
    prefix = game.session_prefix or None
    session_id = generate_session_id(
        game_id, start, prefix=prefix, existing_ids=existing_ids
    )
    timestamp = start.isoformat(timespec="seconds")
    return GameSession(
        session_id=session_id,
        game_id=game_id,
        game_name=game.game_name,
        started_at=timestamp,
        status="started",
        created_at=timestamp,
        updated_at=timestamp,
    )


def finish_session(
    session: GameSession,
    end_time: datetime | None = None,
    *,
    status: str = "finished",
) -> GameSession:
    """終了時刻と duration を計算し、``session`` を更新して返す（破壊的更新）。

    開始時刻のパースに失敗した場合でも例外を投げず、``duration_sec`` は
    そのまま None にして ``status`` を更新する（PlayCue 本体を落とさない方針）。
    """
    end = _to_jst(end_time) if end_time is not None else now_jst()
    session.ended_at = end.isoformat(timespec="seconds")
    session.updated_at = session.ended_at
    session.status = status
    try:
        start = datetime.fromisoformat(session.started_at)
        start = _to_jst(start)
        session.duration_sec = max(0, int((end - start).total_seconds()))
    except (ValueError, TypeError):
        session.duration_sec = None
    return session
