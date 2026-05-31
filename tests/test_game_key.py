"""v0.8-01: GameConfig.get_game_key() の単体テスト"""
import unittest
from pathlib import Path

from playcue.models import GameConfig


class GameKeyTest(unittest.TestCase):
    def _cfg(self, **kwargs) -> GameConfig:
        return GameConfig(game_name="Game", config_file=Path("."), **kwargs)

    def test_active_process_name_takes_priority(self):
        cfg = self._cfg(process_name="launcher.exe", active_process_name="GAME.exe")
        self.assertEqual(cfg.get_game_key(), "game.exe")

    def test_uses_process_name_when_active_empty(self):
        cfg = self._cfg(process_name="ELDENRING.exe")
        self.assertEqual(cfg.get_game_key(), "eldenring.exe")

    def test_lowercases_result(self):
        cfg = self._cfg(process_name="GAME.EXE")
        self.assertEqual(cfg.get_game_key(), "game.exe")

    def test_strips_leading_trailing_whitespace(self):
        cfg = self._cfg(process_name="  game.exe  ")
        self.assertEqual(cfg.get_game_key(), "game.exe")

    def test_comma_separated_uses_first_valid(self):
        cfg = self._cfg(process_name="steam.exe, ELDENRING.exe")
        self.assertEqual(cfg.get_game_key(), "steam.exe")

    def test_semicolon_separated_uses_first_valid(self):
        cfg = self._cfg(process_name="Game.exe; Launcher.exe")
        self.assertEqual(cfg.get_game_key(), "game.exe")

    def test_active_process_name_comma_uses_first(self):
        cfg = self._cfg(process_name="launcher.exe", active_process_name="GAME.exe, sub.exe")
        self.assertEqual(cfg.get_game_key(), "game.exe")

    def test_falls_back_to_game_name_when_no_process(self):
        cfg = GameConfig(game_name="Example Game", config_file=Path("."))
        self.assertEqual(cfg.get_game_key(), "example_game")

    def test_game_name_spaces_become_underscores(self):
        cfg = GameConfig(game_name="My Cool Game 2", config_file=Path("."))
        self.assertEqual(cfg.get_game_key(), "my_cool_game_2")

    def test_game_name_lowercased_in_fallback(self):
        cfg = GameConfig(game_name="ELDENRING", config_file=Path("."))
        self.assertEqual(cfg.get_game_key(), "eldenring")

    def test_same_process_name_produces_same_key(self):
        cfg_a = self._cfg(process_name="ELDENRING.exe")
        cfg_b = self._cfg(process_name="eldenring.exe")
        self.assertEqual(cfg_a.get_game_key(), cfg_b.get_game_key())


if __name__ == "__main__":
    unittest.main()
