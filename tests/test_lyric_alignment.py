import unittest

from scripts.review_lyric_alignment import match_lines


class LyricEvidenceTests(unittest.TestCase):
    def test_repeated_phrases_match_distinct_audio_occurrences(self):
        words = [{"word": "samephrase", "start": s, "end": s + 2, "probability": .95} for s in (1, 10)]
        rows = match_lines(["samephrase", "samephrase"], [{"words": words}])
        self.assertEqual([r["asr_start_ms"] for r in rows], [1000, 10000])
        self.assertTrue(all(not r["anchor_candidate"] for r in rows))
        self.assertTrue(all("repeated_source_phrase_occurrence_unverified" in r["alignment_warnings"] for r in rows))

    def test_unique_contiguous_phrase_can_be_a_candidate(self):
        row = match_lines(["unique phrase"], [{"words": [
            {"word": "unique", "start": 1, "end": 2, "probability": .95},
            {"word": "phrase", "start": 2.1, "end": 3, "probability": .95},
        ]}])[0]
        self.assertTrue(row["anchor_candidate"])
        self.assertEqual(row["alignment_warnings"], [])

    def test_words_from_distant_verses_are_not_a_candidate(self):
        row = match_lines(["unique phrase"], [{"words": [
            {"word": "unique", "start": 1, "end": 2, "probability": .99},
            {"word": "phrase", "start": 101, "end": 103, "probability": .99},
        ]}])[0]
        self.assertFalse(row["anchor_candidate"])
        self.assertIn("large_gap_between_matched_words", row["alignment_warnings"])

    def test_missing_asr_does_not_invent_times(self):
        row = match_lines(["phrase"], [])[0]
        self.assertFalse(row["anchor_candidate"])
        self.assertNotIn("asr_start_ms", row)

    def test_low_confidence_or_partial_edges_are_not_anchor_candidates(self):
        for word, confidence in [("longphrase", .2), ("ongphras", .99)]:
            row = match_lines(["longphrase"], [{"words": [
                {"word": word, "start": 1, "end": 3, "probability": confidence},
            ]}])[0]
            self.assertFalse(row["anchor_candidate"])

    def test_short_refrain_is_not_a_timing_anchor(self):
        row = match_lines(["yeah"], [{"words": [
            {"word": "yeah", "start": 1, "end": 3, "probability": .99},
        ]}])[0]
        self.assertFalse(row["anchor_candidate"])
