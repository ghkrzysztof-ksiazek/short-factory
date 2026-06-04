from pathlib import Path

from short_factory.config.logging import get_logger
from short_factory.config.settings import settings
from short_factory.db.models import Asset, AssetType, ScenePlan, Script
from short_factory.db.session import SessionLocal
from short_factory.media.scene_planner import SCENE_PLANNER_PROMPT, SCENE_PLANNER_SYSTEM
from short_factory.media.subtitles import generate_ass, generate_srt, resolve_subtitle_style
from short_factory.media.tts import generate_speech, merge_audio_files
from short_factory.media.visuals import fetch_stock_video
from short_factory.shared.asset_verification import verify_local_asset
from short_factory.shared.llm import get_llm_client, parse_json_response
from short_factory.shared.storage import storage

logger = get_logger(__name__)


def plan_scenes(script_id: int) -> int:
    db = SessionLocal()
    try:
        script = db.get(Script, script_id)
        if not script:
            raise ValueError(f"Script {script_id} not found")

        llm = get_llm_client()
        prompt = SCENE_PLANNER_PROMPT.format(
            hook=script.hook,
            body=script.body,
            ending=script.ending,
            cta=script.cta,
        )
        try:
            result = llm.complete(prompt, system=SCENE_PLANNER_SYSTEM, json_mode=True)
            data = parse_json_response(result)
        except Exception as exc:
            logger.warning("scene_plan_llm_failed", error=str(exc))
            data = _fallback_scene_plan(script)

        scene_plan = ScenePlan(
            script_id=script_id,
            scenes=data["scenes"],
            total_duration_sec=data.get("total_duration_sec", 40),
        )
        db.add(scene_plan)
        db.commit()
        db.refresh(scene_plan)
        return scene_plan.id
    finally:
        db.close()


def _fallback_scene_plan(script: Script) -> dict:
    parts = [
        script.hook,
        script.body[: len(script.body) // 2] if script.body else "",
        script.body[len(script.body) // 2 :] if script.body else "",
        script.ending,
        script.cta,
    ]
    scenes = []
    for i, text in enumerate(parts):
        if not text.strip():
            continue
        scenes.append(
            {
                "text": text.strip(),
                "emotion": "curiosity",
                "duration_sec": 8.0,
                "visual_keywords": ["relationship", "abstract", "emotion"],
                "pause_ms": 300,
            }
        )
    return {"scenes": scenes, "total_duration_sec": len(scenes) * 8}


def generate_media_assets(scene_plan_id: int) -> dict:
    db = SessionLocal()
    work_dir = Path(settings.render_dir) / f"scene_plan_{scene_plan_id}"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        scene_plan = db.get(ScenePlan, scene_plan_id)
        if not scene_plan:
            raise ValueError(f"ScenePlan {scene_plan_id} not found")

        scenes = scene_plan.scenes
        audio_paths: list[Path] = []
        all_timing: list[dict] = []
        offset = 0.0

        for i, scene in enumerate(scenes):
            text = scene.get("text", "")
            audio_path = work_dir / f"scene_{i}_audio.mp3"
            audio_path, duration, timing = generate_speech(text, audio_path)

            for t in timing:
                t["start"] += offset
                t["end"] += offset
            all_timing.extend(timing)
            offset += duration + scene.get("pause_ms", 0) / 1000

            s3_key = f"audio/{scene_plan_id}/scene_{i}{audio_path.suffix}"
            storage.upload_file(audio_path, s3_key)
            voice_verified = verify_local_asset(
                audio_path, expected_duration=duration, tolerance_sec=0.5
            )
            asset = Asset(
                scene_plan_id=scene_plan_id,
                asset_type=AssetType.VOICE,
                s3_key=s3_key,
                scene_index=i,
                duration_sec=duration,
                timing_metadata={"segments": timing},
                verified=voice_verified and storage.exists(s3_key),
            )
            db.add(asset)
            audio_paths.append(audio_path)

            visual_path = work_dir / f"scene_{i}_visual.mp4"
            keywords = scene.get("visual_keywords", ["abstract"])
            fetch_stock_video(keywords, visual_path)
            visual_key = f"visuals/{scene_plan_id}/scene_{i}.mp4"
            storage.upload_file(visual_path, visual_key)
            expected_visual_duration = scene.get("duration_sec", 5)
            visual_verified = verify_local_asset(
                visual_path, expected_duration=expected_visual_duration, tolerance_sec=1.0
            )
            db.add(
                Asset(
                    scene_plan_id=scene_plan_id,
                    asset_type=AssetType.VISUAL,
                    s3_key=visual_key,
                    scene_index=i,
                    duration_sec=expected_visual_duration,
                    verified=visual_verified and storage.exists(visual_key),
                )
            )

        master_audio = work_dir / "master_audio.mp3"
        merge_audio_files(audio_paths, master_audio)
        master_key = f"audio/{scene_plan_id}/master{master_audio.suffix}"
        storage.upload_file(master_audio, master_key)
        master_duration = offset
        master_verified = verify_local_asset(
            master_audio, expected_duration=master_duration, tolerance_sec=1.0
        )
        db.add(
            Asset(
                scene_plan_id=scene_plan_id,
                asset_type=AssetType.VOICE,
                s3_key=master_key,
                duration_sec=master_duration,
                timing_metadata={"segments": all_timing},
                verified=master_verified and storage.exists(master_key),
            )
        )

        subtitle_style = resolve_subtitle_style(channel_id=None)

        srt_path = work_dir / "subtitles.srt"
        ass_path = work_dir / "subtitles.ass"
        generate_srt(all_timing, srt_path)
        generate_ass(all_timing, ass_path, style=subtitle_style)

        for sub_path, ext in [(srt_path, "srt"), (ass_path, "ass")]:
            sub_key = f"subtitles/{scene_plan_id}/subtitles.{ext}"
            storage.upload_file(sub_path, sub_key)
            db.add(
                Asset(
                    scene_plan_id=scene_plan_id,
                    asset_type=AssetType.SUBTITLE,
                    s3_key=sub_key,
                    timing_metadata={"segments": all_timing},
                    verified=storage.exists(sub_key),
                )
            )

        db.commit()
        return {"scene_plan_id": scene_plan_id, "scenes": len(scenes), "master_audio_key": master_key}
    finally:
        db.close()


def process_approved_script(script_id: int) -> dict:
    scene_plan_id = plan_scenes(script_id)
    media_result = generate_media_assets(scene_plan_id)
    return {"scene_plan_id": scene_plan_id, **media_result}
