import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()

