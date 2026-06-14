"""playcue.session.session の単体テスト（指示書 12.1）。"""

from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path

from playcue.models import GameConfig
from playcue.session.session import (
    _derive_prefix,
    finish_session,
    generate_session_id,
    start_session,
)


class GenerateSessionIdTest(unittest.TestCase):
    def test_format_matches_spec(self):
        """<PREFIX>-YYYYMMDD-HHMMSS 形式で生成される。"""
        started = datetime(2026, 6, 15, 21, 30, 0)
        sid = generate_session_id("shadowverse-wb", started, prefix="SVWB")
        self.assertEqual(sid, "SVWB-20260615-213000")

    def test_prefix_derived_when_not_given(self):
        """prefix 未指定時は game_id から決定的に導出される。"""
        started = datetime(2026, 6, 15, 22, 15, 30)
        # rip は5文字以内なので母音を落とさずそのまま -> "RIP"
        sid = generate_session_id("rip", started)
        self.assertTrue(sid.startswith("RIP-"))
        self.assertEqual(sid, generate_session_id("rip", started))

    def test_derive_prefix_short_id_kept_as_is(self):
        """5文字以内の game_id は母音を落とさずそのまま使う。"""
        self.assertEqual(_derive_prefix("rip"), "RIP")
        self.assertEqual(_derive_prefix("aoi"), "AOI")
        self.assertEqual(_derive_prefix("ff14"), "FF14")
        # 区切りを除いた英数字が5文字以内かで判定する。
        self.assertEqual(_derive_prefix("a-b-c"), "ABC")

    def test_derive_prefix_word_rule(self):
        """6文字以上: 各単語の先頭3文字→(先頭以外の)母音除去→連結→先頭5文字。"""
        self.assertEqual(_derive_prefix("shadowverse-wb"), "SHWB")
        self.assertEqual(_derive_prefix("ff7-rebirth"), "FF7RB")
        # 5文字上限で切り詰められる: br + df + fly -> "brdffly" -> "BRDFF"
        self.assertEqual(_derive_prefix("bravely-default-flying"), "BRDFF")

    def test_derive_prefix_keeps_leading_vowel(self):
        """各単語の先頭1文字が母音なら落とさず残す。"""
        # elden: e(先頭)l d / ring: r i(除去) n -> "eld"+"rn" -> "ELDRN"
        self.assertEqual(_derive_prefix("elden-ring"), "ELDRN")
        # octopath: o(先頭)c t -> "OCT"
        self.assertEqual(_derive_prefix("octopath-traveler"), "OCTTR")

    def test_derive_prefix_empty_falls_back(self):
        self.assertEqual(_derive_prefix(""), "GAME")

    def test_fallback_prefix_when_game_id_empty(self):
        """game_id が空なら GAME 接頭辞にフォールバックする。"""
        started = datetime(2026, 6, 15, 23, 2, 0)
        sid = generate_session_id("", started)
        self.assertEqual(sid, "GAME-20260615-230200")

    def test_collision_appends_suffix(self):
        """同秒起動の衝突時は -01, -02 が付与される。"""
        started = datetime(2026, 6, 15, 21, 30, 0)
        base = "SVWB-20260615-213000"
        sid = generate_session_id(
            "shadowverse-wb", started, prefix="SVWB", existing_ids=[base]
        )
        self.assertEqual(sid, "SVWB-20260615-213000-01")
        sid2 = generate_session_id(
            "shadowverse-wb",
            started,
            prefix="SVWB",
            existing_ids=[base, sid],
        )
        self.assertEqual(sid2, "SVWB-20260615-213000-02")


class StartSessionTest(unittest.TestCase):
    def _config(self, **kwargs) -> GameConfig:
        return GameConfig(game_name="Game", config_file=Path("."), **kwargs)

    def test_start_session_sets_started_and_status(self):
        config = self._config(game_id="shadowverse-wb", session_prefix="SVWB")
        started = datetime(2026, 6, 15, 21, 30, 0)
        session = start_session(config, started_at=started)
        self.assertEqual(session.session_id, "SVWB-20260615-213000")
        self.assertEqual(session.game_id, "shadowverse-wb")
        self.assertEqual(session.status, "started")
        self.assertTrue(session.started_at.startswith("2026-06-15T21:30:00"))
        self.assertIsNone(session.ended_at)
        self.assertEqual(session.result, "unknown")
        self.assertEqual(session.privacy_level, "local_only")

    def test_game_id_falls_back_to_game_key(self):
        config = self._config(process_name="game.exe")
        session = start_session(config, started_at=datetime(2026, 6, 15, 21, 30, 0))
        self.assertEqual(session.game_id, "game.exe")


class FinishSessionTest(unittest.TestCase):
    def test_finish_sets_ended_and_duration(self):
        config = GameConfig(game_name="Game", config_file=Path("."), session_prefix="G")
        start = datetime(2026, 6, 15, 21, 30, 0)
        session = start_session(config, started_at=start)
        end = datetime(2026, 6, 15, 22, 10, 0)  # +2400 秒
        finish_session(session, end)
        self.assertTrue(session.ended_at.startswith("2026-06-15T22:10:00"))
        self.assertEqual(session.duration_sec, 2400)
        self.assertEqual(session.status, "finished")

    def test_finish_with_custom_status(self):
        config = GameConfig(game_name="Game", config_file=Path("."))
        session = start_session(config, started_at=datetime(2026, 6, 15, 21, 30, 0))
        finish_session(session, datetime(2026, 6, 15, 21, 30, 10), status="unknown_end")
        self.assertEqual(session.status, "unknown_end")
        self.assertEqual(session.duration_sec, 10)


if __name__ == "__main__":
    unittest.main()
