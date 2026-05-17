import tempfile
import unittest
from pathlib import Path

from shorts_agent.source_guard import assert_safe_output_path, collect_source_info, verify_source_unchanged


class SourceGuardTest(unittest.TestCase):
    def test_hash_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.mp4"
            source.write_bytes(b"abc")
            before = collect_source_info(source)
            after = verify_source_unchanged(before, source)
            self.assertTrue(after["source_unchanged"])

    def test_reject_same_input_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.mp4"
            source.write_bytes(b"abc")
            with self.assertRaises(ValueError):
                assert_safe_output_path(source, source, Path(tmp) / "outputs")


if __name__ == "__main__":
    unittest.main()

