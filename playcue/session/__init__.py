"""ゲーム攻略AIシステム Phase 1: PlayCue プレイセッションログ基盤。

既存の CSV 履歴 (``playcue.logs``) はそのまま維持しつつ、1プレイ単位の
セッションを SQLite (``play_logs.db``) に正本ログとして保存するための
モジュール群。

- :mod:`playcue.session.session` — セッションID生成・セッションモデル
- :mod:`playcue.session.db` — SQLite 保存 (SessionStore)
- :mod:`playcue.session.dialog` — 終了時メモ入力ダイアログ
"""

from __future__ import annotations

from .session import (
    GameSession,
    finish_session,
    generate_session_id,
    now_jst,
    start_session,
)
from .db import SessionStore

__all__ = [
    "GameSession",
    "SessionStore",
    "finish_session",
    "generate_session_id",
    "now_jst",
    "start_session",
]
