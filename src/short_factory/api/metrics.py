from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from short_factory.db.models import Job, JobStatus
from short_factory.db.session import get_db

router = APIRouter(prefix="/metrics", tags=["monitoring"])


@router.get("")
def metrics(db: Session = Depends(get_db)):
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
