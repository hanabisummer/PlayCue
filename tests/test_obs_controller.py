"""Tests for OBSController and OBSStatus.

All tests run without OBS Studio installed.  Real WebSocket connections and
process detection are replaced with mocks or config-level guards.

IMPORTANT: every test that could trigger _set_error() must either
  a) pass show_errors=False so the dialog is suppressed, or
  b) patch 'playcue.obs.obs_controller.messagebox' to prevent a modal
     dialog from blocking the test runner on the main thread.
"""
from __future__ import annotations

import unittest
from unittest import mock

from playcue.models import OBSConfig
from playcue.obs.obs_controller import OBSController, OBSStatus
from playcue.ui.i18n import obs_status_text


# ---------------------------------------------------------------------------
# Module-level patch: prevent any messagebox dialog from ever blocking tests.
# obsws_python is installed in this environment, so without this guard
# _set_error() would create a modal Tk dialog and hang python -m unittest.
# ---------------------------------------------------------------------------
_mock_messagebox = mock.patch("playcue.obs.obs_controller.messagebox")


def setUpModule():
    _mock_messagebox.start()


def tearDownModule():
    _mock_messagebox.stop()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def disabled_config() -> OBSConfig:
    return OBSConfig(enabled=False)


def enabled_config(**kwargs) -> OBSConfig:
    return OBSConfig(
        enabled=True,
        exe_path="C:/Path/To/OBS/obs64.exe",
        websocket_host="127.0.0.1",
        websocket_port=4455,
        websocket_password="CHANGE_ME",
        **kwargs,
    )


# ---------------------------------------------------------------------------
# #27: OBS status codes
# ---------------------------------------------------------------------------

class OBSStatusCodesTest(unittest.TestCase):
    def test_all_constants_are_strings(self):
        for attr in vars(OBSStatus):
            if attr.startswith("_"):
                continue
            self.assertIsInstance(getattr(OBSStatus, attr), str)

    def test_disabled_config_initialises_to_disabled(self):
        ctrl = OBSController(disabled_config())
        self.assertEqual(ctrl.status, OBSStatus.DISABLED)

    def test_enabled_config_initialises_to_not_running(self):
        ctrl = OBSController(enabled_config())
        self.assertEqual(ctrl.status, OBSStatus.NOT_RUNNING)


class OBSStatusTextTest(unittest.TestCase):
    """obs_status_text() converts status codes to UI strings."""

    def test_known_codes_produce_non_empty_text(self):
        codes = [
            OBSStatus.DISABLED,
            OBSStatus.NOT_CONFIGURED,
            OBSStatus.NOT_RUNNING,
            OBSStatus.STARTING,
            OBSStatus.CONNECTING,
            OBSStatus.CONNECTED,
            OBSStatus.RECORDING,
            OBSStatus.RECORDING_NOT_READY,
            OBSStatus.DISCONNECTED,
            OBSStatus.ERROR,
        ]
        for code in codes:
            with self.subTest(code=code):
                text = obs_status_text(code)
                self.assertTrue(text, f"obs_status_text({code!r}) returned empty string")
                self.assertNotEqual(text, code, "Display text should differ from the raw code")

    def test_unknown_code_falls_back_to_code_itself(self):
        self.assertEqual(obs_status_text("unknown_code"), "unknown_code")

    def test_disabled_ja_display(self):
        from playcue.ui import i18n
        i18n.set_language("ja")
        self.assertEqual(obs_status_text(OBSStatus.DISABLED), "OBS: 無効")

    def test_recording_en_display(self):
        from playcue.ui import i18n
        i18n.set_language("en")
        self.assertEqual(obs_status_text(OBSStatus.RECORDING), "OBS: Recording")
        i18n.set_language("ja")  # restore

    def test_not_configured_has_translation(self):
        from playcue.ui import i18n
        i18n.set_language("ja")
        self.assertIn("設定", obs_status_text(OBSStatus.NOT_CONFIGURED))


# ---------------------------------------------------------------------------
# #28: OBS disabled / not_configured safety
# ---------------------------------------------------------------------------

class OBSDisabledSafetyTest(unittest.TestCase):
    def test_disabled_prepare_is_noop(self):
        ctrl = OBSController(disabled_config())
        ctrl.prepare()  # must not raise
        self.assertEqual(ctrl.status, OBSStatus.DISABLED)

    def test_disabled_connect_returns_false(self):
        ctrl = OBSController(disabled_config())
        result = ctrl.connect()
        self.assertFalse(result)

    def test_disabled_start_recording_returns_false(self):
        ctrl = OBSController(disabled_config())
        result = ctrl.start_recording(show_errors=False)
        self.assertFalse(result)
        self.assertEqual(ctrl.status, OBSStatus.DISABLED)

    def test_disabled_stop_recording_returns_false(self):
        ctrl = OBSController(disabled_config())
        result = ctrl.stop_recording(show_errors=False)
        self.assertFalse(result)
        self.assertEqual(ctrl.status, OBSStatus.DISABLED)

    def test_disabled_poll_status_returns_false(self):
        ctrl = OBSController(disabled_config())
        result = ctrl.poll_status()
        self.assertFalse(result)
        self.assertEqual(ctrl.status, OBSStatus.DISABLED)


class OBSNotConfiguredTest(unittest.TestCase):
    def test_launch_without_exe_path_sets_error(self):
        cfg = OBSConfig(enabled=True, exe_path="")
        ctrl = OBSController(cfg)
        # Pretend OBS is not already running so the exe_path check is reached.
        with mock.patch.object(ctrl, "_is_obs_running", return_value=False):
            ctrl.launch_obs(show_errors=False)
        self.assertEqual(ctrl.status, OBSStatus.ERROR)

    def test_launch_with_missing_exe_sets_error_without_exposing_path(self):
        cfg = OBSConfig(enabled=True, exe_path="C:/Path/To/OBS/obs64.exe")
        ctrl = OBSController(cfg)
        # Pretend OBS is not running and the exe file does not exist.
        with (
            mock.patch.object(ctrl, "_is_obs_running", return_value=False),
            mock.patch("playcue.obs.obs_controller.Path.exists", return_value=False),
        ):
            ctrl.launch_obs(show_errors=False)
        self.assertEqual(ctrl.status, OBSStatus.ERROR)


# ---------------------------------------------------------------------------
# #29: OBS launch / connection failure safety
# ---------------------------------------------------------------------------

class OBSLaunchFailureTest(unittest.TestCase):
    def test_oserror_on_launch_sets_error_not_raises(self):
        cfg = enabled_config()
        ctrl = OBSController(cfg)
        with (
            mock.patch.object(ctrl, "_is_obs_running", return_value=False),
            mock.patch("playcue.obs.obs_controller.Path.exists", return_value=True),
            mock.patch("playcue.obs.obs_controller.subprocess.Popen",
                       side_effect=OSError("launch failed")),
        ):
            ctrl.launch_obs(show_errors=False)
        self.assertEqual(ctrl.status, OBSStatus.ERROR)

    def test_connection_failure_sets_disconnected_not_raises(self):
        cfg = enabled_config()
        ctrl = OBSController(cfg)
        # obsws-python not installed → ReqClient is None → returns False safely
        import playcue.obs.obs_controller as m
        with mock.patch.object(m, "ReqClient", None):
            result = ctrl.connect(show_errors=False)
        self.assertFalse(result)

    def test_obsws_exception_sets_error_not_raises(self):
        cfg = OBSConfig(
            enabled=True,
            exe_path="",
            websocket_host="127.0.0.1",
            websocket_port=4455,
            websocket_password="CHANGE_ME",
            connect_timeout_seconds=1,
            connect_retry_interval_seconds=0,
        )
        ctrl = OBSController(cfg)
        import playcue.obs.obs_controller as m
        mock_client_class = mock.MagicMock(side_effect=ConnectionRefusedError("refused"))
        with mock.patch.object(m, "ReqClient", mock_client_class):
            result = ctrl.connect(show_errors=False)
        self.assertFalse(result)
        self.assertEqual(ctrl.status, OBSStatus.ERROR)


# ---------------------------------------------------------------------------
# #30: Recording start failure safety
# ---------------------------------------------------------------------------

class OBSRecordingStartFailureTest(unittest.TestCase):
    def _ctrl_with_mock_client(self):
        ctrl = OBSController(enabled_config())
        ctrl.client = mock.MagicMock()
        ctrl.status = OBSStatus.CONNECTED
        return ctrl

    def test_start_recording_already_recording_is_success(self):
        ctrl = self._ctrl_with_mock_client()
        ctrl.status = OBSStatus.RECORDING
        ctrl.client.get_record_status.return_value = mock.MagicMock(
            output_active=True, outputActive=True
        )
        result = ctrl.start_recording(show_errors=False)
        self.assertTrue(result)
        self.assertFalse(ctrl.recording_started_by_app)

    def test_start_recording_exception_does_not_raise(self):
        cfg = OBSConfig(
            enabled=True,
            exe_path="",
            websocket_host="127.0.0.1",
            websocket_port=4455,
            websocket_password="CHANGE_ME",
            connect_timeout_seconds=1,
            connect_retry_interval_seconds=0,
        )
        ctrl = OBSController(cfg)
        ctrl.client = mock.MagicMock()
        ctrl.client.get_record_status.return_value = mock.MagicMock(
            output_active=False, outputActive=False
        )
        ctrl.client.start_record.side_effect = Exception("recording failed")
        result = ctrl.start_recording(show_errors=False)
        self.assertFalse(result)
        self.assertFalse(ctrl.recording_started_by_app, "recording_started_by_app must stay False on failure")
        self.assertEqual(ctrl.status, OBSStatus.ERROR)

    def test_start_recording_failure_does_not_set_recording_started_by_app(self):
        ctrl = OBSController(disabled_config())
        ctrl.start_recording(show_errors=False)
        self.assertFalse(ctrl.recording_started_by_app)


# ---------------------------------------------------------------------------
# #31: Recording stop failure safety
# ---------------------------------------------------------------------------

class OBSRecordingStopFailureTest(unittest.TestCase):
    def test_stop_recording_only_if_started_by_app_skips_when_not_started(self):
        ctrl = OBSController(enabled_config())
        ctrl.recording_started_by_app = False
        result = ctrl.stop_recording(only_if_started_by_app=True, show_errors=False)
        self.assertFalse(result)
        self.assertFalse(ctrl.recording_started_by_app)

    def test_stop_recording_exception_does_not_raise(self):
        ctrl = OBSController(enabled_config())
        ctrl.client = mock.MagicMock()
        ctrl.client.get_record_status.return_value = mock.MagicMock(
            output_active=True, outputActive=True
        )
        ctrl.client.stop_record.side_effect = Exception("stop failed")
        result = ctrl.stop_recording(show_errors=False)
        self.assertFalse(result)
        self.assertEqual(ctrl.status, OBSStatus.ERROR)

    def test_stop_recording_not_recording_returns_true(self):
        ctrl = OBSController(enabled_config())
        ctrl.client = mock.MagicMock()
        ctrl.client.get_record_status.return_value = mock.MagicMock(
            output_active=False, outputActive=False
        )
        ctrl.recording_started_by_app = True
        result = ctrl.stop_recording(show_errors=False)
        self.assertTrue(result)
        self.assertFalse(ctrl.recording_started_by_app)


# ---------------------------------------------------------------------------
# #32: Security — no secrets in status strings
# ---------------------------------------------------------------------------

class OBSStatusSecurityTest(unittest.TestCase):
    FORBIDDEN_PATTERNS = [
        "C:\\Users\\",
        "password=",
        "Password=",
        "CHANGE_ME",
    ]

    def _assert_safe(self, text: str) -> None:
        for pattern in self.FORBIDDEN_PATTERNS:
            self.assertNotIn(pattern, text,
                             f"Status text must not contain {pattern!r}")

    def test_all_status_code_display_texts_are_safe(self):
        from playcue.ui import i18n
        for lang in ("ja", "en"):
            i18n.set_language(lang)
            for code in vars(OBSStatus).values():
                if not isinstance(code, str):
                    continue
                self._assert_safe(obs_status_text(code))
        i18n.set_language("ja")

    def test_error_status_does_not_contain_path(self):
        ctrl = OBSController(enabled_config())
        ctrl._set_error("OBS の起動に失敗しました。")
        self._assert_safe(ctrl.status)


if __name__ == "__main__":
    unittest.main()
