from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from short_factory.api.schemas import (
    AnalyticsSummary,
    JobResponse,
    PublicationResponse,
    ScriptResponse,
    TopicResponse,
    VideoResponse,
)
from short_factory.db.models import Job, Publication, Script, Topic, Video
from short_factory.db.session import get_db
from short_factory.shared.jobs import create_job
from short_factory.shared.storage import storage
from short_factory.workers import tasks

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/ping/run", response_model=JobResponse)
def trigger_ping(db: Session = Depends(get_db)):
    job = create_job("ping")
    tasks.ping.delay(job_id=job.id)
    return db.get(Job, job.id)


@router.post("/jobs/research/run", response_model=JobResponse)
def trigger_research(db: Session = Depends(get_db)):
    job = create_job("research.run")
    tasks.run_research.delay(job_id=job.id)
    return db.get(Job, job.id)


@router.post("/jobs/scripts/run", response_model=JobResponse)
def trigger_script_generation(
    topic_id: int | None = None,
    db: Session = Depends(get_db),
):
    job = create_job("scripts.generate", payload={"topic_id": topic_id})
    tasks.run_script_generation.delay(job_id=job.id, topic_id=topic_id)
    return db.get(Job, job.id)


@router.post("/jobs/pipeline/run", response_model=JobResponse)
def trigger_full_pipeline(db: Session = Depends(get_db)):
    job = create_job("pipeline.full")
    tasks.run_full_pipeline.delay(job_id=job.id)
    return db.get(Job, job.id)


@router.get("/topics", response_model=list[TopicResponse])
def list_topics(
    min_virality: float | None = Query(None),
    category: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Topic)
    if min_virality is not None:
        query = query.filter(Topic.virality_score >= min_virality)
    if category:
        query = query.filter(Topic.category == category)
    return query.order_by(Topic.virality_score.desc()).limit(limit).all()


@router.get("/topics/{topic_id}", response_model=TopicResponse)
def get_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@router.post("/scripts/generate", response_model=JobResponse)
def generate_script(topic_id: int, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    job = create_job("scripts.generate", payload={"topic_id": topic_id})
    tasks.run_script_generation.delay(job_id=job.id, topic_id=topic_id)
    return db.get(Job, job.id)


@router.get("/scripts", response_model=list[ScriptResponse])
def list_scripts(
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Script)
    if status:
        query = query.filter(Script.status == status)
    return query.order_by(Script.created_at.desc()).limit(limit).all()


@router.post("/scripts/{script_id}/media", response_model=JobResponse)
def generate_media(script_id: int, db: Session = Depends(get_db)):
    script = db.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    job = create_job("media.process", payload={"script_id": script_id})
    tasks.run_media_pipeline.delay(script_id=script_id, job_id=job.id)
    return db.get(Job, job.id)


@router.post("/scene-plans/{scene_plan_id}/render", response_model=JobResponse)
def render_scene_plan(scene_plan_id: int, db: Session = Depends(get_db)):
    job = create_job("render.video", payload={"scene_plan_id": scene_plan_id})
    tasks.run_render.delay(scene_plan_id=scene_plan_id, job_id=job.id)
    return db.get(Job, job.id)


@router.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    response = VideoResponse.model_validate(video)
    if video.s3_key:
        response.preview_url = storage.get_presigned_url(video.s3_key)
    return response


@router.post("/videos/{video_id}/publish", response_model=JobResponse)
def publish_video_endpoint(
    video_id: int,
    platform: str = Query("youtube"),
    scheduled_at: datetime | None = Query(None),
    db: Session = Depends(get_db),
):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    parsed_scheduled = scheduled_at

    if parsed_scheduled:
        from short_factory.db.models import Platform
        from short_factory.publish.publishers import publish_video

        publication_id = publish_video(video_id, Platform(platform), scheduled_at=parsed_scheduled)
        job = create_job(
            "publish.scheduled",
            payload={"video_id": video_id, "publication_id": publication_id},
        )
        return db.get(Job, job.id)

    job = create_job("publish.video", payload={"video_id": video_id, "platform": platform})
    tasks.run_publish.delay(video_id=video_id, platform=platform, job_id=job.id)
    return db.get(Job, job.id)


@router.get("/publications", response_model=list[PublicationResponse])
def list_publications(db: Session = Depends(get_db)):
    return db.query(Publication).order_by(Publication.created_at.desc()).limit(100).all()


@router.post("/publications/{publication_id}/analytics", response_model=JobResponse)
def collect_analytics(publication_id: int, db: Session = Depends(get_db)):
    pub = db.get(Publication, publication_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    job = create_job("analytics.collect", payload={"publication_id": publication_id})
    tasks.run_analytics_collection.delay(publication_id=publication_id, job_id=job.id)
    return db.get(Job, job.id)


@router.get("/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary():
    from short_factory.analytics.collector import get_performance_summary

    return get_performance_summary()


@router.post("/analytics/optimize", response_model=JobResponse)
def trigger_optimization(db: Session = Depends(get_db)):
    job = create_job("analytics.optimize")
    tasks.run_optimization.delay(job_id=job.id)
    return db.get(Job, job.id)
