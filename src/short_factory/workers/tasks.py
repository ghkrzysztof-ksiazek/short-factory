from short_factory.config.logging import get_logger, setup_logging
from short_factory.db.models import JobStatus, Script, ScriptStatus
from short_factory.db.session import SessionLocal
from short_factory.shared.jobs import create_job, update_job
from short_factory.workers.celery_app import celery_app

logger = get_logger(__name__)
setup_logging()


def _task_wrapper(task, task_name: str, job_id: int | None, fn, *args, **kwargs):
    if job_id is None:
        job = create_job(task_name, payload={"args": list(args), "kwargs": kwargs})
        job_id = job.id

    celery_id = task.request.id if task else None
    update_job(job_id, status=JobStatus.RUNNING, celery_task_id=celery_id)
    try:
        result = fn(*args, **kwargs)
        payload = result if isinstance(result, dict) else {"result": result}
        update_job(job_id, status=JobStatus.COMPLETED, result=payload)
        return result
    except Exception as exc:
        logger.error("task_failed", task=task_name, job_id=job_id, error=str(exc))
        retries = task.request.retries if task else 0
        max_retries = task.max_retries if task else 3

        if retries < max_retries:
            update_job(job_id, status=JobStatus.FAILED, error=str(exc), retries=retries + 1)
            raise task.retry(exc=exc, countdown=task.default_retry_delay)

        update_job(job_id, status=JobStatus.DEAD_LETTER, error=str(exc), retries=retries + 1)
        raise


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def ping(self, job_id: int | None = None):
    return _task_wrapper(self, "ping", job_id, lambda: {"status": "pong"})


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120, queue="research")
def run_research(self, job_id: int | None = None):
    from short_factory.research.pipeline import run_research_pipeline

    return _task_wrapper(self, "research.run", job_id, run_research_pipeline)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120, queue="generation")
def run_script_generation(self, job_id: int | None = None, topic_id: int | None = None):
    from short_factory.scripts.generator import (
        generate_scripts_for_top_topics,
        generate_scripts_for_topic,
    )

    if topic_id:

        def fn():
            return {"script_ids": generate_scripts_for_topic(topic_id)}
    else:
        fn = generate_scripts_for_top_topics
    return _task_wrapper(self, "scripts.generate", job_id, fn)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120, queue="generation")
def run_media_pipeline(self, script_id: int, job_id: int | None = None):
    from short_factory.media.pipeline import process_approved_script

    return _task_wrapper(self, "media.process", job_id, process_approved_script, script_id)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=180, queue="render")
def run_render(self, scene_plan_id: int, job_id: int | None = None):
    from short_factory.render.ffmpeg_renderer import render_video

    return _task_wrapper(self, "render.video", job_id, render_video, scene_plan_id)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120, queue="publish")
def run_publish(
    self,
    video_id: int,
    platform: str = "youtube",
    job_id: int | None = None,
    channel_id: int | None = None,
):
    from short_factory.db.models import Platform
    from short_factory.publish.publishers import publish_video

    return _task_wrapper(
        self,
        "publish.video",
        job_id,
        publish_video,
        video_id,
        Platform(platform),
        channel_id,
        None,
    )


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120, queue="publish")
def run_scheduled_publish(
    self,
    publication_id: int,
    job_id: int | None = None,
):
    from short_factory.publish.publishers import execute_scheduled_publication

    return _task_wrapper(self, "publish.scheduled", job_id, execute_scheduled_publication, publication_id)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120, queue="publish")
def process_due_publications(self, job_id: int | None = None):
    from short_factory.publish.publishers import enqueue_due_publications

    return _task_wrapper(self, "publish.process_due", job_id, enqueue_due_publications)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def run_analytics_collection(self, publication_id: int, job_id: int | None = None):
    from short_factory.analytics.collector import collect_youtube_analytics

    return _task_wrapper(self, "analytics.collect", job_id, collect_youtube_analytics, publication_id)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def run_optimization(self, job_id: int | None = None):
    from short_factory.analytics.collector import run_optimization_feedback

    return _task_wrapper(self, "analytics.optimize", job_id, run_optimization_feedback)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def run_full_pipeline(self, job_id: int | None = None):
    """End-to-end: research → scripts → media → render for approved scripts."""

    def _pipeline():
        from short_factory.analytics.collector import get_performance_summary
        from short_factory.media.pipeline import process_approved_script
        from short_factory.render.ffmpeg_renderer import render_video
        from short_factory.research.pipeline import run_research_pipeline
        from short_factory.scripts.generator import generate_scripts_for_top_topics

        research_result = run_research_pipeline()
        script_result = generate_scripts_for_top_topics(limit=1)

        db = SessionLocal()
        try:
            approved = (
                db.query(Script).filter(Script.status == ScriptStatus.APPROVED).limit(1).all()
            )
        finally:
            db.close()

        media_results = []
        video_ids = []
        for script in approved:
            media = process_approved_script(script.id)
            media_results.append(media)
            video_id = render_video(media["scene_plan_id"])
            video_ids.append(video_id)

        return {
            "research": research_result,
            "scripts": script_result,
            "media": media_results,
            "video_ids": video_ids,
            "performance": get_performance_summary(),
        }

    return _task_wrapper(self, "pipeline.full", job_id, _pipeline)
