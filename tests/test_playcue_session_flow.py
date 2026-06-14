"""セッション一連フローの結合テスト（指示書 12.2）。

GUI (Tk) には依存せず、app.py の _begin_session_log / _finish_session_log が
行う処理（start_session → insert → finish_session → update_session_finish）と
同等のフローを SessionStore レベルで検証する。
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from playcue.models import GameConfig
from playcue.session.db import SessionStore
from playcue.session.dialog import default_memo
from playcue.session.session import finish_session, start_session


class SessionFlowTest(unittest.TestCase):
    def _config(self) -> GameConfig:
        return GameConfig(
            game_name="Shadowverse Worlds Beyond",
            config_file=Path("."),
            game_id="shadowverse-wb",
            session_prefix="SVWB",
        )

    def test_launch_to_finish_persists_to_db(self):
        """疑似ゲーム起動→終了→メモ保存まで DB に残る。"""
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "data" / "global" / "play_logs.db")
            store.init_db()

            # 起動イベント相当
            session = start_session(self._config(), started_at=datetime(2026, 6, 15, 21, 30, 0))
            store.insert_session(session)

            # 終了 + メモ入力相当（保存ボタン）
            finish_session(session, datetime(2026, 6, 15, 22, 10, 0))
            memo = {**default_memo(), "result": "win", "mode": "ranked", "cancelled": False}
            store.update_session_finish(
                session.session_id,
                {
                    "ended_at": session.ended_at,
                    "duration_sec": session.duration_sec,
                    "status": session.status,
                    "updated_at": session.updated_at,
                    "result": memo["result"],
                    "mode": memo["mode"],
                },
            )

            row = store.get_session(session.session_id)
            self.assertEqual(row["status"], "finished")
            self.assertEqual(row["duration_sec"], 2400)
            self.assertEqual(row["result"], "win")
            self.assertEqual(row["mode"], "ranked")

    def test_cancel_saves_result_unknown(self):
        """終了メモをキャンセルしても result=unknown でセッション終了が保存される。"""
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "play_logs.db")
            store.init_db()
            session = start_session(self._config(), started_at=datetime(2026, 6, 15, 21, 30, 0))
            store.insert_session(session)

            memo = default_memo()  # キャンセル時の戻り値
            self.assertTrue(memo["cancelled"])
            self.assertEqual(memo["result"], "unknown")

            finish_session(session, datetime(2026, 6, 15, 21, 40, 0))
            store.update_session_finish(
                session.session_id,
                {
                    "ended_at": session.ended_at,
                    "duration_sec": session.duration_sec,
                    "status": session.status,
                    "updated_at": session.updated_at,
                    "result": memo["result"],
                },
            )
            row = store.get_session(session.session_id)
            self.assertEqual(row["result"], "unknown")
            self.assertEqual(row["status"], "finished")

    def test_db_failure_does_not_raise(self):
        """DB 保存に失敗してもアプリ層が落ちないよう、例外でなく False を返す。"""
        with tempfile.TemporaryDirectory() as tmp:
            # db_path 位置にディレクトリを作り、SQLite 接続を失敗させる。
            broken = Path(tmp) / "play_logs.db"
            broken.mkdir()
            store = SessionStore(broken)
            self.assertFalse(store.init_db())
            session = start_session(self._config(), started_at=datetime(2026, 6, 15, 21, 30, 0))
            self.assertFalse(store.insert_session(session))
            self.assertIsNone(store.get_session(session.session_id))


if __name__ == "__main__":
    unittest.main()
