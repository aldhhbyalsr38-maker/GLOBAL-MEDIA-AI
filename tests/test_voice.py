import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from global_media_ai.voice_engine import (
    VOICES,
    detect_language,
    generate_voice,
)


class VoiceEngineTests(unittest.TestCase):

    def test_detects_arabic(self):
        self.assertEqual(detect_language("مرحبا بالعالم"), "ar")

    def test_detects_english(self):
        self.assertEqual(detect_language("Hello world"), "en")

    def test_rejects_empty_text(self):
        with self.assertRaisesRegex(ValueError, "Text cannot be empty"):
            import asyncio
            asyncio.run(generate_voice(" ", "output/test.mp3"))

    def test_rejects_unsupported_language(self):
        import asyncio
        with self.assertRaisesRegex(ValueError, "Supported languages"):
            asyncio.run(generate_voice("Hello", "output/test.mp3", language="fr"))

    def test_rejects_invalid_gender(self):
        import asyncio
        with self.assertRaisesRegex(ValueError, "Gender"):
            asyncio.run(generate_voice("Hello", "output/test.mp3", gender="unknown"))

    def test_generates_audio_and_subtitles_without_network(self):
        import asyncio

        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "audio" / "voice.mp3"
            subtitles = Path(tmp) / "subtitles" / "voice.srt"

            mock_communicate = type("MockCommunicate", (), {})()
            mock_communicate.save = AsyncMock()

            with patch(
                "global_media_ai.voice_engine.edge_tts.Communicate",
                return_value=mock_communicate,
            ) as communicate:
                result = asyncio.run(
                    generate_voice(
                        "Hello world",
                        audio,
                        language="en",
                        gender="male",
                        subtitle_path=subtitles,
                    )
                )

            self.assertEqual(result, audio)
            communicate.assert_called_once_with(
                "Hello world",
                VOICES["en"]["male"],
                rate="+0%",
                pitch="+0Hz",
            )
            mock_communicate.save.assert_awaited_once_with(
                str(audio), str(subtitles)
            )


if __name__ == "__main__":
    unittest.main()
