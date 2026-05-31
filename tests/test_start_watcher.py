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


class ProcessWatcherOnActiveTest(unittest.TestCase):
    """GameProcessWatcher.tick() が on_active を正しいタイミングで呼ぶことを検証する。

    回帰: v0.8 の active_process_name 配線修正により、active_process_name が空のゲームでは
    on_active が永久に呼ばれなくなっていた。これによりタイマー開始と OBS 録画開始が機能しなかった。
    """

    def _make_watcher(self, process_name, active_process_name="", on_active=None, on_exit=None):
        from playcue.tracking.process_tracker import GameProcessWatcher
        return GameProcessWatcher(
            process_name=process_name,
            on_exit=on_exit or mock.MagicMock(),
            active_process_name=active_process_name,
            on_active=on_active or mock.MagicMock(),
        )

    def _make_proc(self, name: str) -> mock.MagicMock:
        p = mock.MagicMock()
        p.info = {"name": name, "exe": ""}
        return p

    def test_on_active_called_when_no_active_process_name(self):
        """active_process_name 未設定: process_name が初回検知されたとき on_active が呼ばれる。"""
        import playcue.tracking.process_tracker as mod

        on_active = mock.MagicMock()
        watcher = self._make_watcher("game.exe", active_process_name="", on_active=on_active)
        proc = self._make_proc("game.exe")

        with mock.patch.object(mod, "psutil") as mock_psutil:
            mock_psutil.process_iter.return_value = [proc]
            mock_psutil.NoSuchProcess = Exception
            mock_psutil.AccessDenied = Exception
            watcher.tick()

        on_active.assert_called_once()

    def test_on_active_called_only_once_on_repeated_ticks(self):
        """process_name が連続検知されても on_active は1回だけ呼ばれる。"""
        import playcue.tracking.process_tracker as mod

        on_active = mock.MagicMock()
        watcher = self._make_watcher("game.exe", active_process_name="", on_active=on_active)
        proc = self._make_proc("game.exe")

        with mock.patch.object(mod, "psutil") as mock_psutil:
            mock_psutil.process_iter.return_value = [proc]
            mock_psutil.NoSuchProcess = Exception
            mock_psutil.AccessDenied = Exception
            watcher.tick()
            watcher.tick()
            watcher.tick()

        on_active.assert_called_once()

    def test_on_active_not_called_before_process_detected(self):
        """プロセスが未検知のうちは on_active は呼ばれない（猶予期間中）。"""
        import playcue.tracking.process_tracker as mod

        on_active = mock.MagicMock()
        watcher = self._make_watcher("game.exe", active_process_name="", on_active=on_active)

        with mock.patch.object(mod, "psutil") as mock_psutil:
            mock_psutil.process_iter.return_value = []
            mock_psutil.NoSuchProcess = Exception
            mock_psutil.AccessDenied = Exception
            watcher.tick()

        on_active.assert_not_called()

    def test_on_active_via_active_process_name_still_works(self):
        """active_process_name 設定時: active_process_name 検知で on_active が呼ばれる（既存動作維持）。"""
        import playcue.tracking.process_tracker as mod

        on_active = mock.MagicMock()
        watcher = self._make_watcher(
            "launcher.exe", active_process_name="game.exe", on_active=on_active
        )

        with mock.patch.object(mod, "psutil") as mock_psutil:
            mock_psutil.process_iter.return_value = [self._make_proc("game.exe")]
            mock_psutil.NoSuchProcess = Exception
            mock_psutil.AccessDenied = Exception
            watcher.tick()

        on_active.assert_called_once()

    def test_on_active_not_double_fired_when_process_name_equals_active(self):
        """process_name == active_process_name のとき on_active は1回だけ（is_active ブロックで発火）。"""
        import playcue.tracking.process_tracker as mod

        on_active = mock.MagicMock()
        watcher = self._make_watcher(
            "game.exe", active_process_name="game.exe", on_active=on_active
        )

        with mock.patch.object(mod, "psutil") as mock_psutil:
            mock_psutil.process_iter.return_value = [self._make_proc("game.exe")]
            mock_psutil.NoSuchProcess = Exception
            mock_psutil.AccessDenied = Exception
            watcher.tick()
            watcher.tick()

        on_active.assert_called_once()


if __name__ == "__main__":
    unittest.main()
