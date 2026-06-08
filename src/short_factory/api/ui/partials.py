from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from short_factory.api.schemas import ScriptReviewRequest
from short_factory.api.ui.templates_env import templates
from short_factory.db.models import Job, JobStatus, Script, ScriptStatus
from short_factory.db.session import get_db
from short_factory.shared.jobs import create_job, extract_entity_ids
from short_factory.workers import tasks

router = APIRouter(prefix="/admin/partials", tags=["admin-ui-partials"])

_RUNNING_STATUSES = {JobStatus.PENDING.value, JobStatus.RUNNING.value}


def _hx_redirect(url: str) -> Response:
    return Response(status_code=200, headers={"HX-Redirect": url})


@router.post("/run-research")
def run_research(request: Request, db: Session = Depends(get_db)):
    job = create_job("research.run")
    tasks.run_research.delay(job_id=job.id)
    return _hx_redirect(f"/admin/jobs/{job.id}")


@router.post("/run-scripts")
def run_scripts(request: Request, db: Session = Depends(get_db)):
    job = create_job("scripts.generate")
    tasks.run_script_generation.delay(job_id=job.id)
    return _hx_redirect(f"/admin/jobs/{job.id}")


@router.post("/run-pipeline")
def run_pipeline(request: Request, db: Session = Depends(get_db)):
    job = create_job("pipeline.full")
    tasks.run_full_pipeline.delay(job_id=job.id)
    return _hx_redirect(f"/admin/jobs/{job.id}")


@router.post("/run-optimization")
def run_optimization(request: Request, db: Session = Depends(get_db)):
    job = create_job("analytics.optimize")
    tasks.run_optimization.delay(job_id=job.id)
    return _hx_redirect(f"/admin/jobs/{job.id}")


@router.get("/jobs/{job_id}/status", response_class=HTMLResponse)
def job_status_partial(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    entity_ids = extract_entity_ids(job.task_name, job.result)
    poll = job.status.value in _RUNNING_STATUSES
    return templates.TemplateResponse(
        request,
        "components/job_status_panel.html",
        {
            "request": request,
            "job": job,
            "entity_ids": entity_ids,
            "poll": poll,
        },
    )


@router.post("/scripts/{script_id}/approve", response_class=HTMLResponse)
def approve_script_partial(
    request: Request,
    script_id: int,
    db: Session = Depends(get_db),
):
    script = db.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    body = ScriptReviewRequest()
    metadata = dict(script.metadata_ or {})
    metadata["review_source"] = "manual"
    script.status = ScriptStatus.APPROVED
    script.metadata_ = metadata
    db.commit()
    db.refresh(script)
    return templates.TemplateResponse(
        request,
        "components/script_status_panel.html",
        {"request": request, "script": script},
    )


@router.post("/scripts/{script_id}/reject", response_class=HTMLResponse)
def reject_script_partial(
    request: Request,
    script_id: int,
    db: Session = Depends(get_db),
):
    script = db.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    metadata = dict(script.metadata_ or {})
    metadata["review_source"] = "manual"
    script.status = ScriptStatus.REJECTED
    script.metadata_ = metadata
    db.commit()
    db.refresh(script)
    return templates.TemplateResponse(
        request,
        "components/script_status_panel.html",
        {"request": request, "script": script},
    )


@router.post("/scripts/{script_id}/media")
def generate_media_partial(script_id: int, db: Session = Depends(get_db)):
    script = db.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    job = create_job("media.process", payload={"script_id": script_id})
    tasks.run_media_pipeline.delay(script_id=script_id, job_id=job.id)
    return _hx_redirect(f"/admin/jobs/{job.id}")


@router.post("/scene-plans/{scene_plan_id}/render")
def render_scene_plan_partial(scene_plan_id: int, db: Session = Depends(get_db)):
    job = create_job("render.video", payload={"scene_plan_id": scene_plan_id})
    tasks.run_render.delay(scene_plan_id=scene_plan_id, job_id=job.id)
    return _hx_redirect(f"/admin/jobs/{job.id}")


@router.post("/videos/{video_id}/publish")
def publish_video_partial(
    video_id: int,
    platform: str = Form("youtube"),
    db: Session = Depends(get_db),
):
    from short_factory.db.models import Video

    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    job = create_job("publish.video", payload={"video_id": video_id, "platform": platform})
    tasks.run_publish.delay(video_id=video_id, platform=platform, job_id=job.id)
    return _hx_redirect(f"/admin/jobs/{job.id}")


@router.post("/publications/{publication_id}/analytics")
def collect_analytics_partial(publication_id: int, db: Session = Depends(get_db)):
    from short_factory.db.models import Publication

    pub = db.get(Publication, publication_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    job = create_job("analytics.collect", payload={"publication_id": publication_id})
    tasks.run_analytics_collection.delay(publication_id=publication_id, job_id=job.id)
    return _hx_redirect(f"/admin/jobs/{job.id}")
