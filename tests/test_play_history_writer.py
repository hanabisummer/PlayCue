import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from playcue.logs.play_history_writer import PlayTimeLogger
from playcue.models import GameConfig


class PlayHistoryWriterTest(unittest.TestCase):
    def read_rows(self, log_path):
        with log_path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.reader(f))

    def read_dict_rows(self, log_path):
        with log_path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def save_log(self, tmp, config, elapsed_seconds=3661):
        base_dir = Path(tmp)
        log_file = base_dir / "logs" / "play_history.csv"
        session_start = datetime(2026, 5, 26, 7, 0, 0)

        with (
            mock.patch("playcue.logs.play_history_writer.BASE_DIR", base_dir),
            mock.patch("playcue.logs.play_history_writer.LOG_FILE", log_file),
            mock.patch("playcue.logs.play_history_writer.datetime") as mocked_datetime,
        ):
            mocked_datetime.now.return_value = datetime(2026, 5, 26, 8, 1, 1)
            PlayTimeLogger().save(config, session_start, elapsed_seconds)

        return log_file

    def test_format_hhmmss(self):
        self.assertEqual(PlayTimeLogger.format_hhmmss(0), "00:00:00")
        self.assertEqual(PlayTimeLogger.format_hhmmss(59), "00:00:59")
        self.assertEqual(PlayTimeLogger.format_hhmmss(60), "00:01:00")
        self.assertEqual(PlayTimeLogger.format_hhmmss(3661), "01:01:01")
        self.assertEqual(PlayTimeLogger.format_hhmmss(-1), "00:00:00")

    def test_creates_missing_log_file_with_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = GameConfig(game_name="Game", config_file=Path(tmp) / "outside.json")

            log_file = self.save_log(tmp, config)

            rows = self.read_rows(log_file)
            self.assertEqual(rows[0], PlayTimeLogger.HEADER)
            self.assertEqual(len(rows), 2)

    def test_append_does_not_duplicate_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = GameConfig(game_name="Game", config_file=Path(tmp) / "outside.json")
            log_file = self.save_log(tmp, config)

            self.save_log(tmp, config, elapsed_seconds=60)

            rows = self.read_rows(log_file)
            self.assertEqual(rows.count(PlayTimeLogger.HEADER), 1)
            self.assertEqual(len(rows), 3)

    def test_writes_elapsed_seconds_and_hhmmss(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = GameConfig(game_name="Game", config_file=Path(tmp) / "outside.json")

            log_file = self.save_log(tmp, config, elapsed_seconds=3661)

            row = self.read_dict_rows(log_file)[0]
            self.assertEqual(row["elapsed_seconds"], "3661")
            self.assertEqual(row["elapsed_hhmmss"], "01:01:01")

    def test_config_file_outside_base_dir_is_masked(self):
        """config_file outside BASE_DIR is stored as 'external:<name>' not the full path.

        This prevents usernames (C:\\Users\\username\\...) from appearing in
        play_history.csv and in any bug-report screenshots shared by users.
        """
        with tempfile.TemporaryDirectory() as base_tmp:
            with tempfile.TemporaryDirectory() as external_tmp:
                external_config = Path(external_tmp) / "my_game.json"
                config = GameConfig(game_name="Game", config_file=external_config)

                log_file = self.save_log(base_tmp, config)

                row = self.read_dict_rows(log_file)[0]
                self.assertEqual(row["config_file"], "external:my_game.json")
                # Full external path must not appear in the CSV.
                self.assertNotIn(external_tmp, row["config_file"])

    def test_config_file_under_base_dir_is_relative(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "configs" / "game.json"
            config = GameConfig(game_name="Game", config_file=config_file)

            log_file = self.save_log(tmp, config)

            row = self.read_dict_rows(log_file)[0]
            self.assertEqual(row["config_file"], str(Path("configs") / "game.json"))

    def test_save_keeps_existing_csv_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            log_file = base_dir / "logs" / "play_history.csv"
            config_file = base_dir / "configs" / "game.json"
            config = GameConfig(game_name="Game", config_file=config_file, process_name="game.exe")

            with (
                mock.patch("playcue.logs.play_history_writer.BASE_DIR", base_dir),
                mock.patch("playcue.logs.play_history_writer.LOG_FILE", log_file),
                mock.patch("playcue.logs.play_history_writer.datetime") as mocked_datetime,
            ):
                mocked_datetime.now.return_value = datetime(2026, 5, 20, 12, 34, 56)
                PlayTimeLogger().save(config, datetime(2026, 5, 20, 12, 0, 0), 125)

            rows = self.read_rows(log_file)

            self.assertEqual(rows[0], PlayTimeLogger.HEADER)
            self.assertEqual(
                rows[1],
                [
                    "2026-05-20 12:00:00",
                    "2026-05-20 12:34:56",
                    "2026-05-20",
                    "Game",
                    "125",
                    "00:02:05",
                    str(Path("configs") / "game.json"),
                    "game.exe",   # game_key
                    "game.exe",   # process_name
                    "",           # active_process_name
                    "",           # game_exe_name
                ],
            )


    # ------------------------------------------------------------------
    # #25: log write failure — OSError must propagate to caller
    # ------------------------------------------------------------------

    def test_save_propagates_oserror_on_write_failure(self):
        """save() does not swallow OSError — the caller (save_log_once) handles display.

        This contract is important: if save() silently discarded the error, the
        UI layer would mark log_saved=True and the session would be lost silently.
        The error must reach save_log_once() so it can inform the user.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            log_dir = base_dir / "logs"
            log_dir.mkdir()

            # Build a mock LOG_FILE whose .open() raises PermissionError.
            mock_log = mock.MagicMock(spec=Path)
            mock_log.parent = log_dir          # real dir so mkdir() is a no-op
            mock_log.exists.return_value = False
            mock_log.open.side_effect = PermissionError("simulated: permission denied")

            config = GameConfig(game_name="Game", config_file=base_dir / "outside.json")

            with (
                mock.patch("playcue.logs.play_history_writer.BASE_DIR", base_dir),
                mock.patch("playcue.logs.play_history_writer.LOG_FILE", mock_log),
            ):
                with self.assertRaises(OSError):
                    PlayTimeLogger().save(config, datetime(2026, 5, 26, 7, 0, 0), 60)

    # ------------------------------------------------------------------
    # #24: log auto-creation stability
    # ------------------------------------------------------------------

    def test_logs_directory_is_created_automatically(self):
        """save() creates the logs/ directory when it does not exist."""
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            log_dir = base_dir / "logs"
            log_file = log_dir / "play_history.csv"
            config = GameConfig(game_name="Game", config_file=base_dir / "outside.json")

            self.assertFalse(log_dir.exists(), "pre-condition: logs/ must not exist yet")

            with (
                mock.patch("playcue.logs.play_history_writer.BASE_DIR", base_dir),
                mock.patch("playcue.logs.play_history_writer.LOG_FILE", log_file),
                mock.patch("playcue.logs.play_history_writer.datetime") as mocked_dt,
            ):
                mocked_dt.now.return_value = datetime(2026, 5, 26, 8, 0, 0)
                PlayTimeLogger().save(config, datetime(2026, 5, 26, 7, 0, 0), 60)

            self.assertTrue(log_dir.exists(), "logs/ directory should have been created")
            self.assertTrue(log_file.exists(), "play_history.csv should have been created")

    def test_csv_is_utf8_bom_encoded(self):
        """Log file starts with UTF-8 BOM so Excel opens it without garbling."""
        with tempfile.TemporaryDirectory() as tmp:
            config = GameConfig(game_name="Game", config_file=Path(tmp) / "outside.json")
            log_file = self.save_log(tmp, config)

            raw_bytes = log_file.read_bytes()
            self.assertTrue(
                raw_bytes.startswith(b"\xef\xbb\xbf"),
                "File should start with UTF-8 BOM (\\xef\\xbb\\xbf)",
            )

    def test_multiple_saves_preserve_all_rows(self):
        """All sessions are retained across repeated save() calls."""
        with tempfile.TemporaryDirectory() as tmp:
            config = GameConfig(game_name="RPG", config_file=Path(tmp) / "outside.json")
            log_file = self.save_log(tmp, config, elapsed_seconds=3600)
            self.save_log(tmp, config, elapsed_seconds=7200)
            self.save_log(tmp, config, elapsed_seconds=1800)

            rows = self.read_dict_rows(log_file)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["elapsed_seconds"], "3600")
            self.assertEqual(rows[1]["elapsed_seconds"], "7200")
            self.assertEqual(rows[2]["elapsed_seconds"], "1800")

    def test_header_columns_match_expected_spec(self):
        """HEADER constant matches the documented v0.8 CSV column spec."""
        expected = [
            "session_start",
            "session_end",
            "date",
            "game_name",
            "elapsed_seconds",
            "elapsed_hhmmss",
            "config_file",
            "game_key",
            "process_name",
            "active_process_name",
            "game_exe_name",
        ]
        self.assertEqual(PlayTimeLogger.HEADER, expected)

    def test_writes_game_key_column(self):
        """game_key列にget_game_key()の値が記録される。"""
        with tempfile.TemporaryDirectory() as tmp:
            config = GameConfig(
                game_name="Elden Ring",
                config_file=Path(tmp) / "outside.json",
                active_process_name="ELDENRING.exe",
            )
            log_file = self.save_log(tmp, config)
            row = self.read_dict_rows(log_file)[0]
            self.assertEqual(row["game_key"], "eldenring.exe")

    def test_game_exe_name_does_not_include_full_path(self):
        """game_exe_nameはファイル名のみでフルパスを含まない。"""
        with tempfile.TemporaryDirectory() as tmp:
            config = GameConfig(
                game_name="Game",
                config_file=Path(tmp) / "outside.json",
                game_exe=r"C:\Games\MyGame\game.exe",
            )
            log_file = self.save_log(tmp, config)
            row = self.read_dict_rows(log_file)[0]
            self.assertEqual(row["game_exe_name"], "game.exe")
            self.assertNotIn("C:\\", row["game_exe_name"])

    def test_old_csv_without_new_columns_is_readable(self):
        """game_key列がない旧フォーマットのCSVでも読み込みでエラーが起きない。"""
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            log_file = base_dir / "logs" / "play_history.csv"
            log_file.parent.mkdir(parents=True)
            old_header = [
                "session_start", "session_end", "date", "game_name",
                "elapsed_seconds", "elapsed_hhmmss", "config_file",
            ]
            with log_file.open("w", encoding="utf-8-sig", newline="") as f:
                import csv as _csv
                w = _csv.writer(f)
                w.writerow(old_header)
                w.writerow([
                    "2026-01-01 10:00:00", "2026-01-01 11:00:00",
                    "2026-01-01", "OldGame", "3600", "01:00:00",
                    "configs/old.json",
                ])

            with log_file.open("r", encoding="utf-8-sig", newline="") as f:
                import csv as _csv
                rows = list(_csv.DictReader(f))

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["game_name"], "OldGame")
            self.assertIsNone(rows[0].get("game_key"))


if __name__ == "__main__":
    unittest.main()
