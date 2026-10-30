import asyncio
import re
from pathlib import Path

import edge_tts


VOICES = {
    "ar": {
        "male": "ar-JO-TaimNeural",
        "female": "ar-JO-SanaNeural",
    },
    "en": {
        "male": "en-US-GuyNeural",
        "female": "en-US-JennyNeural",
    },
}


def detect_language(text):
    return "ar" if re.search(r"[\u0600-\u06FF]", text) else "en"


async def generate_voice(
    text,
    output_path,
    language=None,
    gender="male",
    rate="+0%",
    pitch="+0Hz",
    subtitle_path=None,
):
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    language = language or detect_language(text)

    if language not in VOICES:
        raise ValueError("Supported languages: ar, en")

    if gender not in VOICES[language]:
        raise ValueError("Gender must be male or female")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(
        text.strip(),
        VOICES[language][gender],
        rate=rate,
        pitch=pitch,
    )

    if subtitle_path:
        subtitle = Path(subtitle_path)
        subtitle.parent.mkdir(parents=True, exist_ok=True)
        await communicate.save(str(output), str(subtitle))
    else:
        await communicate.save(str(output))

    return output


def create_voice(text, output_path, **options):
    return asyncio.run(generate_voice(text, output_path, **options))
