from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from short_factory.db.models import Job, JobStatus
from short_factory.db.session import get_db

router = APIRouter(prefix="/metrics", tags=["monitoring"])


@router.get("")
def metrics_json(db: Session = Depends(get_db)):
    """Simple operational metrics for monitoring DLQ depth and job status."""
    jobs = db.query(Job).all()
    by_status = {s.value: 0 for s in JobStatus}
    for job in jobs:
        by_status[job.status.value] = by_status.get(job.status.value, 0) + 1

    return {
        "jobs_total": len(jobs),
        "jobs_by_status": by_status,
        "dead_letter_depth": by_status.get("dead_letter", 0),
        "queues": ["default", "research", "generation", "render", "publish"],
    }


@router.get("/prometheus")
def metrics_prometheus(db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    by_status = {s.value: 0 for s in JobStatus}
    for job in jobs:
        by_status[job.status.value] = by_status.get(job.status.value, 0) + 1

    lines = [
        "# HELP short_factory_jobs_total Total tracked jobs",
        "# TYPE short_factory_jobs_total gauge",
        f"short_factory_jobs_total {len(jobs)}",
        "# HELP short_factory_dead_letter_depth Jobs in dead letter state",
        "# TYPE short_factory_dead_letter_depth gauge",
        f"short_factory_dead_letter_depth {by_status.get('dead_letter', 0)}",
    ]
    for status, count in by_status.items():
        lines.extend(
            [
                "# HELP short_factory_jobs_by_status Jobs grouped by status",
                "# TYPE short_factory_jobs_by_status gauge",
                f'short_factory_jobs_by_status{{status="{status}"}} {count}',
            ]
        )

    return Response(content="\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
