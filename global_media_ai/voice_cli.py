import argparse
from pathlib import Path

from .voice_engine import create_voice


def main():
    parser = argparse.ArgumentParser(
        description="Generate bilingual AI voice and synchronized subtitles"
    )
    parser.add_argument("--input", required=True, help="Input TXT file")
    parser.add_argument("--output", required=True, help="Output MP3 file")
    parser.add_argument("--language", choices=["auto", "ar", "en"], default="auto")
    parser.add_argument("--gender", choices=["male", "female"], default="male")
    parser.add_argument("--rate", default="+0%")
    parser.add_argument("--pitch", default="+0Hz")
    parser.add_argument("--subtitles", default=None, help="Optional SRT output path")
    args = parser.parse_args()

    source = Path(args.input)
    if not source.is_file():
        parser.error(f"Input file not found: {source}")

    text = source.read_text(encoding="utf-8").strip()
    if not text:
        parser.error("Input text file is empty")

    language = None if args.language == "auto" else args.language

    audio = create_voice(
        text,
        args.output,
        language=language,
        gender=args.gender,
        rate=args.rate,
        pitch=args.pitch,
        subtitle_path=args.subtitles,
    )

    print(f"Audio created: {audio}")
    if args.subtitles:
        print(f"Subtitles created: {args.subtitles}")


if __name__ == "__main__":
    main()
