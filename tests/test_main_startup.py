"""第2層バグ修正: 設定ゼロ（初回起動）でも main() がアプリを起動することを検証する。

修正前は、configs が空のとき main() が「設定エラー」を表示して return 1 していたため、
ResidentPlayCueApp が用意している初回セットアップウィザード（_open_initial_wizard）に
到達できず、新規ユーザーは UI からゲームを追加できなかった。

修正後は:
- 設定ゼロ & 致命的エラーなし → アプリを起動（ウィザードは本体側が開く）
- 壊れた JSON のみ           → 警告を出しつつ起動を継続
- 明示指定したファイルが壊れている → 従来どおり致命的エラーで終了
"""
from __future__ import annotations

import unittest
from unittest import mock


class MainStartupTest(unittest.TestCase):
    def _run_main(self, resolve_result=None, resolve_exc=None, argv=None):
        """副作用（管理者昇格・コンソール・Tk・本体・ダイアログ）をモックして main() を実行する。

        戻り値: (exit_code, mocks) — mocks に各モックを格納し呼び出しを検証する。
        """
        import PlayCue

        argv = argv or ["PlayCue.py"]
        app_cls = mock.MagicMock(name="ResidentPlayCueApp")
        tk_cls = mock.MagicMock(name="Tk")
        msgbox = mock.MagicMock(name="messagebox")

        def fake_resolve(_argv):
            if resolve_exc is not None:
                raise resolve_exc
            return resolve_result

        with mock.patch.object(PlayCue, "relaunch_as_admin", return_value=False), \
                mock.patch.object(PlayCue.ConsoleController, "set_visible"), \
                mock.patch.object(PlayCue, "resolve_configs", side_effect=fake_resolve), \
                mock.patch.object(PlayCue, "Tk", tk_cls), \
                mock.patch.object(PlayCue, "ResidentPlayCueApp", app_cls), \
                mock.patch.object(PlayCue, "messagebox", msgbox):
            code = PlayCue.main()

        return code, {"app": app_cls, "tk": tk_cls, "msgbox": msgbox}

    def test_empty_configs_launches_app_not_error(self):
        """設定ゼロ・警告なし → アプリ起動・エラー非表示・戻り値0。"""
        code, m = self._run_main(resolve_result=([], []))

        self.assertEqual(code, 0)
        m["app"].assert_called_once()
        m["msgbox"].showerror.assert_not_called()

    def test_empty_configs_passes_empty_list_to_app(self):
        """ResidentPlayCueApp に空の configs が渡され、本体がウィザード起動を担う。"""
        code, m = self._run_main(resolve_result=([], []))

        self.assertEqual(code, 0)
        _root, passed_configs = m["app"].call_args.args
        self.assertEqual(passed_configs, [])

    def test_empty_configs_with_warnings_launches_and_warns(self):
        """壊れた JSON のみ → 起動継続・警告スケジュール・エラー非表示。"""
        code, m = self._run_main(resolve_result=([], ["- broken.json: JSON 形式が不正です"]))

        self.assertEqual(code, 0)
        m["app"].assert_called_once()
        m["msgbox"].showerror.assert_not_called()
        # 警告は root.after(300, ...) でスケジュールされる
        root = m["tk"].return_value
        self.assertTrue(root.after.called)

    def test_valid_configs_launch_without_warning(self):
        """正常設定あり → アプリ起動・警告もエラーも非表示。"""
        sentinel = object()
        code, m = self._run_main(resolve_result=([sentinel], []))

        self.assertEqual(code, 0)
        m["app"].assert_called_once()
        m["msgbox"].showerror.assert_not_called()
        m["msgbox"].showwarning.assert_not_called()

    def test_explicit_broken_config_arg_is_fatal(self):
        """明示指定したファイルが壊れている → 致命的エラーで終了（アプリ未起動）。"""
        code, m = self._run_main(resolve_exc=ValueError("game_name は必須です"))

        self.assertEqual(code, 1)
        m["app"].assert_not_called()
        m["msgbox"].showerror.assert_called_once()


if __name__ == "__main__":
    unittest.main()
