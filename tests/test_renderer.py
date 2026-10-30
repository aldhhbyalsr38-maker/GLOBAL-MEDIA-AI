import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from global_media_ai.renderer import (
    RenderError, build_ffmpeg_command, load_manifest, render_video, validate_manifest,
)


class RendererTests(unittest.TestCase):
    def make_manifest(self, root: Path):
        (root / "scene.jpg").write_bytes(b"placeholder image")
        (root / "voice.mp3").write_bytes(b"placeholder audio")
        data = {
            "title": "Test vertical video",
            "clips": [{
                "path": "scene.jpg", "duration": 4,
                "rights_status": "owned", "rights_note": "Original test asset created by the project owner",
            }],
            "narration_path": "voice.mp3",
            "output_path": "out/test.mp4",
        }
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps(data), encoding="utf-8")
        return manifest, data

    def test_manifest_requires_rights_declaration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scene.jpg").write_bytes(b"x")
            with self.assertRaisesRegex(RenderError, "rights_status"):
                validate_manifest({"clips": [{"path": "scene.jpg", "duration": 3}]}, root)

    def test_manifest_rejects_remote_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RenderError, "local file path"):
                validate_manifest({"clips": [{"path": "https://example.com/a.jpg", "duration": 3,
                    "rights_status": "licensed", "rights_note": "licensed"}]}, Path(tmp))

    def test_manifest_rejects_too_long_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scene.jpg").write_bytes(b"x")
            clips = [{"path": "scene.jpg", "duration": 60, "rights_status": "owned", "rights_note": "mine"} for _ in range(4)]
            with self.assertRaisesRegex(RenderError, "180 seconds"):
                validate_manifest({"clips": clips}, root)

    def test_command_contains_vertical_h264_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, data = self.make_manifest(root)
            raw, base = load_manifest(manifest)
            config = validate_manifest(raw, base)
            command = build_ffmpeg_command(config)
            joined = " ".join(command)
            self.assertIn("scale=1080:1920", joined)
            self.assertIn("libx264", joined)
            self.assertIn("-movflags +faststart", joined)

    @patch("global_media_ai.renderer.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("global_media_ai.renderer.subprocess.run")
    def test_render_writes_report_after_success(self, run_mock, _which):
        run_mock.return_value = Mock(returncode=0, stderr="", stdout="")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, _ = self.make_manifest(root)
            output = render_video(manifest)
            self.assertEqual(output, root / "out" / "test.mp4")
            report = output.with_suffix(".render_report.json")
            self.assertTrue(report.exists())
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["renderer_version"], "0.4.0")
            self.assertTrue(payload["narration_used"])

    @patch("global_media_ai.renderer.shutil.which", return_value=None)
    def test_missing_ffmpeg_is_reported(self, _which):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, _ = self.make_manifest(root)
            with self.assertRaisesRegex(RenderError, "FFmpeg was not found"):
                render_video(manifest)


if __name__ == "__main__":
    unittest.main()
