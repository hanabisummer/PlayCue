"""v0.8 bugfix: resolve_configs が壊れた JSON 混在時にも起動継続することを検証する。

修正前は ConfigLoader.list_configs() を使っていたため、壊れた JSON が 1 件あるだけで
アプリ全体が起動不能になっていた。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def _write(directory: Path, name: str, data: object) -> None:
    (directory / name).write_text(json.dumps(data), encoding="utf-8")


class ResolveConfigsTest(unittest.TestCase):
    def _call(self, tmp_dir: Path, argv: list[str] | None = None) -> tuple:
        """PlayCue.resolve_configs をテスト用ディレクトリで呼び出す。"""
        import PlayCue

        argv = argv or ["PlayCue.py"]
        with mock.patch.object(PlayCue, "CONFIG_DIR", tmp_dir):
            return PlayCue.resolve_configs(argv)

    def test_valid_configs_load_successfully(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write(d, "a.json", {"game_name": "Alpha"})
            _write(d, "b.json", {"game_name": "Beta"})

            configs, warnings = self._call(d)

            self.assertEqual(len(configs), 2)
            self.assertEqual(warnings, [])

    def test_broken_json_skipped_valid_configs_returned(self):
        """壊れた JSON が混在しても正常設定は返される。"""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "broken.json").write_text("{", encoding="utf-8")
            _write(d, "good.json", {"game_name": "Good"})

            configs, warnings = self._call(d)

            self.assertEqual(len(configs), 1)
            self.assertEqual(configs[0].game_name, "Good")

    def test_broken_json_produces_warning_lines(self):
        """壊れたファイルはファイル名とメッセージを含む warning_lines に記録される。"""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "broken.json").write_text("{", encoding="utf-8")
            _write(d, "good.json", {"game_name": "Good"})

            _configs, warnings = self._call(d)

            self.assertEqual(len(warnings), 1)
            self.assertIn("broken.json", warnings[0])

    def test_warning_lines_do_not_contain_absolute_path(self):
        """警告メッセージに絶対パスが含まれない。"""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "broken.json").write_text("{", encoding="utf-8")
            _write(d, "good.json", {"game_name": "Good"})

            _configs, warnings = self._call(d)

            for line in warnings:
                self.assertNotIn(str(d), line, "警告に絶対パスが含まれてはいけない")

    def test_example_json_excluded(self):
        """example.json は通常ゲーム一覧から除外される。"""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write(d, "example.json", {"game_name": "Example Game"})
            _write(d, "my_game.json", {"game_name": "My Game"})

            configs, _ = self._call(d)

            names = [c.game_name for c in configs]
            self.assertNotIn("Example Game", names)
            self.assertIn("My Game", names)

    def test_all_broken_returns_empty_configs(self):
        """全ファイルが壊れている場合は空のリストを返す（起動判断は呼び出し元）。"""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "broken.json").write_text("{", encoding="utf-8")

            configs, warnings = self._call(d)

            self.assertEqual(configs, [])
            self.assertEqual(len(warnings), 1)

    def test_multiple_broken_all_in_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "bad1.json").write_text("{", encoding="utf-8")
            _write(d, "bad2.json", {"game_name": ""})
            _write(d, "good.json", {"game_name": "Good"})

            configs, warnings = self._call(d)

            self.assertEqual(len(configs), 1)
            self.assertEqual(len(warnings), 2)


if __name__ == "__main__":
    unittest.main()
