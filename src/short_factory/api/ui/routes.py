from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload

from short_factory.api.ui.templates_env import templates
from short_factory.db.models import (
    Job,
    JobStatus,
    Platform,
    Publication,
    PublishStatus,
    QAStatus,
    ScenePlan,
    Script,
    ScriptStatus,
    Topic,
    Video,
)
from short_factory.db.session import get_db
from short_factory.shared.jobs import extract_entity_ids

router = APIRouter(prefix="/admin", tags=["admin-ui"])

PAGE_SIZE = 20

NAV_ITEMS = [
    {"label": "Dashboard", "href": "/admin", "icon": "📊"},
    {"label": "Jobs", "href": "/admin/jobs", "icon": "⚙️"},
    {"label": "Topics", "href": "/admin/topics", "icon": "💡"},
    {"label": "Scripts", "href": "/admin/scripts", "icon": "📝"},
    {"label": "Scene Plans", "href": "/admin/scene-plans", "icon": "🎬"},
    {"label": "Videos", "href": "/admin/videos", "icon": "🎥"},
    {"label": "Publications", "href": "/admin/publications", "icon": "📤"},
    {"label": "Analytics", "href": "/admin/analytics", "icon": "📈"},
]


def _ctx(request: Request, **extra):
    return {"request": request, "nav_items": NAV_ITEMS, **extra}


def _paginate(query, page: int, page_size: int = PAGE_SIZE):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = max(1, (total + page_size - 1) // page_size)
    return items, total, total_pages


def _platform_url(platform: str, external_id: str | None) -> str | None:
    if not external_id or external_id.startswith(("stub_", "dry_run_")):
        return None
    if platform == Platform.YOUTUBE.value:
        return f"https://youtube.com/watch?v={external_id}"
    return None


def _dashboard_counts(db: Session) -> dict:
    job_counts = {s.value: 0 for s in JobStatus}
    for job in db.query(Job).all():
        job_counts[job.status.value] = job_counts.get(job.status.value, 0) + 1

    script_counts = {}
    for status in ScriptStatus:
        script_counts[status.value] = db.query(Script).filter(Script.status == status).count()

    return {
        "jobs_by_status": job_counts,
        "jobs_total": sum(job_counts.values()),
        "topics_count": db.query(Topic).count(),
        "scripts_by_status": script_counts,
        "videos_count": db.query(Video).count(),
        "videos_qa_passed": db.query(Video).filter(Video.qa_status == QAStatus.PASSED).count(),
        "publications_count": db.query(Publication).count(),
        "publications_published": db.query(Publication).filter(
            Publication.status == PublishStatus.PUBLISHED
        ).count(),
    }


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    recent_jobs = db.query(Job).order_by(Job.created_at.desc()).limit(20).all()
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        _ctx(
            request,
            page_title="Dashboard",
            counts=_dashboard_counts(db),
            recent_jobs=recent_jobs,
        ),
    )


@router.get("/jobs", response_class=HTMLResponse)
def jobs_list(
    request: Request,
    status: str | None = Query(None),
    task_name: str | None = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    if task_name:
        query = query.filter(Job.task_name == task_name)
    query = query.order_by(Job.created_at.desc())
    jobs, total, total_pages = _paginate(query, page)

    return templates.TemplateResponse(
        request,
        "pages/jobs/list.html",
        _ctx(
            request,
            page_title="Jobs",
            breadcrumbs=[{"label": "Jobs"}],
            jobs=jobs,
            total=total,
            page=page,
            total_pages=total_pages,
            status_filter=status,
            task_name_filter=task_name,
        ),
    )


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_detail(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    poll = job.status.value in {JobStatus.PENDING.value, JobStatus.RUNNING.value}
    return templates.TemplateResponse(
        request,
        "pages/jobs/detail.html",
        _ctx(
            request,
            page_title=f"Job #{job_id}",
            breadcrumbs=[{"label": "Jobs", "href": "/admin/jobs"}, {"label": f"#{job_id}"}],
            job=job,
            entity_ids=extract_entity_ids(job.task_name, job.result),
            poll=poll,
        ),
    )


@router.get("/topics", response_class=HTMLResponse)
def topics_list(
    request: Request,
    category: str | None = Query(None),
    min_virality: float | None = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    query = db.query(Topic)
    if category:
        query = query.filter(Topic.category == category)
    if min_virality is not None:
        query = query.filter(Topic.virality_score >= min_virality)
    query = query.order_by(Topic.virality_score.desc())
    topics, total, total_pages = _paginate(query, page)

    return templates.TemplateResponse(
        request,
        "pages/topics/list.html",
        _ctx(
            request,
            page_title="Topics",
            breadcrumbs=[{"label": "Topics"}],
            topics=topics,
            total=total,
            page=page,
            total_pages=total_pages,
            category_filter=category,
            min_virality_filter=min_virality,
        ),
    )


@router.get("/topics/{topic_id}", response_class=HTMLResponse)
def topic_detail(request: Request, topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).options(joinedload(Topic.scripts)).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return templates.TemplateResponse(
        request,
        "pages/topics/detail.html",
        _ctx(
            request,
            page_title=f"Topic #{topic_id}",
            breadcrumbs=[
                {"label": "Topics", "href": "/admin/topics"},
                {"label": f"#{topic_id}"},
            ],
            topic=topic,
            scripts=topic.scripts,
        ),
    )


@router.get("/scripts", response_class=HTMLResponse)
def scripts_list(
    request: Request,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    query = db.query(Script).options(joinedload(Script.topic))
    if status:
        query = query.filter(Script.status == status)
    query = query.order_by(Script.created_at.desc())
    scripts, total, total_pages = _paginate(query, page)

    return templates.TemplateResponse(
        request,
        "pages/scripts/list.html",
        _ctx(
            request,
            page_title="Scripts",
            breadcrumbs=[{"label": "Scripts"}],
            scripts=scripts,
            total=total,
            page=page,
            total_pages=total_pages,
            status_filter=status,
            status_tabs=[
                ("", "All"),
                ("pending_review", "Pending Review"),
                ("approved", "Approved"),
                ("rejected", "Rejected"),
            ],
        ),
    )


@router.get("/scripts/{script_id}", response_class=HTMLResponse)
def script_detail(request: Request, script_id: int, db: Session = Depends(get_db)):
    script = (
        db.query(Script)
        .options(joinedload(Script.topic), joinedload(Script.scene_plans), joinedload(Script.videos))
        .filter(Script.id == script_id)
        .first()
    )
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return templates.TemplateResponse(
        request,
        "pages/scripts/detail.html",
        _ctx(
            request,
            page_title=f"Script #{script_id}",
            breadcrumbs=[
                {"label": "Scripts", "href": "/admin/scripts"},
                {"label": f"#{script_id}"},
            ],
            script=script,
        ),
    )


@router.get("/scene-plans", response_class=HTMLResponse)
def scene_plans_list(
    request: Request,
    script_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    query = db.query(ScenePlan).options(joinedload(ScenePlan.script), joinedload(ScenePlan.assets))
    if script_id is not None:
        query = query.filter(ScenePlan.script_id == script_id)
    query = query.order_by(ScenePlan.created_at.desc())
    plans, total, total_pages = _paginate(query, page)

    plan_rows = []
    for plan in plans:
        has_video = db.query(Video).filter(Video.script_id == plan.script_id).count() > 0
        plan_rows.append({"plan": plan, "has_video": has_video})

    return templates.TemplateResponse(
        request,
        "pages/scene_plans/list.html",
        _ctx(
            request,
            page_title="Scene Plans",
            breadcrumbs=[{"label": "Scene Plans"}],
            plan_rows=plan_rows,
            total=total,
            page=page,
            total_pages=total_pages,
            script_id_filter=script_id,
        ),
    )


@router.get("/scene-plans/{scene_plan_id}", response_class=HTMLResponse)
def scene_plan_detail(request: Request, scene_plan_id: int, db: Session = Depends(get_db)):
    plan = (
        db.query(ScenePlan)
        .options(joinedload(ScenePlan.script), joinedload(ScenePlan.assets))
        .filter(ScenePlan.id == scene_plan_id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Scene plan not found")
    return templates.TemplateResponse(
        request,
        "pages/scene_plans/detail.html",
        _ctx(
            request,
            page_title=f"Scene Plan #{scene_plan_id}",
            breadcrumbs=[
                {"label": "Scene Plans", "href": "/admin/scene-plans"},
                {"label": f"#{scene_plan_id}"},
            ],
            plan=plan,
        ),
    )


@router.get("/videos", response_class=HTMLResponse)
def videos_list(
    request: Request,
    qa_status: str | None = Query(None),
    publish_status: str | None = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    query = db.query(Video).options(joinedload(Video.script))
    if qa_status:
        query = query.filter(Video.qa_status == qa_status)
    if publish_status:
        query = query.filter(Video.publish_status == publish_status)
    query = query.order_by(Video.created_at.desc())
    videos, total, total_pages = _paginate(query, page)

    return templates.TemplateResponse(
        request,
        "pages/videos/list.html",
        _ctx(
            request,
            page_title="Videos",
            breadcrumbs=[{"label": "Videos"}],
            videos=videos,
            total=total,
            page=page,
            total_pages=total_pages,
            qa_status_filter=qa_status,
            publish_status_filter=publish_status,
        ),
    )


@router.get("/videos/{video_id}", response_class=HTMLResponse)
def video_detail(request: Request, video_id: int, db: Session = Depends(get_db)):
    video = (
        db.query(Video)
        .options(
            joinedload(Video.script).joinedload(Script.topic),
            joinedload(Video.publications),
        )
        .filter(Video.id == video_id)
        .first()
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    scene_plan = (
        db.query(ScenePlan).filter(ScenePlan.script_id == video.script_id).order_by(ScenePlan.created_at.desc()).first()
    )
    return templates.TemplateResponse(
        request,
        "pages/videos/detail.html",
        _ctx(
            request,
            page_title=f"Video #{video_id}",
            breadcrumbs=[
                {"label": "Videos", "href": "/admin/videos"},
                {"label": f"#{video_id}"},
            ],
            video=video,
            scene_plan=scene_plan,
        ),
    )


@router.get("/publications", response_class=HTMLResponse)
def publications_list(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Publication)
        .options(joinedload(Publication.video).joinedload(Video.script))
        .order_by(Publication.created_at.desc())
    )
    publications, total, total_pages = _paginate(query, page)

    pub_rows = [
        {
            "publication": pub,
            "platform_url": _platform_url(pub.platform.value, pub.external_id),
        }
        for pub in publications
    ]

    return templates.TemplateResponse(
        request,
        "pages/publications/list.html",
        _ctx(
            request,
            page_title="Publications",
            breadcrumbs=[{"label": "Publications"}],
            pub_rows=pub_rows,
            total=total,
            page=page,
            total_pages=total_pages,
        ),
    )


@router.get("/publications/{publication_id}", response_class=HTMLResponse)
def publication_detail(request: Request, publication_id: int, db: Session = Depends(get_db)):
    publication = (
        db.query(Publication)
        .options(joinedload(Publication.video).joinedload(Video.script))
        .filter(Publication.id == publication_id)
        .first()
    )
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")
    return templates.TemplateResponse(
        request,
        "pages/publications/detail.html",
        _ctx(
            request,
            page_title=f"Publication #{publication_id}",
            breadcrumbs=[
                {"label": "Publications", "href": "/admin/publications"},
                {"label": f"#{publication_id}"},
            ],
            publication=publication,
            platform_url=_platform_url(publication.platform.value, publication.external_id),
        ),
    )


@router.get("/analytics", response_class=HTMLResponse)
def analytics_page(request: Request, db: Session = Depends(get_db)):
    from short_factory.analytics.collector import (
        get_category_performance,
        get_performance_summary,
        get_top_scripts,
        get_top_topics,
    )

    summary = get_performance_summary()
    top_topics = get_top_topics(limit=10)
    top_scripts = get_top_scripts(limit=10)
    category_perf = get_category_performance()

    return templates.TemplateResponse(
        request,
        "pages/analytics/index.html",
        _ctx(
            request,
            page_title="Analytics",
            breadcrumbs=[{"label": "Analytics"}],
            summary=summary,
            top_topics=top_topics,
            top_scripts=top_scripts,
            category_perf=category_perf,
        ),
    )
