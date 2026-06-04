import json
import subprocess
from pathlib import Path


def probe_media_duration(path: Path) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    except (subprocess.CalledProcessError, ValueError, json.JSONDecodeError):
        return None


def verify_local_asset(
    path: Path,
    *,
    exists: bool = True,
    expected_duration: float | None = None,
    tolerance_sec: float = 0.5,
) -> bool:
    if exists and not path.exists():
        return False
    if expected_duration is None:
        return path.exists()
    actual = probe_media_duration(path)
    if actual is None:
        return False
    return abs(actual - expected_duration) <= tolerance_sec
