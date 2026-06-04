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
