"""``play_logs.db`` (SQLite) へのセッション保存を扱う。

方針（指示書 8.2 / 19）:
- DB 保存失敗時は例外を握りつぶさずログに記録するが、呼び出し側
  (PlayCue 本体) は落とさない。失敗の判断は戻り値 (bool) で返す。
- DB ロック時は短いリトライを入れる。
- 個人情報・OBS パスワード・ローカル絶対パス全文はログに出さない。
"""

from __future__ import annotations

import contextlib
import logging
import sqlite3
import time
from pathlib import Path

from .session import GameSession

logger = logging.getLogger("PlayCueDB")

_BUSY_TIMEOUT_SEC = 5.0
_RETRY_COUNT = 3
_RETRY_SLEEP_SEC = 0.2

_CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL,
    game_name TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_sec INTEGER,
    mode TEXT,
    build_or_deck_id TEXT,
    result TEXT DEFAULT 'unknown',
    score TEXT,
    memo TEXT,
    advice_id TEXT,
    privacy_level TEXT DEFAULT 'local_only',
    status TEXT DEFAULT 'started',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_CREATE_SESSION_ASSETS = """
CREATE TABLE IF NOT EXISTS session_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    asset_id TEXT,
    relative_path TEXT,
    created_at TEXT NOT NULL,
    note TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
)
"""

_CREATE_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_sessions_game_id ON sessions(game_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_result ON sessions(result)",
    "CREATE INDEX IF NOT EXISTS idx_session_assets_session_id "
    "ON session_assets(session_id)",
)

# update_session_finish で更新を許可するカラム（任意指定）。
_FINISH_UPDATABLE = (
    "ended_at",
    "duration_sec",
    "status",
    "updated_at",
    "mode",
    "build_or_deck_id",
    "result",
    "score",
    "memo",
    "advice_id",
    "privacy_level",
)

_SESSION_COLUMNS = (
    "session_id",
    "game_id",
    "game_name",
    "started_at",
    "ended_at",
    "duration_sec",
    "mode",
    "build_or_deck_id",
    "result",
    "score",
    "memo",
    "advice_id",
    "privacy_level",
    "status",
    "created_at",
    "updated_at",
)


class SessionStore:
    """``play_logs.db`` への薄いラッパー。1インスタンス = 1 DB ファイル。"""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

    # ------------------------------------------------------------------
    # 接続・初期化
    # ------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        # SQLite ファイル作成先が無い場合は自動作成する（指示書 15.2）。
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_SEC)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self) -> bool:
        """DB とテーブル・インデックスを作成する。既存 DB があっても壊さない。"""
        try:
            with contextlib.closing(self._connect()) as conn, conn:
                conn.execute(_CREATE_SESSIONS)
                conn.execute(_CREATE_SESSION_ASSETS)
                for statement in _CREATE_INDEXES:
                    conn.execute(statement)
            return True
        except sqlite3.Error as exc:
            logger.error("PlayCueDB failed to init db reason=%s", type(exc).__name__)
            return False

    # ------------------------------------------------------------------
    # 書き込み
    # ------------------------------------------------------------------
    def insert_session(self, session: GameSession) -> bool:
        """開始セッションを保存する。成功で True、失敗で False。"""
        row = session.to_row()
        columns = ", ".join(_SESSION_COLUMNS)
        placeholders = ", ".join(f":{name}" for name in _SESSION_COLUMNS)
        sql = f"INSERT INTO sessions ({columns}) VALUES ({placeholders})"
        ok = self._execute_write(sql, row, session.session_id)
        if ok:
            logger.info(
                "PlayCueDB saved session_id=%s game_id=%s",
                session.session_id,
                session.game_id,
            )
        return ok

    def update_session_finish(self, session_id: str, data: dict[str, object]) -> bool:
        """終了情報でセッションを更新する。``data`` のうち許可カラムのみ反映する。"""
        updates = {k: v for k, v in data.items() if k in _FINISH_UPDATABLE}
        if not updates:
            return True
        assignments = ", ".join(f"{name} = :{name}" for name in updates)
        params = dict(updates)
        params["session_id"] = session_id
        sql = f"UPDATE sessions SET {assignments} WHERE session_id = :session_id"
        ok = self._execute_write(sql, params, session_id)
        if ok:
            logger.info(
                "PlayCueDB updated session_id=%s status=%s",
                session_id,
                updates.get("status", "?"),
            )
        return ok

    def _execute_write(self, sql: str, params: dict[str, object], session_id: str) -> bool:
        """ロック時リトライ付きで書き込みを実行する。例外は握りログ化して False。"""
        for attempt in range(1, _RETRY_COUNT + 1):
            try:
                with contextlib.closing(self._connect()) as conn, conn:
                    conn.execute(sql, params)
                return True
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc).lower() and attempt < _RETRY_COUNT:
                    logger.warning(
                        "PlayCueDB retry due to sqlite_locked session_id=%s attempt=%d",
                        session_id,
                        attempt,
                    )
                    time.sleep(_RETRY_SLEEP_SEC)
                    continue
                logger.error(
                    "PlayCueDB failed to save session session_id=%s reason=%s",
                    session_id,
                    type(exc).__name__,
                )
                return False
            except sqlite3.Error as exc:
                logger.error(
                    "PlayCueDB failed to save session session_id=%s reason=%s",
                    session_id,
                    type(exc).__name__,
                )
                return False
        return False

    # ------------------------------------------------------------------
    # 読み出し（テスト・確認用）
    # ------------------------------------------------------------------
    def get_session(self, session_id: str) -> dict[str, object] | None:
        try:
            with contextlib.closing(self._connect()) as conn:
                cur = conn.execute(
                    "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
                )
                row = cur.fetchone()
                return dict(row) if row is not None else None
        except sqlite3.Error as exc:
            logger.error(
                "PlayCueDB failed to read session session_id=%s reason=%s",
                session_id,
                type(exc).__name__,
            )
            return None

    def list_recent_sessions(self, limit: int = 50) -> list[dict[str, object]]:
        try:
            with contextlib.closing(self._connect()) as conn:
                cur = conn.execute(
                    "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?",
                    (int(limit),),
                )
                return [dict(row) for row in cur.fetchall()]
        except sqlite3.Error as exc:
            logger.error(
                "PlayCueDB failed to list sessions reason=%s", type(exc).__name__
            )
            return []

    def existing_session_ids(self, prefix_date: str) -> list[str]:
        """``prefix_date`` で始まる session_id 一覧（衝突回避用）。失敗時は空。"""
        try:
            with contextlib.closing(self._connect()) as conn:
                cur = conn.execute(
                    "SELECT session_id FROM sessions WHERE session_id LIKE ?",
                    (f"{prefix_date}%",),
                )
                return [row["session_id"] for row in cur.fetchall()]
        except sqlite3.Error:
            return []
