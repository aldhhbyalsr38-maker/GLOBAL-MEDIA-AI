import json
import tempfile
import unittest
from pathlib import Path
from global_media_ai.production import build_production_pack, create_production_packs


class ProductionTests(unittest.TestCase):
    def sample_topic(self):
        return {
            "rank": 1,
            "source_title": "A new scientific discovery",
            "source": "Example Source",
            "source_url": "https://example.com/story",
            "corroborating_sources": [{"source": "Example Source", "url": "https://example.com/story"}],
            "quality_flags": ["single_source_only"],
            "english": {"summary_for_writer": "Researchers published a new study describing a scientific result. The complete article must be read and the claims checked independently before publication."},
        }

    def test_pack_has_two_language_tracks_and_storyboard(self):
        pack = build_production_pack(self.sample_topic())
        self.assertIn("en_draft", pack["scripts"])
        self.assertIn("ar_localization_template", pack["scripts"])
        self.assertGreaterEqual(len(pack["storyboard"]), 5)

    def test_single_source_is_blocked(self):
        pack = build_production_pack(self.sample_topic())
        self.assertEqual(pack["quality_gate"]["status"], "blocked_pending_verification")

    def test_no_claim_of_final_video_or_publication(self):
        pack = build_production_pack(self.sample_topic())
        notes = " ".join(pack["production_notes"])
        self.assertIn("No voice generation", notes)
        self.assertIn("not independently verified", notes)

    def test_writes_pack_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = {"topics": [self.sample_topic()]}
            source = root / "plan.json"
            source.write_text(json.dumps(plan), encoding="utf-8")
            files = create_production_packs(source, root / "production")
            self.assertEqual(len(files), 3)
            self.assertTrue((root / "production" / "production_index.json").exists())


if __name__ == "__main__":
    unittest.main()
