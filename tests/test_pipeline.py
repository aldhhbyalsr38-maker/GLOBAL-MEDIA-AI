import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from global_media_ai import pipeline_cli


class PipelineTests(unittest.TestCase):

    def test_pipeline_generates_voice_and_calls_renderer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "approved.txt"
            manifest = root / "manifest.json"
            output_dir = root / "pipeline-output"

            script.write_text("This is the approved test script.", encoding="utf-8")

            original_manifest = {
                "title": "Integration test",
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "clips": [
                    {
                        "path": "assets/scene.jpg",
                        "duration": 5,
                        "rights_status": "owned",
                        "rights_note": "Original test asset"
                    }
                ],
                "output_path": "output/test.mp4"
            }

            manifest.write_text(
                json.dumps(original_manifest),
                encoding="utf-8"
            )

            def fake_voice(text, output_path, **options):
                output_path.write_bytes(b"fake audio")
                options["subtitle_path"].write_text(
                    "1\n00:00:00,000 --> 00:00:02,000\nTest\n",
                    encoding="utf-8"
                )
                return output_path

            def fake_renderer(temporary_manifest):
                temporary_manifest = Path(temporary_manifest)
                self.assertEqual(temporary_manifest.parent, manifest.parent)

                data = json.loads(
                    temporary_manifest.read_text(encoding="utf-8")
                )

                self.assertTrue(Path(data["narration_path"]).is_file())
                self.assertTrue(Path(data["subtitles_path"]).is_file())
                self.assertTrue(data["burn_subtitles"])

                rendered = root / "rendered.mp4"
                rendered.write_bytes(b"fake video")
                return rendered

            arguments = [
                "pipeline_cli",
                "--text", str(script),
                "--manifest", str(manifest),
                "--output-dir", str(output_dir),
                "--burn-subtitles"
            ]

            with patch.object(sys, "argv", arguments):
                with patch.object(
                    pipeline_cli, "create_voice", side_effect=fake_voice
                ) as voice_mock:
                    with patch.object(
                        pipeline_cli, "render_video",
                        side_effect=fake_renderer
                    ) as render_mock:
                        pipeline_cli.main()

            voice_mock.assert_called_once()
            render_mock.assert_called_once()

            self.assertEqual(
                json.loads(manifest.read_text(encoding="utf-8")),
                original_manifest
            )

    def test_empty_script_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "empty.txt"
            manifest = root / "manifest.json"

            script.write_text("   ", encoding="utf-8")
            manifest.write_text("{}", encoding="utf-8")

            arguments = [
                "pipeline_cli",
                "--text", str(script),
                "--manifest", str(manifest)
            ]

            with patch.object(sys, "argv", arguments):
                with patch.object(pipeline_cli, "create_voice") as voice_mock:
                    with self.assertRaises(SystemExit):
                        pipeline_cli.main()

            voice_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
