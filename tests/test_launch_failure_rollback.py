"""v0.8 bugfix: ゲーム起動失敗時に UI が待機状態へ戻り、0 秒ログが残らないことを検証する。

修正前は launch_game() が失敗しても内部状態が「プレイ中」のままになり、
0 秒ログが保存される問題があった。
"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from playcue.models import GameConfig


def _make_config(game_exe: str = "C:/game/game.exe", process_name: str = "") -> GameConfig:
    return GameConfig(
        game_name="TestGame",
        config_file=Path("."),
        game_exe=game_exe,
        process_name=process_name,
    )


class GameLauncherBoolReturnTest(unittest.TestCase):
    """launch_game() の bool 戻り値を検証する。"""

    def _make_launcher(self):
        from playcue.launcher.game_launcher import GameLauncher
        return GameLauncher()

    def test_returns_true_when_exe_is_empty(self):
        """game_exe が空の場合は True（外部ランチャー待機設計）。"""
        launcher = self._make_launcher()
        config = _make_config(game_exe="")
        self.assertTrue(launcher.launch_game(config))

    def test_returns_false_when_exe_not_found(self):
        """存在しない exe の場合は False。"""
        launcher = self._make_launcher()
        config = _make_config(game_exe="C:/nonexistent/game.exe")
        with mock.patch("playcue.launcher.game_launcher.messagebox"):
            result = launcher.launch_game(config)
        self.assertFalse(result)

    def test_returns_true_on_success(self):
        """Popen 成功時は True。"""
        launcher = self._make_launcher()
        config = _make_config(game_exe="C:/game/game.exe")
        with (
            mock.patch("playcue.launcher.game_launcher.Path.exists", return_value=True),
            mock.patch("playcue.launcher.game_launcher.subprocess.Popen"),
        ):
            result = launcher.launch_game(config)
        self.assertTrue(result)

    def test_returns_false_on_oserror(self):
        """Popen が OSError の場合は False。"""
        launcher = self._make_launcher()
        config = _make_config(game_exe="C:/game/game.exe")
        with (
            mock.patch("playcue.launcher.game_launcher.Path.exists", return_value=True),
            mock.patch("playcue.launcher.game_launcher.subprocess.Popen", side_effect=OSError("denied")),
            mock.patch("playcue.launcher.game_launcher.messagebox"),
        ):
            result = launcher.launch_game(config)
        self.assertFalse(result)

    def test_error_message_does_not_contain_full_path(self):
        """エラーダイアログに絶対パスが含まれない。"""
        launcher = self._make_launcher()
        config = _make_config(game_exe="C:/Users/secret/game.exe")
        shown: list[str] = []
        with mock.patch(
            "playcue.launcher.game_launcher.messagebox.showerror",
            side_effect=lambda _title, msg: shown.append(msg),
        ):
            launcher.launch_game(config)

        for msg in shown:
            self.assertNotIn("C:/Users/secret", msg, "エラーメッセージに絶対パスが含まれてはいけない")


class UIRollbackOnLaunchFailureTest(unittest.TestCase):
    """start_game が launch_game 失敗時に UI を待機状態へ戻すことを検証する。"""

    def _make_app_with_mock_launcher(self, launch_result: bool):
        """ResidentPlayCueApp の最小スタブ。launch_result で launch_game の結果を制御する。"""
        from playcue.ui.app import ResidentPlayCueApp

        config = _make_config(game_exe="C:/game/game.exe")
        app = ResidentPlayCueApp.__new__(ResidentPlayCueApp)
        app.config = None
        app.configs = [config]
        app.closed = False
        app.session_start = __import__("datetime").datetime.now()
        app.elapsed_before_run = 0.0
        app.run_started_at = 0.0
        app.paused = True
        app.play_started = False
        app.log_saved = True
        app.watcher = None
        app.obs_prepare_running = False
        app.topmost = True

        import tkinter as tk
        app.current_game_var = mock.MagicMock()
        app.pause_var = mock.MagicMock()
        app.time_var = mock.MagicMock()
        app.obs_status_var = mock.MagicMock()
        app.login_bonus_status_var = mock.MagicMock()
        app.opacity_var = mock.MagicMock()
        app.game_button_vars = {}
        app.reset_button = None
        app.game_list_frame = None
        app.link_frame = None
        app.link_canvas = None
        app.link_body = None
        app.login_bonus_frame = None
        app.obs_status_label = None
        app.obs_controls = None
        app.recording_start_button = None
        app.recording_stop_button = None

        root_mock = mock.MagicMock()
        app.root = root_mock

        mock_launcher = mock.MagicMock()
        mock_launcher.launch_game.return_value = launch_result
        app.launcher = mock_launcher

        mock_obs = mock.MagicMock()
        app.obs_controller = mock_obs

        mock_logger = mock.MagicMock()
        app.logger = mock_logger

        app.login_bonus_logger = mock.MagicMock()
        app.login_bonus_checker = mock.MagicMock()

        # ヘルパーメソッドをモック化
        app._update_obs_status = mock.MagicMock()
        app._fit_window_to_screen = mock.MagicMock()
        app._set_waiting_ui = mock.MagicMock()
        app._refresh_links = mock.MagicMock()
        app._refresh_login_bonus_status = mock.MagicMock()
        app._start_watcher = mock.MagicMock()
        app.start_login_bonus_check = mock.MagicMock()
        app._reset_to_waiting_state = ResidentPlayCueApp._reset_to_waiting_state.__get__(app)

        return app, config

    def test_config_is_none_after_launch_failure(self):
        """起動失敗後に self.config が None に戻る。"""
        app, config = self._make_app_with_mock_launcher(launch_result=False)
        app.start_game(config)
        self.assertIsNone(app.config)

    def test_play_started_is_false_after_launch_failure(self):
        """起動失敗後に play_started が False に戻る。"""
        app, config = self._make_app_with_mock_launcher(launch_result=False)
        app.start_game(config)
        self.assertFalse(app.play_started)

    def test_log_saved_is_true_after_launch_failure(self):
        """起動失敗後に log_saved が True のまま（0秒ログが保存されない）。"""
        app, config = self._make_app_with_mock_launcher(launch_result=False)
        app.start_game(config)
        self.assertTrue(app.log_saved)

    def test_logger_not_called_after_launch_failure(self):
        """起動失敗時に PlayTimeLogger.save が呼ばれない。"""
        app, config = self._make_app_with_mock_launcher(launch_result=False)
        app.start_game(config)
        app.logger.save.assert_not_called()

    def test_watcher_not_started_after_launch_failure(self):
        """起動失敗時にウォッチャーが起動しない。"""
        app, config = self._make_app_with_mock_launcher(launch_result=False)
        app.start_game(config)
        app._start_watcher.assert_not_called()

    def test_successful_launch_sets_config(self):
        """起動成功時は self.config が設定される（既存動作を維持）。"""
        app, config = self._make_app_with_mock_launcher(launch_result=True)
        app.start_game(config)
        self.assertIs(app.config, config)


if __name__ == "__main__":
    unittest.main()
