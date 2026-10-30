import argparse
import json
import tempfile
from pathlib import Path

from .voice_engine import create_voice
from .renderer import render_video, RenderError


def main():
    parser = argparse.ArgumentParser(
        description="GLOBAL MEDIA AI V0.6 production pipeline"
    )
    parser.add_argument("--text", required=True, help="Final approved script TXT")
    parser.add_argument("--manifest", required=True, help="Render manifest JSON")
    parser.add_argument("--output-dir", default="output/pipeline")
    parser.add_argument("--language", choices=["auto", "ar", "en"], default="auto")
    parser.add_argument("--gender", choices=["male", "female"], default="male")
    parser.add_argument("--rate", default="+0%")
    parser.add_argument("--pitch", default="+0Hz")
    parser.add_argument("--burn-subtitles", action="store_true")
    args = parser.parse_args()

    text_path = Path(args.text).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    if not text_path.is_file():
        parser.error(f"Text file not found: {text_path}")

    if not manifest_path.is_file():
        parser.error(f"Manifest not found: {manifest_path}")

    script = text_path.read_text(encoding="utf-8").strip()
    if not script:
        parser.error("Approved script is empty")

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        parser.error(f"Invalid manifest JSON: {exc}")

    if not isinstance(data, dict):
        parser.error("Manifest root must be a JSON object")

    output_dir.mkdir(parents=True, exist_ok=True)

    audio_path = output_dir / "narration.mp3"
    subtitle_path = output_dir / "captions.srt"

    language = None if args.language == "auto" else args.language

    try:
        audio = create_voice(
            script,
            audio_path,
            language=language,
            gender=args.gender,
            rate=args.rate,
            pitch=args.pitch,
            subtitle_path=subtitle_path,
        )

        data["narration_path"] = str(audio.resolve())
        data["subtitles_path"] = str(subtitle_path.resolve())

        if args.burn_subtitles:
            data["burn_subtitles"] = True

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            prefix=".pipeline-",
            dir=manifest_path.parent,
            delete=False,
        ) as temporary:
            json.dump(data, temporary, ensure_ascii=False, indent=2)
            temporary_manifest = Path(temporary.name)

        try:
            video = render_video(temporary_manifest)
            import shutil
            gallery_dir = Path("/storage/emulated/0/DCIM/Camera")
            gallery_dir.mkdir(parents=True, exist_ok=True)
            gallery_video = gallery_dir / video.name
            shutil.copy2(video, gallery_video)
        finally:
            temporary_manifest.unlink(missing_ok=True)

        print("PIPELINE: SUCCESS")
        print(f"Audio: {audio}")
        print(f"Subtitles: {subtitle_path}")
        print(f"Video: {video}")
        print(f"Report: {video.with_suffix('.render_report.json')}")

    except (RenderError, OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"PIPELINE BLOCKED: {exc}\n")


if __name__ == "__main__":
    main()
