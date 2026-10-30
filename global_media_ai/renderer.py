"""Render a vertical MP4 from locally supplied, rights-declared media assets.

V0.4 assembles existing narration/music and local image/video assets with FFmpeg.
It does not synthesize speech, fetch media, verify licenses, or publish to platforms.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
RIGHTS_STATUSES = {"owned", "licensed", "public_domain", "ai_generated"}


class RenderError(ValueError):
    """Raised when a render manifest or FFmpeg operation is invalid."""


def _local_path(value: str | None, base: Path, field: str, required: bool = False) -> Path | None:
    if not value:
        if required:
            raise RenderError(f"Missing required field: {field}")
        return None
    if "://" in value:
        raise RenderError(f"{field} must be a local file path, not a URL")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    if not path.is_file():
        raise RenderError(f"File not found for {field}: {path}")
    return path


def load_manifest(manifest_path: Path) -> tuple[dict[str, Any], Path]:
    manifest_path = manifest_path.expanduser().resolve()
    if not manifest_path.is_file():
        raise RenderError(f"Manifest not found: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RenderError(f"Invalid manifest JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RenderError("Manifest root must be a JSON object")
    return data, manifest_path.parent


def validate_manifest(data: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips:
        raise RenderError("Manifest must contain at least one clip")
    width = int(data.get("width", 1080))
    height = int(data.get("height", 1920))
    fps = int(data.get("fps", 30))
    if width < 360 or height < 640 or width > 2160 or height > 3840:
        raise RenderError("Output dimensions must be between 360x640 and 2160x3840")
    if fps not in {24, 25, 30, 50, 60}:
        raise RenderError("fps must be one of: 24, 25, 30, 50, 60")

    normalized_clips = []
    total = 0.0
    for index, clip in enumerate(clips, start=1):
        if not isinstance(clip, dict):
            raise RenderError(f"Clip {index} must be an object")
        path = _local_path(clip.get("path"), base_dir, f"clips[{index}].path", required=True)
        ext = path.suffix.lower()
        if ext not in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
            raise RenderError(f"Unsupported media type for clip {index}: {ext}")
        try:
            duration = float(clip.get("duration", 0))
        except (TypeError, ValueError) as exc:
            raise RenderError(f"Invalid duration for clip {index}") from exc
        if duration < 0.5 or duration > 60:
            raise RenderError(f"Clip {index} duration must be between 0.5 and 60 seconds")
        rights = str(clip.get("rights_status", "")).strip().lower()
        rights_note = str(clip.get("rights_note", "")).strip()
        if rights not in RIGHTS_STATUSES or not rights_note:
            raise RenderError(
                f"Clip {index} needs rights_status ({', '.join(sorted(RIGHTS_STATUSES))}) "
                "and a non-empty rights_note. This is your declaration, not an automated license check."
            )
        normalized_clips.append({**clip, "path_resolved": path, "duration": duration, "is_image": ext in IMAGE_EXTENSIONS})
        total += duration
    if total > 180:
        raise RenderError("Total video duration cannot exceed 180 seconds in V0.4")

    narration = _local_path(data.get("narration_path"), base_dir, "narration_path")
    music = _local_path(data.get("music_path"), base_dir, "music_path")
    subtitles = _local_path(data.get("subtitles_path"), base_dir, "subtitles_path")
    for field, path in (("narration_path", narration), ("music_path", music)):
        if path and path.suffix.lower() not in AUDIO_EXTENSIONS:
            raise RenderError(f"Unsupported audio file type for {field}: {path.suffix}")
    if subtitles and subtitles.suffix.lower() != ".srt":
        raise RenderError("subtitles_path must point to an .srt file")

    output_value = str(data.get("output_path") or "output/video.mp4")
    if "://" in output_value:
        raise RenderError("output_path must be a local file path")
    output = Path(output_value).expanduser()
    if not output.is_absolute():
        output = base_dir / output
    output = output.resolve()
    if output.suffix.lower() != ".mp4":
        raise RenderError("output_path must end in .mp4")

    return {
        "title": str(data.get("title") or "GLOBAL MEDIA AI video"),
        "width": width,
        "height": height,
        "fps": fps,
        "clips": normalized_clips,
        "duration": round(total, 3),
        "narration": narration,
        "music": music,
        "subtitles": subtitles,
        "burn_subtitles": bool(data.get("burn_subtitles", False)),
        "output": output,
    }


def _escape_filter_path(path: Path) -> str:
    # Escape characters meaningful to FFmpeg filtergraph option parsing.
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace(",", "\\,")


def build_ffmpeg_command(config: dict[str, Any], ffmpeg: str = "ffmpeg") -> list[str]:
    args = [ffmpeg, "-hide_banner", "-y"]
    filters: list[str] = []
    video_labels: list[str] = []
    fps = config["fps"]
    width, height = config["width"], config["height"]

    for i, clip in enumerate(config["clips"]):
        path: Path = clip["path_resolved"]
        duration = clip["duration"]
        if clip["is_image"]:
            args += ["-loop", "1", "-framerate", str(fps), "-t", f"{duration:.3f}", "-i", str(path)]
        else:
            args += ["-stream_loop", "-1", "-i", str(path)]
        label = f"v{i}"
        filters.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,fps={fps},trim=duration={duration:.3f},"
            f"setpts=PTS-STARTPTS,format=yuv420p[{label}]"
        )
        video_labels.append(f"[{label}]")

    filters.append("".join(video_labels) + f"concat=n={len(video_labels)}:v=1:a=0[vbase]")
    audio_input_index = len(config["clips"])
    narration_index = music_index = None
    if config["narration"]:
        args += ["-i", str(config["narration"])]
        narration_index = audio_input_index
        audio_input_index += 1
    if config["music"]:
        args += ["-stream_loop", "-1", "-i", str(config["music"])]
        music_index = audio_input_index
        audio_input_index += 1

    video_map = "[vbase]"
    if config["subtitles"] and config["burn_subtitles"]:
        filters.append(f"[vbase]subtitles='{_escape_filter_path(config['subtitles'])}'[vout]")
        video_map = "[vout]"

    audio_map = None
    if narration_index is not None and music_index is not None:
        filters.append(f"[{narration_index}:a]aresample=44100,volume=1.0[voice]")
        filters.append(f"[{music_index}:a]aresample=44100,volume=0.12,atrim=duration={config['duration']:.3f}[bgm]")
        filters.append("[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]")
        audio_map = "[aout]"
    elif narration_index is not None:
        filters.append(f"[{narration_index}:a]aresample=44100,volume=1.0[aout]")
        audio_map = "[aout]"
    elif music_index is not None:
        filters.append(f"[{music_index}:a]aresample=44100,volume=0.7,atrim=duration={config['duration']:.3f}[aout]")
        audio_map = "[aout]"

    args += ["-filter_complex", ";".join(filters), "-map", video_map]
    if audio_map:
        args += ["-map", audio_map, "-c:a", "aac", "-b:a", "192k"]
    args += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-r", str(fps), "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-t", f"{config['duration']:.3f}", str(config["output"]),
    ]
    return args


def render_video(manifest_path: Path, ffmpeg: str = "ffmpeg") -> Path:
    data, base_dir = load_manifest(manifest_path)
    config = validate_manifest(data, base_dir)
    executable = shutil.which(ffmpeg)
    if not executable:
        raise RenderError("FFmpeg was not found. Install it first (Termux: pkg install ffmpeg).")
    if config["burn_subtitles"] and config["subtitles"] is None:
        raise RenderError("burn_subtitles=true requires subtitles_path")
    config["output"].parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_command(config, executable)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "Unknown FFmpeg error")[-2500:]
        raise RenderError(f"FFmpeg render failed:\n{details}")

    report = {
        "renderer_version": "0.4.0",
        "title": config["title"],
        "output": str(config["output"]),
        "duration_seconds": config["duration"],
        "resolution": f"{config['width']}x{config['height']}",
        "fps": config["fps"],
        "clips": [
            {"path": str(c["path_resolved"]), "duration": c["duration"],
             "rights_status_declared_by_user": c["rights_status"], "rights_note": c["rights_note"]}
            for c in config["clips"]
        ],
        "narration_used": bool(config["narration"]),
        "music_used": bool(config["music"]),
        "subtitle_file": str(config["subtitles"]) if config["subtitles"] else None,
        "subtitles_burned_in": bool(config["subtitles"] and config["burn_subtitles"]),
        "limitations": [
            "Asset rights declarations are supplied by the user and are not independently verified.",
            "Narration must already exist as a local audio file; V0.4 does not synthesize speech.",
            "The output is not uploaded or published automatically.",
        ],
    }
    report_path = config["output"].with_suffix(".render_report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return config["output"]
