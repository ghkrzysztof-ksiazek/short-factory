from unittest.mock import MagicMock, patch

from short_factory.analytics.collector import (
    _fetch_youtube_analytics_report,
    _fetch_youtube_metrics,
    run_optimization_feedback,
)
from short_factory.db.models import (
    AnalyticsEvent,
    Publication,
    Platform,
    PublishStatus,
    Script,
    ScriptStatus,
    Topic,
    Video,
)
from short_factory.publish.publishers import YouTubePublisher
from short_factory.shared.optimization import build_script_context


def test_hook_patterns_injected_into_script_context(sqlite_db):
    from short_factory.db.models import OptimizationWeight

    sqlite_db.add(
        OptimizationWeight(dimension="hook_pattern", value="Emotionally safe men are different.", weight=1.8)
    )
    sqlite_db.commit()

    context = build_script_context()
    assert "Winning hook patterns" in context
    assert "Emotionally safe men are different." in context


def test_optimization_feedback_tracks_hook_patterns(sqlite_db):
    topic = Topic(topic="T", category="breakups", emotion="curiosity", virality_score=0.8, source="test")
    sqlite_db.add(topic)
    sqlite_db.flush()
    script = Script(
        topic_id=topic.id,
        hook="Why silence hurts more than anger.",
        body="b",
        ending="e",
        cta="c",
        status=ScriptStatus.APPROVED,
    )
    sqlite_db.add(script)
    sqlite_db.flush()
    video = Video(script_id=script.id, s3_key="videos/1/final.mp4")
    sqlite_db.add(video)
    sqlite_db.flush()
    pub = Publication(
        video_id=video.id,
        platform=Platform.YOUTUBE,
        external_id="abc123",
        status=PublishStatus.PUBLISHED,
    )
    sqlite_db.add(pub)
    sqlite_db.flush()
    sqlite_db.add(
        AnalyticsEvent(
            publication_id=pub.id,
            views=1000,
            ctr=0.1,
            retention_rate=0.8,
        )
    )
    sqlite_db.commit()

    result = run_optimization_feedback()
    assert result["hook_patterns"] >= 1

    from short_factory.db.models import OptimizationWeight

    hook_weight = (
        sqlite_db.query(OptimizationWeight)
        .filter(OptimizationWeight.dimension == "hook_pattern")
        .first()
    )
    assert hook_weight is not None
    assert "Why silence hurts" in hook_weight.value


def test_youtube_dry_run_skips_upload():
    from short_factory.config.settings import settings

    publisher = YouTubePublisher()
    video = Video(id=7, script_id=1, s3_key="videos/7/final.mp4")

    with patch.object(settings, "youtube_dry_run", True):
        external_id = publisher.publish(video, "Title", "Description")

    assert external_id == "dry_run_youtube_7"


def test_youtube_analytics_api_integration():
    mock_analytics = MagicMock()
    mock_reports = MagicMock()
    mock_query = MagicMock()
    mock_analytics.reports.return_value = mock_reports
    mock_reports.query.return_value = mock_query
    mock_query.execute.return_value = {
        "rows": [[500, 10.5, 32.0, 0.07]],
    }

    with patch("short_factory.analytics.collector._youtube_credentials", return_value=object()):
        with patch("short_factory.config.settings.settings.youtube_channel_id", "UC_TEST"):
            with patch("googleapiclient.discovery.build", return_value=mock_analytics):
                metrics = _fetch_youtube_analytics_report("video123")

    assert metrics["analytics_api"] is True
    assert metrics["views"] == 500
    assert metrics["retention_rate"] > 0


def test_fetch_youtube_metrics_merges_data_and_analytics():
    mock_youtube = MagicMock()
    mock_videos = MagicMock()
    mock_youtube.videos.return_value = mock_videos
    mock_videos.list.return_value.execute.return_value = {
        "items": [{"statistics": {"viewCount": "900", "commentCount": "12"}}]
    }

    with patch("short_factory.config.settings.settings.youtube_api_key", "test-key"):
        with patch("googleapiclient.discovery.build", return_value=mock_youtube):
            with patch(
                "short_factory.analytics.collector._fetch_youtube_analytics_report",
                return_value={"avg_view_duration_sec": 30.0, "ctr": 0.08, "retention_rate": 0.66},
            ):
                metrics = _fetch_youtube_metrics("video123")

    assert metrics["views"] == 900
    assert metrics["comments"] == 12
    assert metrics["retention_rate"] == 0.66
    assert metrics["source"] == "youtube_api"
