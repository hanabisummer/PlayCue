import tempfile
import unittest
from pathlib import Path

from shorts_agent.source_guard import assert_safe_output_path


class PathSafetyTest(unittest.TestCase):
    def test_reject_output_outside_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            source.write_bytes(b"abc")
            with self.assertRaises(ValueError):
                assert_safe_output_path(source, root / "final.mp4", root / "outputs")


if __name__ == "__main__":
    unittest.main()

