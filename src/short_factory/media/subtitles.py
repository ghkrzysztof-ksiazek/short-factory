from pathlib import Path

from short_factory.config.settings import settings
from short_factory.db.models import Channel
from short_factory.db.session import SessionLocal


def resolve_subtitle_style(channel_id: int | None = None) -> dict:
    style = dict(settings.default_subtitle_style)
    if channel_id is None:
        return style

    db = SessionLocal()
    try:
        channel = db.get(Channel, channel_id)
        if channel and channel.style_config:
            style.update(channel.style_config)
        return style
    finally:
        db.close()


def generate_srt(timing_segments: list[dict], output_path: Path) -> Path:
    """Generate SRT from word/segment timing metadata."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    idx = 1

    chunk_size = 6
    words = timing_segments
    for i in range(0, len(words), chunk_size):
        chunk = words[i : i + chunk_size]
        if not chunk:
            continue
        start = chunk[0]["start"]
        end = chunk[-1]["end"]
        text = " ".join(w["word"] for w in chunk)
        lines.append(str(idx))
        lines.append(f"{_format_time(start)} --> {_format_time(end)}")
        lines.append(text)
        lines.append("")
        idx += 1

    output_path.write_text("\n".join(lines))
    return output_path


def generate_ass(timing_segments: list[dict], output_path: Path, style: dict | None = None) -> Path:
    """Generate ASS subtitles styled for vertical video."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    style = style or resolve_subtitle_style()
    fontname = style.get("fontname", "Arial")
    fontsize = style.get("fontsize", 52)
    primary = style.get("primary_colour", "&H00FFFFFF")
    margin_v = style.get("margin_v", 120)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{fontname},{fontsize},{primary},&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: list[str] = []
    chunk_size = 6
    for i in range(0, len(timing_segments), chunk_size):
        chunk = timing_segments[i : i + chunk_size]
        if not chunk:
            continue
        start = _format_ass_time(chunk[0]["start"])
        end = _format_ass_time(chunk[-1]["end"])
        text = " ".join(w["word"] for w in chunk)
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    output_path.write_text(header + "\n".join(events))
    return output_path


def validate_subtitle_timing(timing_segments: list[dict]) -> list[str]:
    issues: list[str] = []
    if not timing_segments:
        issues.append("no_subtitle_segments")
        return issues

    for i, seg in enumerate(timing_segments):
        duration = seg["end"] - seg["start"]
        if duration <= 0:
            issues.append(f"overlap_at_segment_{i}")
        if duration < 0.08:
            issues.append(f"unreadable_speed_at_segment_{i}")

    return issues


def _format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"
