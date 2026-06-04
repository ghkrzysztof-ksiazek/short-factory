from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from short_factory.research.reddit_scraper import scrape_reddit
from short_factory.research.youtube_scraper import scrape_youtube
from short_factory.research.tiktok_scraper import scrape_tiktok
from short_factory.research.trends_scraper import scrape_google_trends
from short_factory.shared.embeddings import _word_overlap_duplicate, cosine_similarity
from short_factory.shared.optimization import build_script_context, get_category_weight
from short_factory.media.subtitles import validate_subtitle_timing


def test_mock_research_produces_at_least_twenty_topics():
    total = len(scrape_reddit()) + len(scrape_youtube()) + len(scrape_tiktok()) + len(
        scrape_google_trends()
    )
    assert total >= 20


def test_cosine_similarity_identical_vectors():
    vec = [1.0, 0.0, 0.0]
    assert cosine_similarity(vec, vec) == 1.0


def test_word_overlap_duplicate_detects_similar_titles():
    existing = ["Why emotionally unavailable people feel addictive"]
    assert _word_overlap_duplicate(
        "Why emotionally unavailable people feel addictive", existing, 0.85
    )


def test_optimization_context_empty_without_weights():
    with patch("short_factory.shared.optimization.get_weights", return_value={}):
        assert build_script_context() == ""


def test_optimization_context_includes_weights():
    weights = {"attachment_styles": 1.5, "breakups": 1.2}
    with patch("short_factory.shared.optimization.get_weights") as mock_get:
        mock_get.side_effect = lambda dim: weights if dim == "category" else {}
        context = build_script_context()
        assert "attachment_styles" in context


def test_category_weight_default():
    with patch("short_factory.shared.optimization.get_weights", return_value={}):
        assert get_category_weight("unknown") == 1.0


def test_subtitle_timing_validation_flags_overlap():
    issues = validate_subtitle_timing([{"word": "a", "start": 1.0, "end": 0.5}])
    assert "overlap_at_segment_0" in issues


def test_celery_task_wrapper_retries_before_dead_letter():
    from short_factory.db.models import JobStatus
    from short_factory.workers import tasks

    task = MagicMock()
    task.request.retries = 0
    task.max_retries = 3
    task.default_retry_delay = 1
    task.retry.side_effect = Exception("retry called")

    with patch("short_factory.workers.tasks.create_job") as mock_create:
        mock_create.return_value = MagicMock(id=99)
        with patch("short_factory.workers.tasks.update_job") as mock_update:
            try:
                tasks._task_wrapper(task, "test.task", 99, lambda: (_ for _ in ()).throw(RuntimeError("fail")))
            except Exception as exc:
                assert str(exc) == "retry called"

            mock_update.assert_any_call(99, status=JobStatus.FAILED, error="fail", retries=1)
            task.retry.assert_called_once()


def test_scheduled_publish_creates_publication_without_immediate_upload():
    from short_factory.db.models import Platform, PublishStatus, Publication, Video
    from short_factory.publish import publishers

    video = Video(id=1, script_id=1, s3_key="videos/1/final.mp4")
    video.script = MagicMock(hook="Hook", body="Body", cta="CTA")

    scheduled_at = datetime.now(UTC) + timedelta(hours=2)

    with patch.object(publishers, "SessionLocal") as mock_session_local:
        db = MagicMock()
        mock_session_local.return_value = db
        db.get.return_value = video

        with patch("short_factory.workers.tasks.run_scheduled_publish") as mock_task:
            mock_task.apply_async = MagicMock()
            pub_id = publishers.publish_video(
                1, Platform.YOUTUBE, scheduled_at=scheduled_at
            )

        added = db.add.call_args[0][0]
        assert isinstance(added, Publication)
        assert added.status == PublishStatus.SCHEDULED
        mock_task.apply_async.assert_called_once()
