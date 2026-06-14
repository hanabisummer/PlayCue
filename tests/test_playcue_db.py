"""playcue.session.db.SessionStore の単体テスト（指示書 12.1）。"""

from __future__ import annotations

import contextlib
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from playcue.models import GameConfig
from playcue.session.db import SessionStore
from playcue.session.session import finish_session, start_session


def _session(prefix: str = "G", started=datetime(2026, 6, 15, 21, 30, 0)):
    config = GameConfig(
        game_name="Shadowverse Worlds Beyond",
        config_file=Path("."),
        game_id="shadowverse-wb",
        session_prefix=prefix,
    )
    return start_session(config, started_at=started)


class InitDbTest(unittest.TestCase):
    def test_creates_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "data" / "global" / "play_logs.db")
            self.assertTrue(store.init_db())
            with contextlib.closing(sqlite3.connect(store.db_path)) as conn:
                names = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
            self.assertIn("sessions", names)
            self.assertIn("session_assets", names)

    def test_db_file_created_in_data_global(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "data" / "global" / "play_logs.db"
            self.assertFalse(db_path.exists())
            SessionStore(db_path).init_db()
            self.assertTrue(db_path.exists())

    def test_reinit_does_not_break_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "play_logs.db")
            store.init_db()
            store.insert_session(_session())
            # 既存 DB に対する再初期化でデータが消えない。
            self.assertTrue(store.init_db())
            self.assertEqual(len(store.list_recent_sessions()), 1)


class InsertAndReadTest(unittest.TestCase):
    def test_insert_and_get(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "play_logs.db")
            store.init_db()
            session = _session()
            self.assertTrue(store.insert_session(session))
            row = store.get_session(session.session_id)
            self.assertIsNotNone(row)
            self.assertEqual(row["game_id"], "shadowverse-wb")
            self.assertEqual(row["status"], "started")
            self.assertIsNone(row["ended_at"])

    def test_update_session_finish_persists_memo(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "play_logs.db")
            store.init_db()
            session = _session()
            store.insert_session(session)
            finish_session(session, datetime(2026, 6, 15, 22, 10, 0))
            store.update_session_finish(
                session.session_id,
                {
                    "ended_at": session.ended_at,
                    "duration_sec": session.duration_sec,
                    "status": session.status,
                    "updated_at": session.updated_at,
                    "mode": "ranked",
                    "build_or_deck_id": "forest_rotation_001",
                    "result": "win",
                    "memo": "序盤事故、除去不足",
                    "advice_id": "ADV-SVWB-001",
                    "privacy_level": "local_only",
                },
            )
            row = store.get_session(session.session_id)
            self.assertEqual(row["status"], "finished")
            self.assertEqual(row["duration_sec"], 2400)
            self.assertEqual(row["mode"], "ranked")
            self.assertEqual(row["result"], "win")
            self.assertEqual(row["memo"], "序盤事故、除去不足")
            self.assertEqual(row["advice_id"], "ADV-SVWB-001")
            self.assertEqual(row["privacy_level"], "local_only")

    def test_list_recent_orders_by_started_at_desc(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "play_logs.db")
            store.init_db()
            store.insert_session(_session(started=datetime(2026, 6, 15, 20, 0, 0)))
            store.insert_session(_session(started=datetime(2026, 6, 15, 22, 0, 0)))
            rows = store.list_recent_sessions()
            self.assertEqual(len(rows), 2)
            self.assertGreater(rows[0]["started_at"], rows[1]["started_at"])

    def test_existing_session_ids_by_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "play_logs.db")
            store.init_db()
            session = _session(prefix="SVWB")
            store.insert_session(session)
            ids = store.existing_session_ids("SVWB-20260615")
            self.assertIn(session.session_id, ids)


class FailureToleranceTest(unittest.TestCase):
    def test_operations_on_uninitialized_db_do_not_raise(self):
        """テーブル未作成でも例外を投げず False/None/[] を返す（本体を落とさない）。"""
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "play_logs.db")
            # init_db を呼ばずに操作する。
            self.assertFalse(store.insert_session(_session()))
            self.assertIsNone(store.get_session("missing"))
            self.assertEqual(store.list_recent_sessions(), [])
            self.assertEqual(store.existing_session_ids("X"), [])


if __name__ == "__main__":
    unittest.main()
