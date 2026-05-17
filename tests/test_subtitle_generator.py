import tempfile
import unittest
from pathlib import Path

from shorts_agent.subtitle_generator import generate_ass, generate_srt


class SubtitleGeneratorTest(unittest.TestCase):
    def test_generate_subtitles(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            srt = generate_srt("これはテストなのだ。字幕を作るのだ。", None, base / "test.srt")
            ass = generate_ass("これはテストなのだ。字幕を作るのだ。", None, base / "test.ass", {})
            self.assertTrue(srt.exists())
            self.assertTrue(ass.exists())
            self.assertIn("[Events]", ass.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

