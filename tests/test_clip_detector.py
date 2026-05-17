import unittest

from shorts_agent.clip_detector import detect_highlight_candidates


class ClipDetectorTest(unittest.TestCase):
    def test_near_peaks_are_deduplicated(self):
        rms = [{"start_sec": i * 2, "end_sec": i * 2 + 2, "rms": 0.1} for i in range(100)]
        rms[30]["rms"] = 0.9
        rms[35]["rms"] = 0.85
        candidates = detect_highlight_candidates(
            rms,
            300,
            {
                "clip_duration_sec": 60,
                "pre_peak_sec": 20,
                "min_gap_between_clips_sec": 90,
                "max_clips_per_video": 5,
                "peak_threshold_percentile": 90,
                "ignore_first_sec": 0,
                "ignore_last_sec": 0,
            },
        )
        self.assertEqual(len(candidates), 1)


if __name__ == "__main__":
    unittest.main()

