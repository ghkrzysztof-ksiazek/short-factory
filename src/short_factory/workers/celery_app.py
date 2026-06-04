from celery import Celery
from celery.schedules import crontab

from short_factory.config.settings import settings

celery_app = Celery("short_factory", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_routes={
        "short_factory.workers.tasks.run_research": {"queue": "research"},
        "short_factory.workers.tasks.run_script_generation": {"queue": "generation"},
        "short_factory.workers.tasks.run_media_pipeline": {"queue": "generation"},
        "short_factory.workers.tasks.run_render": {"queue": "render"},
        "short_factory.workers.tasks.run_publish": {"queue": "publish"},
        "short_factory.workers.tasks.run_scheduled_publish": {"queue": "publish"},
        "short_factory.workers.tasks.process_due_publications": {"queue": "publish"},
        "short_factory.workers.tasks.run_analytics_collection": {"queue": "default"},
        "short_factory.workers.tasks.run_optimization": {"queue": "default"},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "daily-research": {
            "task": "short_factory.workers.tasks.run_research",
            "schedule": crontab(hour=6, minute=0),
        },
        "daily-script-generation": {
            "task": "short_factory.workers.tasks.run_script_generation",
            "schedule": crontab(hour=7, minute=0),
        },
        "weekly-optimization": {
            "task": "short_factory.workers.tasks.run_optimization",
            "schedule": crontab(hour=8, minute=0, day_of_week=1),
        },
        "process-due-publications": {
            "task": "short_factory.workers.tasks.process_due_publications",
            "schedule": crontab(minute="*/5"),
        },
    },
)

import short_factory.workers.tasks  # noqa: E402, F401
