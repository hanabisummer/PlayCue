"""v0.8 bugfix: _start_watcher が active_process_name を正しく GameProcessWatcher へ渡すことを検証する。

修正前は active_process_name=config.process_name になっており、
config.active_process_name が設定されていても無視されていた。
"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from playcue.models import GameConfig


class StartWatcherWiringTest(unittest.TestCase):
    """ResidentPlayCueApp._start_watcher が GameProcessWatcher へ渡す引数を検証する。"""

    def _make_config(self, process_name: str = "", active_process_name: str = "") -> GameConfig:
        return GameConfig(
            game_name="TestGame",
            config_file=Path("."),
            game_exe="C:/game/launcher.exe",
            process_name=process_name,
            active_process_name=active_process_name,
        )

    def _make_app_stub(self):
        """ResidentPlayCueApp の _start_watcher を呼ぶのに必要な最小スタブを返す。"""
        from playcue.ui.app import ResidentPlayCueApp

        with (
            mock.patch("playcue.ui.app.OBSController"),
            mock.patch("playcue.ui.app.GameLauncher"),
            mock.patch("playcue.ui.app.PlayTimeLogger"),
            mock.patch("playcue.ui.app.LoginBonusLogger"),
            mock.patch("playcue.ui.app.LoginBonusChecker"),
            mock.patch("playcue.ui.app.StartupTaskController"),
            mock.patch("playcue.ui.app.ResidentPlayCueApp._configure_theme"),
            mock.patch("playcue.ui.app.ResidentPlayCueApp._build_ui"),
            mock.patch("playcue.ui.app.ResidentPlayCueApp._update_timer"),
            mock.patch("playcue.ui.app.ResidentPlayCueApp._monitor_obs_status"),
            mock.patch("playcue.ui.app.ResidentPlayCueApp._fit_window_to_screen"),
            mock.patch("playcue.ui.app.ResidentPlayCueApp._update_topmost_label"),
            mock.patch("playcue.ui.app.ResidentPlayCueApp.prepare_obs_on_startup"),
        ):
            root_mock = mock.MagicMock()
            config = self._make_config(process_name="launcher.exe", active_process_name="game.exe")
            app = ResidentPlayCueApp.__new__(ResidentPlayCueApp)
            app.root = root_mock
            app.configs = [config]
            app.watcher = None
            app.closed = False
            app.on_game_exit = mock.MagicMock()
            app.on_game_active = mock.MagicMock()
            app._update_config_process_name = mock.MagicMock()
            app._watch_process = mock.MagicMock()
            return app

    def test_active_process_name_is_passed_correctly(self):
        """active_process_name が設定された config では、その値がウォッチャーへ渡る。"""
        import playcue.ui.app as app_module

        config = self._make_config(
            process_name="launcher.exe",
            active_process_name="game.exe",
        )

        captured: dict = {}

        original_watcher = app_module.GameProcessWatcher

        def mock_watcher(process_name, on_exit, **kwargs):
            captured["process_name"] = process_name
            captured["active_process_name"] = kwargs.get("active_process_name", "")
            watcher = mock.MagicMock()
            watcher.stopped = False
            return watcher

        with mock.patch.object(app_module, "GameProcessWatcher", side_effect=mock_watcher):
            with mock.patch.object(app_module, "psutil", mock.MagicMock()):
                app = self._make_app_stub()
                app._start_watcher(config)

        self.assertEqual(captured["process_name"], "launcher.exe")
        self.assertEqual(captured["active_process_name"], "game.exe")

    def test_active_process_name_empty_passes_empty(self):
        """active_process_name が空の場合、空文字列がウォッチャーへ渡る（従来動作維持）。"""
        import playcue.ui.app as app_module

        config = self._make_config(
            process_name="game.exe",
            active_process_name="",
        )

        captured: dict = {}

        def mock_watcher(process_name, on_exit, **kwargs):
            captured["active_process_name"] = kwargs.get("active_process_name", "SENTINEL")
            watcher = mock.MagicMock()
            watcher.stopped = False
            return watcher

        with mock.patch.object(app_module, "GameProcessWatcher", side_effect=mock_watcher):
            with mock.patch.object(app_module, "psutil", mock.MagicMock()):
                app = self._make_app_stub()
                app._start_watcher(config)

        self.assertEqual(captured["active_process_name"], "")

    def test_process_name_and_active_process_name_differ_in_watcher(self):
        """process_name と active_process_name が異なることをウォッチャーで確認する。

        修正前は両者が同じ値（config.process_name）になっていたため、このテストが失敗した。
        """
        import playcue.ui.app as app_module

        config = self._make_config(
            process_name="launcher.exe",
            active_process_name="game.exe",
        )

        captured: dict = {}

        def mock_watcher(process_name, on_exit, **kwargs):
            captured["process_name"] = process_name
            captured["active_process_name"] = kwargs.get("active_process_name", "")
            watcher = mock.MagicMock()
            watcher.stopped = False
            return watcher

        with mock.patch.object(app_module, "GameProcessWatcher", side_effect=mock_watcher):
            with mock.patch.object(app_module, "psutil", mock.MagicMock()):
                app = self._make_app_stub()
                app._start_watcher(config)

        self.assertNotEqual(
            captured["process_name"],
            captured["active_process_name"],
            "process_name と active_process_name がウォッチャー内で同じになってはいけない",
        )


if __name__ == "__main__":
    unittest.main()
