import unittest
from datetime import datetime, timezone, timedelta
from global_media_ai.research import clean_text, classify_topic, score_story, make_bilingual_brief, write_outputs
from pathlib import Path
import tempfile

class ResearchTests(unittest.TestCase):
    def test_clean_text(self):
        self.assertEqual(clean_text("<b>Hello</b> &amp; world"), "Hello & world")

    def test_classify(self):
        self.assertIn("technology", classify_topic("A new AI technology", {"technology": ["AI", "technology"]}))

    def test_score_prefers_recent(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        base = {"title": "New science discovery", "summary": "", "source": "Test",
                "source_weight": 1.0, "url": "https://example.com/a"}
        recent = dict(base, published_at=(now - timedelta(hours=1)).isoformat())
        old = dict(base, published_at=(now - timedelta(hours=40)).isoformat())
        self.assertGreater(score_story(recent, now, 48, {})["score"],
                           score_story(old, now, 48, {})["score"])

    def test_brief_has_two_languages_and_sources(self):
        story = {"title":"Test story", "summary":"Summary", "source":"Test",
                 "url":"https://example.com", "published_at":"2026-01-01T00:00:00+00:00",
                 "score":70, "categories":["general"]}
        brief = make_bilingual_brief(story, 1)
        self.assertIn("english", brief)
        self.assertIn("arabic", brief)
        self.assertEqual(brief["source_url"], story["url"])

    def test_writes_reports(self):
        with tempfile.TemporaryDirectory() as d:
            jp, mp = write_outputs({"project":"Test","generated_at":"now","status":"ok",
                                    "topics_found":0,"topics":[],"feed_errors":[]}, Path(d))
            self.assertTrue(jp.exists())
            self.assertTrue(mp.exists())

if __name__ == "__main__":
    unittest.main()
