from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from short_factory.api.schemas import (
    AnalyticsSummary,
    AssetResponse,
    CategoryPerformance,
    JobListResponse,
    JobResponse,
    PublicationDetailResponse,
    PublicationResponse,
    RankedItem,
    ScenePlanDetailResponse,
    ScenePlanResponse,
    ScriptDetailResponse,
    ScriptResponse,
    ScriptReviewRequest,
    TopicResponse,
    TopicSummary,
    VideoResponse,
    VideoSummary,
)
from short_factory.db.models import Asset, Job, Platform, Publication, ScenePlan, Script, ScriptStatus, Topic, Video
from short_factory.db.session import get_db
from short_factory.shared.jobs import create_job
from short_factory.workers import tasks

router = APIRouter()


def _platform_url(platform: str, external_id: str | None) -> str | None:
    if not external_id or external_id.startswith(("stub_", "dry_run_")):
        return None
    if platform == Platform.YOUTUBE.value:
        return f"https://youtube.com/watch?v={external_id}"
    return None


def _asset_response(asset: Asset) -> AssetResponse:
    return AssetResponse(
        id=asset.id,
        asset_type=asset.asset_type.value,
        scene_index=asset.scene_index,
        s3_key=asset.s3_key,
        duration_sec=asset.duration_sec,
        verified=asset.verified,
        preview_url=f"/media/asset/{asset.id}",
    )


def _scene_plan_response(plan: ScenePlan) -> ScenePlanResponse:
    return ScenePlanResponse(
        id=plan.id,
        script_id=plan.script_id,
        scene_count=len(plan.scenes) if plan.scenes else 0,
        total_duration_sec=plan.total_duration_sec,
        created_at=plan.created_at,
    )


def _script_detail(script: Script) -> ScriptDetailResponse:
    return ScriptDetailResponse(
        id=script.id,
        topic_id=script.topic_id,
        hook=script.hook,
        body=script.body,
        ending=script.ending,
        cta=script.cta,
        estimated_duration_sec=script.estimated_duration_sec,
        quality_score=script.quality_score,
        status=script.status.value,
        hook_variant=script.hook_variant,
        created_at=script.created_at,
        metadata_=script.metadata_,
        topic=TopicSummary.model_validate(script.topic),
        scene_plan_ids=[plan.id for plan in script.scene_plans],
        video_ids=[video.id for video in script.videos],
    )


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    status: str | None = Query(None),
    task_name: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    if task_name:
        query = query.filter(Job.task_name == task_name)
    total = query.count()
    items = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
    return JobListResponse(items=items, total=total)


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


@router.get("/scripts/{script_id}", response_model=ScriptDetailResponse)
def get_script(script_id: int, db: Session = Depends(get_db)):
    script = db.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return _script_detail(script)


@router.post("/scripts/{script_id}/approve", response_model=ScriptDetailResponse)
def approve_script(
    script_id: int,
    body: ScriptReviewRequest = ScriptReviewRequest(),
    db: Session = Depends(get_db),
):
    script = db.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    metadata = dict(script.metadata_ or {})
    metadata["review_source"] = "manual"
    if body.reason:
        metadata["review_reason"] = body.reason
    script.status = ScriptStatus.APPROVED
    script.metadata_ = metadata
    db.commit()
    db.refresh(script)
    return _script_detail(script)


@router.post("/scripts/{script_id}/reject", response_model=ScriptDetailResponse)
def reject_script(
    script_id: int,
    body: ScriptReviewRequest = ScriptReviewRequest(),
    db: Session = Depends(get_db),
):
    script = db.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    metadata = dict(script.metadata_ or {})
    metadata["review_source"] = "manual"
    if body.reason:
        metadata["review_reason"] = body.reason
    script.status = ScriptStatus.REJECTED
    script.metadata_ = metadata
    db.commit()
    db.refresh(script)
    return _script_detail(script)


@router.post("/scripts/{script_id}/media", response_model=JobResponse)
def generate_media(script_id: int, db: Session = Depends(get_db)):
    script = db.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    job = create_job("media.process", payload={"script_id": script_id})
    tasks.run_media_pipeline.delay(script_id=script_id, job_id=job.id)
    return db.get(Job, job.id)


@router.get("/scene-plans", response_model=list[ScenePlanResponse])
def list_scene_plans(
    script_id: int | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(ScenePlan)
    if script_id is not None:
        query = query.filter(ScenePlan.script_id == script_id)
    return [_scene_plan_response(plan) for plan in query.order_by(ScenePlan.created_at.desc()).offset(offset).limit(limit).all()]


@router.get("/scene-plans/{scene_plan_id}", response_model=ScenePlanDetailResponse)
def get_scene_plan(scene_plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(ScenePlan, scene_plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Scene plan not found")
    base = _scene_plan_response(plan)
    return ScenePlanDetailResponse(
        **base.model_dump(),
        scenes=plan.scenes,
        assets=[_asset_response(asset) for asset in plan.assets],
    )


@router.post("/scene-plans/{scene_plan_id}/render", response_model=JobResponse)
def render_scene_plan(scene_plan_id: int, db: Session = Depends(get_db)):
    job = create_job("render.video", payload={"scene_plan_id": scene_plan_id})
    tasks.run_render.delay(scene_plan_id=scene_plan_id, job_id=job.id)
    return db.get(Job, job.id)


@router.get("/videos", response_model=list[VideoResponse])
def list_videos(
    qa_status: str | None = Query(None),
    publish_status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Video)
    if qa_status:
        query = query.filter(Video.qa_status == qa_status)
    if publish_status:
        query = query.filter(Video.publish_status == publish_status)
    return query.order_by(Video.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    response = VideoResponse.model_validate(video)
    if video.s3_key:
        response.preview_url = f"/media/video/{video_id}"
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


@router.get("/publications/{publication_id}", response_model=PublicationDetailResponse)
def get_publication(publication_id: int, db: Session = Depends(get_db)):
    publication = db.get(Publication, publication_id)
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")
    video_summary = None
    if publication.video:
        video_summary = VideoSummary(
            id=publication.video.id,
            script_id=publication.video.script_id,
            duration_sec=publication.video.duration_sec,
            qa_status=publication.video.qa_status.value,
        )
    return PublicationDetailResponse(
        id=publication.id,
        video_id=publication.video_id,
        channel_id=publication.channel_id,
        platform=publication.platform.value,
        external_id=publication.external_id,
        status=publication.status.value,
        scheduled_at=publication.scheduled_at,
        published_at=publication.published_at,
        created_at=publication.created_at,
        platform_url=_platform_url(publication.platform.value, publication.external_id),
        video_summary=video_summary,
    )


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


@router.get("/analytics/top-topics", response_model=list[RankedItem])
def analytics_top_topics(limit: int = Query(10, le=50)):
    from short_factory.analytics.collector import get_top_topics

    return get_top_topics(limit=limit)


@router.get("/analytics/top-scripts", response_model=list[RankedItem])
def analytics_top_scripts(limit: int = Query(10, le=50)):
    from short_factory.analytics.collector import get_top_scripts

    return get_top_scripts(limit=limit)


@router.get("/analytics/category-performance", response_model=list[CategoryPerformance])
def analytics_category_performance():
    from short_factory.analytics.collector import get_category_performance

    return get_category_performance()


@router.post("/analytics/optimize", response_model=JobResponse)
def trigger_optimization(db: Session = Depends(get_db)):
    job = create_job("analytics.optimize")
    tasks.run_optimization.delay(job_id=job.id)
    return db.get(Job, job.id)
