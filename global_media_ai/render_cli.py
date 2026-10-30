"""Command line interface for the V0.4 FFmpeg renderer."""
import argparse
from pathlib import Path
from .renderer import RenderError, render_video


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a vertical MP4 from a local media manifest")
    parser.add_argument("--manifest", default="render_manifest.json", help="Path to render manifest JSON")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable name or path")
    args = parser.parse_args()
    try:
        output = render_video(Path(args.manifest), args.ffmpeg)
    except RenderError as exc:
        parser.exit(2, f"Render blocked: {exc}\n")
    print(f"Rendered MP4: {output}")
    print(f"Render report: {output.with_suffix('.render_report.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
