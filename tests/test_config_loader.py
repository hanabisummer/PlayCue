import json
import tempfile
import unittest
from json import JSONDecodeError
from pathlib import Path

from playcue.config.loader import ConfigLoader
from playcue.config.validator import ConfigLoadResult, ConfigValidationIssue


class ConfigLoaderTest(unittest.TestCase):
    def test_loads_example_config(self):
        cfg = ConfigLoader.load(Path("configs/example.json"))

        self.assertEqual(cfg.game_name, "Example Game")
        self.assertEqual(cfg.game_exe, "C:/Path/To/Game.exe")
        self.assertEqual(cfg.active_process_name, "")
        self.assertEqual(cfg.obs.websocket_port, 4455)
        self.assertEqual(cfg.obs.websocket_password, "CHANGE_ME")
        self.assertFalse(cfg.obs.auto_start_recording_on_game_launch)
        self.assertFalse(cfg.obs.auto_stop_recording_on_game_exit)
        self.assertEqual(cfg.login_bonus.reset_time, "05:00")
        self.assertIn("取得済み", cfg.login_bonus.game_screen.claimed_patterns)
        self.assertIn("受け取る", cfg.login_bonus.game_screen.unclaimed_patterns)
        self.assertEqual(len(cfg.auto_open_links), 0)
        self.assertEqual(cfg.buttons[0].name, "Official Site")
        self.assertEqual(cfg.buttons[0].url, "https://example.com")

    def test_missing_file_raises_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "missing.json"

            with self.assertRaises(FileNotFoundError):
                ConfigLoader.load(missing_path)

    def test_broken_json_raises_json_decode_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "broken.json"
            config_path.write_text("{", encoding="utf-8")

            with self.assertRaises(JSONDecodeError):
                ConfigLoader.load(config_path)

    def test_blank_game_name_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "blank.json"
            config_path.write_text(json.dumps({"game_name": "  "}), encoding="utf-8")

            with self.assertRaises(ValueError):
                ConfigLoader.load(config_path)

    def test_list_configs_loads_json_files_in_name_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            (config_dir / "b.json").write_text(json.dumps({"game_name": "B"}), encoding="utf-8")
            (config_dir / "a.json").write_text(json.dumps({"game_name": "A"}), encoding="utf-8")
            (config_dir / "ignore.txt").write_text(json.dumps({"game_name": "Ignored"}), encoding="utf-8")

            configs = ConfigLoader.list_configs(config_dir)

            self.assertEqual([cfg.game_name for cfg in configs], ["A", "B"])

    def test_loader_normalizes_bounds_and_ignores_invalid_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "bounds.json"
            config_path.write_text(
                json.dumps(
                    {
                        "game_name": "Game",
                        "opacity": 2,
                        "window_width": 0,
                        "window_height": "invalid",
                        "auto_open_links": [
                            {"name": " Guide ", "url": " https://example.com/guide "},
                            {"name": "", "url": "https://example.com/blank-name"},
                            "invalid",
                        ],
                        "obs": {
                            "websocket_port": 0,
                            "connect_timeout_seconds": "invalid",
                            "connect_retry_interval_seconds": -1,
                        },
                    }
                ),
                encoding="utf-8",
            )

            cfg = ConfigLoader.load(config_path)

            self.assertEqual(cfg.opacity, 1.0)
            self.assertEqual(cfg.window_width, 360)
            self.assertEqual(cfg.window_height, 420)
            self.assertEqual([(link.name, link.url) for link in cfg.auto_open_links], [("Guide", "https://example.com/guide")])
            self.assertEqual(cfg.obs.websocket_port, 4455)
            self.assertEqual(cfg.obs.connect_timeout_seconds, 30)
            self.assertEqual(cfg.obs.connect_retry_interval_seconds, 2)

    def test_login_bonus_defaults_and_fallback_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "login_bonus.json"
            config_path.write_text(
                json.dumps(
                    {
                        "game_name": "Game",
                        "login_bonus": {
                            "enabled": True,
                            "reset_time": "25:00",
                            "claimed_patterns": ["claimed"],
                            "unclaimed_patterns": "claim",
                            "game_screen": {
                                "enabled": True,
                                "timeout_seconds": 0,
                                "retry_interval_seconds": "invalid",
                            },
                            "web": "invalid",
                        },
                    }
                ),
                encoding="utf-8",
            )

            cfg = ConfigLoader.load(config_path)

            self.assertTrue(cfg.login_bonus.enabled)
            self.assertEqual(cfg.login_bonus.reset_time, "05:00")
            self.assertEqual(cfg.login_bonus.game_screen.claimed_patterns, ("claimed",))
            self.assertEqual(cfg.login_bonus.game_screen.unclaimed_patterns, ("claim",))
            self.assertEqual(cfg.login_bonus.game_screen.timeout_seconds, 300)
            self.assertEqual(cfg.login_bonus.game_screen.retry_interval_seconds, 5)
            self.assertEqual(cfg.login_bonus.web.claimed_patterns, ("claimed",))
            self.assertEqual(cfg.login_bonus.web.unclaimed_patterns, ("claim",))
            self.assertEqual(cfg.login_bonus.web.timeout_seconds, 30)


class ListConfigsWithIssuesTest(unittest.TestCase):
    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _write(directory: Path, name: str, data: object) -> None:
        (directory / name).write_text(json.dumps(data), encoding="utf-8")

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_returns_empty_result_for_nonexistent_directory(self):
        result = ConfigLoader.list_configs_with_issues(Path("/nonexistent/dir"))
        self.assertIsInstance(result, ConfigLoadResult)
        self.assertEqual(result.configs, [])
        self.assertEqual(result.issues, [])

    def test_loads_valid_configs_with_no_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._write(d, "a.json", {"game_name": "Alpha"})
            self._write(d, "b.json", {"game_name": "Beta"})

            result = ConfigLoader.list_configs_with_issues(d)

            self.assertEqual([c.game_name for c in result.configs], ["Alpha", "Beta"])
            self.assertEqual(result.issues, [])
            self.assertFalse(result.has_errors)
            self.assertFalse(result.has_warnings)

    # ------------------------------------------------------------------
    # Error-level issues — file is skipped from configs
    # ------------------------------------------------------------------

    def test_broken_json_recorded_as_error_and_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "broken.json").write_text("{", encoding="utf-8")
            self._write(d, "good.json", {"game_name": "Good"})

            result = ConfigLoader.list_configs_with_issues(d)

            self.assertEqual([c.game_name for c in result.configs], ["Good"])
            self.assertEqual(len(result.issues), 1)
            issue = result.issues[0]
            self.assertEqual(issue.level, "error")
            self.assertEqual(issue.file, "broken.json")
            self.assertTrue(result.has_errors)

    def test_blank_game_name_recorded_as_error_and_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._write(d, "blank.json", {"game_name": "  "})
            self._write(d, "ok.json", {"game_name": "OK"})

            result = ConfigLoader.list_configs_with_issues(d)

            self.assertEqual([c.game_name for c in result.configs], ["OK"])
            self.assertEqual(len(result.issues), 1)
            self.assertEqual(result.issues[0].level, "error")
            self.assertEqual(result.issues[0].file, "blank.json")
            self.assertEqual(result.issues[0].field, "game_name")

    def test_multiple_broken_files_all_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "bad1.json").write_text("{", encoding="utf-8")
            self._write(d, "bad2.json", {"game_name": ""})
            self._write(d, "good.json", {"game_name": "Good"})

            result = ConfigLoader.list_configs_with_issues(d)

            self.assertEqual(len(result.configs), 1)
            self.assertEqual(len(result.issues), 2)
            self.assertTrue(all(i.level == "error" for i in result.issues))

    def test_all_broken_returns_empty_configs(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "x.json").write_text("{", encoding="utf-8")

            result = ConfigLoader.list_configs_with_issues(d)

            self.assertEqual(result.configs, [])
            self.assertTrue(result.has_errors)

    # ------------------------------------------------------------------
    # Warning-level issues — file IS included in configs
    # ------------------------------------------------------------------

    def test_missing_game_exe_recorded_as_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._write(d, "game.json", {
                "game_name": "Game",
                "game_exe": "/nonexistent/Game.exe",
            })

            result = ConfigLoader.list_configs_with_issues(d)

            # Config is still returned
            self.assertEqual(len(result.configs), 1)
            self.assertEqual(result.configs[0].game_name, "Game")
            # Warning is recorded
            self.assertEqual(len(result.issues), 1)
            self.assertEqual(result.issues[0].level, "warning")
            self.assertEqual(result.issues[0].field, "game_exe")
            self.assertTrue(result.has_warnings)
            self.assertFalse(result.has_errors)

    def test_invalid_button_url_recorded_as_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._write(d, "game.json", {
                "game_name": "Game",
                "buttons": [
                    {"name": "Good Link", "url": "https://example.com"},
                    {"name": "Bad Link", "url": "not-a-url"},
                ],
            })

            result = ConfigLoader.list_configs_with_issues(d)

            self.assertEqual(len(result.configs), 1)
            warnings = [i for i in result.issues if i.level == "warning"]
            self.assertEqual(len(warnings), 1)
            self.assertEqual(warnings[0].field, "buttons.url")
            self.assertIn("Bad Link", warnings[0].message)

    def test_issue_file_field_contains_filename_only(self):
        """Issue.file must never be an absolute path."""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "broken.json").write_text("{", encoding="utf-8")

            result = ConfigLoader.list_configs_with_issues(d)

            self.assertEqual(result.issues[0].file, "broken.json")
            self.assertNotIn("\\", result.issues[0].file)
            self.assertNotIn("/", result.issues[0].file)

    # ------------------------------------------------------------------
    # _is_valid_url_or_path
    # ------------------------------------------------------------------

    def test_valid_url_schemes(self):
        valid = [
            "https://example.com",
            "http://example.com/guide",
            "file:///C:/notes.txt",
            "steam://rungameid/12345",
        ]
        for url in valid:
            with self.subTest(url=url):
                self.assertTrue(ConfigLoader._is_valid_url_or_path(url))

    def test_valid_windows_paths(self):
        valid = [
            "C:/Users/notes.txt",
            "C:\\Users\\notes.txt",
            "D:/games/memo.txt",
        ]
        for url in valid:
            with self.subTest(url=url):
                self.assertTrue(ConfigLoader._is_valid_url_or_path(url))

    def test_invalid_urls(self):
        invalid = [
            "not-a-url",
            "just some text",
            "ftp://legacy.example.com",  # ftp not in allowed list
            "",
        ]
        for url in invalid:
            with self.subTest(url=url):
                self.assertFalse(ConfigLoader._is_valid_url_or_path(url))


class ExampleJsonFilterTest(unittest.TestCase):
    """Verify that example.json is excluded from the game list at the app level.

    The filtering itself lives in PlayCue.py:resolve_configs(), but the logic
    is simple enough to test via ConfigLoader.list_configs() + a name filter,
    mirroring exactly what resolve_configs() does.
    """

    @staticmethod
    def _write(directory: Path, name: str, data: object) -> None:
        (directory / name).write_text(json.dumps(data), encoding="utf-8")

    def test_example_json_is_excluded_by_name_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._write(d, "example.json", {"game_name": "Example Game"})
            self._write(d, "my_game.json", {"game_name": "My Game"})

            all_configs = ConfigLoader.list_configs(d)
            filtered = [c for c in all_configs if c.config_file.name != "example.json"]

            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0].game_name, "My Game")

    def test_only_example_json_yields_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._write(d, "example.json", {"game_name": "Example Game"})

            all_configs = ConfigLoader.list_configs(d)
            filtered = [c for c in all_configs if c.config_file.name != "example.json"]

            self.assertEqual(filtered, [])

    def test_no_json_files_yields_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)

            all_configs = ConfigLoader.list_configs(d)

            self.assertEqual(all_configs, [])


if __name__ == "__main__":
    unittest.main()
