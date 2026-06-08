from short_factory.db.models import Job, JobStatus
from short_factory.db.session import SessionLocal


def create_job(task_name: str, payload: dict | None = None) -> Job:
    db = SessionLocal()
    try:
        job = Job(task_name=task_name, payload=payload, status=JobStatus.PENDING)
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    finally:
        db.close()


def update_job(
    job_id: int,
    *,
    status: JobStatus | None = None,
    celery_task_id: str | None = None,
    result: dict | None = None,
    error: str | None = None,
    retries: int | None = None,
) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return
        if status is not None:
            job.status = status
        if celery_task_id is not None:
            job.celery_task_id = celery_task_id
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error
        if retries is not None:
            job.retries = retries
        db.commit()
    finally:
        db.close()


def get_job(job_id: int) -> Job | None:
    db = SessionLocal()
    try:
        return db.get(Job, job_id)
    finally:
        db.close()


def _add_ids(target: dict[str, list[int]], key: str, value) -> None:
    if value is None:
        return
    if isinstance(value, list):
        target[key] = [int(item) for item in value]
    else:
        target[key] = [int(value)]


def extract_entity_ids(task_name: str, result: dict | None) -> dict[str, list[int]]:
    """Normalize job result payloads into entity ID lists for UI consumption."""
    if not result:
        return {}

    ids: dict[str, list[int]] = {}

    if task_name == "scripts.generate":
        _add_ids(ids, "script_ids", result.get("script_ids"))
    elif task_name == "media.process":
        _add_ids(ids, "scene_plan_ids", result.get("scene_plan_id"))
    elif task_name == "render.video":
        _add_ids(ids, "video_ids", result.get("result", result.get("video_id")))
    elif task_name in ("publish.video", "publish.scheduled"):
        _add_ids(ids, "publication_ids", result.get("result", result.get("publication_id")))
    elif task_name == "analytics.collect":
        _add_ids(ids, "publication_ids", result.get("publication_id", result.get("result")))
    elif task_name == "pipeline.full":
        _add_ids(ids, "video_ids", result.get("video_ids"))
        scripts = result.get("scripts") or {}
        _add_ids(ids, "script_ids", scripts.get("script_ids"))
        media_results = result.get("media") or []
        scene_plan_ids = [item["scene_plan_id"] for item in media_results if item.get("scene_plan_id") is not None]
        if scene_plan_ids:
            ids["scene_plan_ids"] = [int(item) for item in scene_plan_ids]

    return ids
