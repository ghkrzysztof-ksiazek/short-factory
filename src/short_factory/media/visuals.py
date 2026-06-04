from pathlib import Path

import httpx

from short_factory.config.logging import get_logger
from short_factory.config.settings import settings
from short_factory.shared.rate_limit import rate_limit

logger = get_logger(__name__)


@rate_limit(calls=20, period_sec=60)
def fetch_stock_video(keywords: list[str], output_path: Path) -> Path | None:
    if not settings.pexels_api_key:
        return _generate_placeholder_video(keywords, output_path)

    query = " ".join(keywords[:3]) or "relationship abstract"
    try:
        response = httpx.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": settings.pexels_api_key},
            params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 5},
            timeout=30,
        )
        response.raise_for_status()
        videos = response.json().get("videos", [])
        if not videos:
            return _generate_placeholder_video(keywords, output_path)

        best = videos[0]
        files = sorted(best.get("video_files", []), key=lambda f: f.get("width", 0), reverse=True)
        portrait = next((f for f in files if f.get("height", 0) > f.get("width", 0)), files[0] if files else None)
        if not portrait:
            return _generate_placeholder_video(keywords, output_path)

        video_url = portrait["link"]
        video_response = httpx.get(video_url, timeout=60)
        video_response.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(video_response.content)
        return output_path
    except Exception as exc:
        logger.error("pexels_fetch_failed", keywords=keywords, error=str(exc))
        return _generate_placeholder_video(keywords, output_path)


def _generate_placeholder_video(keywords: list[str], output_path: Path) -> Path:
    import subprocess

    output_path.parent.mkdir(parents=True, exist_ok=True)
    label = (keywords[0] if keywords else "scene")[:20].replace("'", "")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=0x1a1a2e:s=1080x1920:d=5",
            "-vf", f"drawtext=text='{label}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264", "-t", "5", "-pix_fmt", "yuv420p",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )
    return output_path
