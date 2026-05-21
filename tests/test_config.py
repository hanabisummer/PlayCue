import tempfile
import unittest
import json
from pathlib import Path

import PlayCue
from PlayCue import ConfigLoader, GameProcessWatcher, LoginBonusChecker, LoginBonusLogger
from shorts_agent.config import AgentConfig


class ConfigTest(unittest.TestCase):
    def test_default_output_base(self):
        cfg = AgentConfig()
        self.assertEqual(cfg.data["output"]["base_dir"], "outputs")

    def test_input_video_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "sample.mkv"
            video.write_bytes(b"dummy")
            cfg = AgentConfig().with_input(video)
            self.assertEqual(cfg.input_videos(), [video.resolve()])

    def test_game_config_active_process_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "game.json"
            config_path.write_text(json.dumps({"game_name": "Game"}), encoding="utf-8")
            cfg = ConfigLoader.load(config_path)
            self.assertFalse(cfg.launch_unelevated)
            self.assertEqual(cfg.active_process_name, "")

    def test_game_config_active_process_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "game.json"
            config_path.write_text(
                json.dumps(
                    {
                        "game_name": "Game",
                        "launch_unelevated": True,
                        "process_name": "launcher.exe,game.exe",
                        "active_process_name": "game.exe",
                    }
                ),
                encoding="utf-8",
            )
            cfg = ConfigLoader.load(config_path)
            self.assertTrue(cfg.launch_unelevated)
            self.assertEqual(cfg.process_name, "launcher.exe,game.exe")
            self.assertEqual(cfg.active_process_name, "game.exe")

    def test_login_bonus_config_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "game.json"
            config_path.write_text(
                json.dumps(
                    {
                        "game_name": "Game",
                        "login_bonus": {
                            "enabled": True,
                            "reset_time": "5:00",
                            "game_screen": {
                                "enabled": True,
                                "window_title": "Game Window",
                                "claimed_patterns": ["claimed"],
                                "timeout_seconds": 300,
                            },
                            "web": {
                                "enabled": True,
                                "url": "https://example.com/bonus",
                                "unclaimed_patterns": ["claim"],
                                "timeout_seconds": 30,
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            cfg = ConfigLoader.load(config_path)
            self.assertTrue(cfg.login_bonus.enabled)
            self.assertEqual(cfg.login_bonus.reset_time, "05:00")
            self.assertEqual(cfg.login_bonus.game_screen.window_title, "Game Window")
            self.assertEqual(cfg.login_bonus.game_screen.claimed_patterns, ("claimed",))
            self.assertEqual(cfg.login_bonus.web.url, "https://example.com/bonus")
            self.assertEqual(cfg.login_bonus.web.unclaimed_patterns, ("claim",))

    def test_login_bonus_date_uses_reset_time(self):
        self.assertEqual(
            LoginBonusLogger.bonus_date(PlayCue.datetime(2026, 5, 20, 4, 59), "05:00").isoformat(),
            "2026-05-19",
        )
        self.assertEqual(
            LoginBonusLogger.bonus_date(PlayCue.datetime(2026, 5, 20, 5, 0), "05:00").isoformat(),
            "2026-05-20",
        )

    def test_login_bonus_logger_ignores_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "game.json"
            config_path.write_text(
                json.dumps({"game_name": "Game", "login_bonus": {"enabled": True}}),
                encoding="utf-8",
            )
            cfg = ConfigLoader.load(config_path)
            original_log_file = PlayCue.LOGIN_BONUS_LOG_FILE
            PlayCue.LOGIN_BONUS_LOG_FILE = Path(tmp) / "login_bonus_history.csv"
            try:
                logger = LoginBonusLogger()
                logger.save(cfg, "game_screen", "unknown")
                self.assertFalse(PlayCue.LOGIN_BONUS_LOG_FILE.exists())
                logger.save(cfg, "game_screen", "claimed", evidence="claimed", method="manual", manual=True)
                self.assertEqual(logger.latest(cfg, "game_screen")["status"], "claimed")
            finally:
                PlayCue.LOGIN_BONUS_LOG_FILE = original_log_file

    def test_login_bonus_checker_matches_patterns(self):
        source = PlayCue.LoginBonusSourceConfig(
            claimed_patterns=("claimed",),
            unclaimed_patterns=("claim",),
        )
        self.assertEqual(LoginBonusChecker._match_text("Daily bonus claimed", source), ("claimed", "claimed", "ocr"))
        self.assertEqual(LoginBonusChecker._match_text("Tap claim", source), ("unclaimed", "claim", "ocr"))

    def test_game_site_searcher_extracts_candidates(self):
        html = """
        <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com%2Fgame">Other Site</a>
        <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com%2Fgame%2Fwiki">Other Site Wiki</a>
        <a class="result__a" href="/l/?uddg=https%3A%2F%2Fpcgamingwiki.com%2Fwiki%2FGame">Game - PCGamingWiki</a>
        <a class="result__a" href="https://duckduckgo.com/about">DuckDuckGo</a>
        <a class="result__a" href="https://www.pcgamingwiki.com/wiki/Game#section">Game - PCGamingWiki</a>
        """
        links = PlayCue.GameSiteSearcher.links_from_html(html, max_results=3)
        self.assertEqual(links[0].name, "Game - PCGamingWiki")
        self.assertEqual(links[0].url, "https://pcgamingwiki.com/wiki/Game")
        self.assertEqual(len(links), 2)

    def test_game_site_searcher_normalizes_urls(self):
        self.assertEqual(
            PlayCue.GameSiteSearcher.normalized_url_key("https://www.example.com/path/#top"),
            "https://example.com/path",
        )

    def test_watcher_waits_until_game_process_before_exit(self):
        class FakeProc:
            def __init__(self, name, exe=""):
                self.info = {"name": name, "exe": exe}

        class FakePsutil:
            NoSuchProcess = Exception
            AccessDenied = Exception

            def __init__(self):
                self.names = []

            def process_iter(self, _attrs):
                return [FakeProc(name) for name in self.names]

        fake_psutil = FakePsutil()
        original_psutil = PlayCue.psutil
        PlayCue.psutil = fake_psutil
        active_calls = []
        exit_calls = []
        try:
            watcher = GameProcessWatcher(
                "game.exe",
                lambda: exit_calls.append(True),
                grace_seconds=0,
                missing_threshold=1,
                active_process_name="game.exe",
                on_active=lambda: active_calls.append(True),
            )
            watcher.tick()
            self.assertEqual(active_calls, [])
            self.assertEqual(exit_calls, [])

            fake_psutil.names = ["game.exe"]
            watcher.tick()
            self.assertEqual(active_calls, [True])
            self.assertEqual(exit_calls, [])

            fake_psutil.names = []
            watcher.tick()
            self.assertEqual(exit_calls, [True])
        finally:
            PlayCue.psutil = original_psutil

    def test_watcher_exits_when_launcher_closes_before_game_starts(self):
        class FakeProc:
            def __init__(self, name, exe=""):
                self.info = {"name": name, "exe": exe}

        class FakePsutil:
            NoSuchProcess = Exception
            AccessDenied = Exception

            def __init__(self):
                self.procs = []

            def process_iter(self, _attrs):
                return self.procs

        fake_psutil = FakePsutil()
        original_psutil = PlayCue.psutil
        PlayCue.psutil = fake_psutil
        active_calls = []
        exit_calls = []
        try:
            launcher_path = str(Path("C:/Games/Launcher.exe").resolve())
            watcher = GameProcessWatcher(
                "game.exe",
                lambda: exit_calls.append(True),
                grace_seconds=0,
                missing_threshold=1,
                exe_path=launcher_path,
                active_process_name="game.exe",
                on_active=lambda: active_calls.append(True),
            )

            fake_psutil.procs = [FakeProc("Launcher.exe", launcher_path)]
            watcher.tick()
            self.assertEqual(active_calls, [])
            self.assertEqual(exit_calls, [])

            fake_psutil.procs = []
            watcher.tick()
            self.assertEqual(active_calls, [])
            self.assertEqual(exit_calls, [True])
        finally:
            PlayCue.psutil = original_psutil


if __name__ == "__main__":
    unittest.main()
