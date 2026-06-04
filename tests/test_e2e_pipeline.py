from unittest.mock import patch

from short_factory.db.models import Job, JobStatus, Script, ScriptStatus, Topic
from short_factory.research.scoring import RawTopic
from short_factory.research.pipeline import run_research_pipeline
from short_factory.shared.jobs import create_job


def test_research_pipeline_persists_topics_in_sqlite(sqlite_db):
    mock_topics = [
        RawTopic(
            title="Why emotionally unavailable people feel addictive",
            source="reddit",
            source_url="https://reddit.com/mock",
            metadata={"score": 100},
        )
    ]

    with patch("short_factory.research.pipeline.scrape_reddit", return_value=mock_topics), patch(
        "short_factory.research.pipeline.scrape_youtube", return_value=[]
    ), patch("short_factory.research.pipeline.scrape_tiktok", return_value=[]), patch(
        "short_factory.research.pipeline.scrape_google_trends", return_value=[]
    ), patch("short_factory.research.pipeline.is_duplicate", return_value=False), patch(
        "short_factory.research.pipeline.classify_and_score",
        return_value={
            "topic": mock_topics[0].title,
            "category": "attachment_styles",
            "emotion": "curiosity",
            "emotional_score": 0.8,
            "virality_score": 0.9,
            "source": "reddit",
            "source_url": mock_topics[0].source_url,
            "metadata": {},
        },
    ):
        result = run_research_pipeline()

    assert result["created"] == 1
    topics = sqlite_db.query(Topic).all()
    assert len(topics) == 1
    assert topics[0].virality_score == 0.9


def test_job_tracking_with_sqlite(sqlite_db):
    job = create_job("research.run", payload={"test": True})
    assert job.id is not None

    stored = sqlite_db.get(Job, job.id)
    stored.status = JobStatus.COMPLETED
    sqlite_db.commit()

    refreshed = sqlite_db.get(Job, job.id)
    assert refreshed.status == JobStatus.COMPLETED


def test_script_and_topic_relationship_in_sqlite(sqlite_db):
    topic = Topic(
        topic="Test topic",
        category="boundaries",
        emotion="validation",
        virality_score=0.85,
        source="test",
    )
    sqlite_db.add(topic)
    sqlite_db.flush()

    script = Script(
        topic_id=topic.id,
        hook="Boundaries reveal who respects you.",
        body="Body text.",
        ending="Ending.",
        cta="Save this.",
        quality_score=0.9,
        status=ScriptStatus.APPROVED,
    )
    sqlite_db.add(script)
    sqlite_db.commit()

    assert sqlite_db.query(Script).count() == 1
    assert sqlite_db.query(Topic).count() == 1
