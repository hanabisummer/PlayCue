import tempfile
import unittest
import json
from pathlib import Path

import PlayCue
from PlayCue import ConfigLoader, GameProcessWatcher
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

    def test_watcher_waits_until_game_process_before_exit(self):
        class FakeProc:
            def __init__(self, name):
                self.info = {"name": name, "exe": ""}

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


if __name__ == "__main__":
    unittest.main()
