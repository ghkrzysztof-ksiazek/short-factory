import json
import subprocess
from pathlib import Path

from short_factory.config.logging import get_logger
from short_factory.config.settings import settings
from short_factory.db.models import Asset, AssetType, QAStatus, ScenePlan, Video
from short_factory.db.session import SessionLocal
from short_factory.media.subtitles import validate_subtitle_timing
from short_factory.shared.storage import storage

logger = get_logger(__name__)


def render_video(scene_plan_id: int) -> int:
    db = SessionLocal()
    work_dir = Path(settings.render_dir) / f"render_{scene_plan_id}"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        scene_plan = db.get(ScenePlan, scene_plan_id)
        if not scene_plan:
            raise ValueError(f"ScenePlan {scene_plan_id} not found")

        assets = db.query(Asset).filter(Asset.scene_plan_id == scene_plan_id).all()
        visual_assets = sorted(
            [a for a in assets if a.asset_type == AssetType.VISUAL],
            key=lambda a: a.scene_index or 0,
        )
        subtitle_asset = next((a for a in assets if a.asset_type == AssetType.SUBTITLE and a.s3_key.endswith(".ass")), None)
        master_audio = next((a for a in assets if a.asset_type == AssetType.VOICE and "master" in a.s3_key), None)

        if not visual_assets:
            raise ValueError("No visual assets found")

        scene_clips: list[Path] = []
        for i, asset in enumerate(visual_assets):
            local_visual = work_dir / f"scene_{i}_visual.mp4"
            storage.download_file(asset.s3_key, local_visual)
            scene = scene_plan.scenes[i] if i < len(scene_plan.scenes) else {}
            duration = scene.get("duration_sec", 5)
            clip_path = work_dir / f"scene_{i}_clip.mp4"
            _trim_to_duration(local_visual, clip_path, duration)
            scene_clips.append(clip_path)

        concat_list = work_dir / "concat.txt"
        with concat_list.open("w") as f:
            for clip in scene_clips:
                f.write(f"file '{clip.resolve()}'\n")

        concatenated = work_dir / "concatenated.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(concatenated)],
            check=True,
            capture_output=True,
        )

        output_path = work_dir / "final.mp4"
        cmd = ["ffmpeg", "-y", "-i", str(concatenated)]

        if master_audio:
            local_audio = work_dir / "master_audio.mp3"
            storage.download_file(master_audio.s3_key, local_audio)
            cmd.extend(["-i", str(local_audio)])

        if subtitle_asset:
            local_subs = work_dir / "subtitles.ass"
            storage.download_file(subtitle_asset.s3_key, local_subs)
            cmd.extend(["-vf", f"ass={local_subs}"])

        cmd.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(output_path)])
        subprocess.run(cmd, check=True, capture_output=True)

        duration = _probe_duration(output_path)
        s3_key = f"videos/{scene_plan.script_id}/final.mp4"
        storage.upload_file(output_path, s3_key)

        qa_status, qa_details = run_qa_checks(output_path, duration, subtitle_asset)

        video = Video(
            script_id=scene_plan.script_id,
            s3_key=s3_key,
            duration_sec=duration,
            qa_status=qa_status,
            qa_details=qa_details,
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        return video.id
    finally:
        db.close()


def _trim_to_duration(input_path: Path, output_path: Path, duration: float) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(input_path),
            "-t", str(duration),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    return float(data.get("format", {}).get("duration", 0))


def run_qa_checks(
    video_path: Path, duration: float, subtitle_asset: Asset | None = None
) -> tuple[QAStatus, dict]:
    issues: list[str] = []

    if duration < 30:
        issues.append("too_short")
    if duration > 45:
        issues.append("too_long")

    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-select_streams", "v:0", str(video_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if streams:
            width = streams[0].get("width", 0)
            height = streams[0].get("height", 0)
            if height <= width:
                issues.append("not_vertical")

    black_result = subprocess.run(
        [
            "ffmpeg", "-i", str(video_path), "-vf", "blackdetect=d=0.1:pix_th=0.10", "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
    )
    if "black_start" in black_result.stderr:
        issues.append("black_frames_detected")

    audio_result = subprocess.run(
        [
            "ffmpeg", "-i", str(video_path), "-af", "volumedetect", "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
    )
    if "mean_volume" in audio_result.stderr:
        for line in audio_result.stderr.split("\n"):
            if "mean_volume" in line:
                try:
                    mean_db = float(line.split("mean_volume:")[1].split(" dB")[0].strip())
                    if mean_db < -40:
                        issues.append("audio_too_quiet")
                except (IndexError, ValueError):
                    pass

    if subtitle_asset and subtitle_asset.timing_metadata:
        segments = subtitle_asset.timing_metadata.get("segments", [])
        subtitle_issues = validate_subtitle_timing(segments)
        issues.extend(subtitle_issues)

    details = {"duration_sec": duration, "issues": issues}
    status = QAStatus.PASSED if not issues else QAStatus.FAILED
    return status, details
