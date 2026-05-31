import unittest
from pathlib import Path

from playcue.models import GameConfig, LinkItem, LoginBonusConfig, OBSConfig


class ModelsTest(unittest.TestCase):
    def test_game_config_defaults(self):
        cfg = GameConfig(game_name="Game", config_file=Path("game.json"))

        self.assertEqual(cfg.obs, OBSConfig())
        self.assertEqual(cfg.login_bonus, LoginBonusConfig())
        self.assertEqual(cfg.auto_open_links, ())
        self.assertEqual(cfg.buttons, ())

    def test_login_bonus_defaults(self):
        cfg = LoginBonusConfig()

        self.assertEqual(cfg.reset_time, "05:00")
        self.assertEqual(cfg.game_screen.timeout_seconds, 300)
        self.assertEqual(cfg.web.timeout_seconds, 30)

    def test_link_item_fields(self):
        link = LinkItem(name="Guide", url="https://example.com")

        self.assertEqual(link.name, "Guide")
        self.assertEqual(link.url, "https://example.com")


if __name__ == "__main__":
    unittest.main()
