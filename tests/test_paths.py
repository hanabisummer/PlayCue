import unittest
import tempfile
from pathlib import Path

from playcue import paths


class PathsTest(unittest.TestCase):
    def test_source_tree_paths(self):
        base_dir = Path(__file__).resolve().parent.parent

        self.assertEqual(paths.app_base_dir(), base_dir)
        self.assertEqual(paths.config_dir(), base_dir / "configs")
        self.assertEqual(paths.log_dir(), base_dir / "logs")
        self.assertEqual(paths.play_history_log_file(), base_dir / "logs" / "play_history.csv")

    def test_resolve_app_path_keeps_absolute_path(self):
        absolute_path = Path(__file__).resolve()

        self.assertEqual(paths.resolve_app_path(absolute_path), absolute_path)

    def test_resolve_app_path_resolves_relative_path_from_base(self):
        base_dir = Path(__file__).resolve().parent.parent

        self.assertEqual(paths.resolve_app_path("configs/example.json"), base_dir / "configs" / "example.json")

    def test_frozen_paths_use_executable_directory(self):
        original_executable = paths.sys.executable
        had_frozen = hasattr(paths.sys, "frozen")
        original_frozen = getattr(paths.sys, "frozen", None)
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "PlayCue.exe"
            paths.sys.frozen = True
            paths.sys.executable = str(executable)
            try:
                self.assertEqual(paths.app_base_dir(), executable.resolve().parent)
                self.assertEqual(paths.script_path(), executable.resolve())
            finally:
                paths.sys.executable = original_executable
                if had_frozen:
                    paths.sys.frozen = original_frozen
                else:
                    delattr(paths.sys, "frozen")


if __name__ == "__main__":
    unittest.main()
