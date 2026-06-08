import io
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from short_factory.api.main import app
from short_factory.db.models import (
    Asset,
    AssetType,
    Base,
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

client = TestClient(app)


@pytest.fixture()
def api_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    db = session_factory()
    try:
        yield db, TestClient(app)
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        app.dependency_overrides.clear()


def _seed_pipeline_data(db):
    topic = Topic(
        topic="Why avoidant partners pull away",
        category="attachment_styles",
        virality_score=0.9,
    )
    db.add(topic)
    db.flush()

    script = Script(
        topic_id=topic.id,
        hook="They pull away when you get close.",
        body="Body text.",
        ending="Ending.",
        cta="Follow for more.",
        quality_score=0.8,
        status=ScriptStatus.REJECTED,
        metadata_={"validation_issues": ["hook_too_long"], "review_source": "auto"},
    )
    db.add(script)
    db.flush()

    scene_plan = ScenePlan(
        script_id=script.id,
        scenes=[{"index": 0, "text": "Scene one", "emotion": "curiosity"}],
        total_duration_sec=8.0,
    )
    db.add(scene_plan)
    db.flush()

    asset = Asset(
        scene_plan_id=scene_plan.id,
        asset_type=AssetType.VOICE,
        s3_key="audio/1/scene_0.mp3",
        scene_index=0,
        duration_sec=8.0,
        verified=True,
    )
    db.add(asset)
    db.flush()

    video = Video(
        script_id=script.id,
        s3_key="videos/1/final.mp4",
        duration_sec=40.0,
        qa_status=QAStatus.PASSED,
        publish_status=PublishStatus.DRAFT,
    )
    db.add(video)
    db.flush()

    publication = Publication(
        video_id=video.id,
        platform=Platform.YOUTUBE,
        external_id="abc123xyz",
        status=PublishStatus.PUBLISHED,
        published_at=datetime.now(UTC),
    )
    db.add(publication)
    db.flush()

    job = Job(
        task_name="render.video",
        status=JobStatus.COMPLETED,
        result={"result": video.id},
    )
    db.add(job)
    db.commit()

    return {
        "topic": topic,
        "script": script,
        "scene_plan": scene_plan,
        "asset": asset,
        "video": video,
        "publication": publication,
        "job": job,
    }


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_page():
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Short Factory" in response.text
    assert "Pipeline Actions" in response.text
    assert "Run Research" in response.text
    assert "Run Full Pipeline" in response.text
    assert 'href="/admin/jobs"' in response.text
    assert 'href="/admin/videos"' in response.text


def test_admin_jobs_page():
    response = client.get("/admin/jobs")
    assert response.status_code == 200
    assert "Jobs" in response.text


def test_admin_videos_page():
    response = client.get("/admin/videos")
    assert response.status_code == 200
    assert "Videos" in response.text


def test_admin_topics_page():
    response = client.get("/admin/topics")
    assert response.status_code == 200
    assert "Topics" in response.text


def test_analytics_dashboard_endpoints():
    with patch(
        "short_factory.analytics.collector.get_top_topics",
        return_value=[{"id": 1, "label": "Topic", "category": "breakups", "views": 10, "avg_retention": 0.8, "avg_ctr": 0.1, "score": 0.5}],
    ):
        response = client.get("/analytics/top-topics")
    assert response.status_code == 200
    assert response.json()[0]["label"] == "Topic"

    with patch(
        "short_factory.analytics.collector.get_top_scripts",
        return_value=[{"id": 2, "label": "Hook", "category": None, "views": 5, "avg_retention": 0.7, "avg_ctr": 0.09, "score": 0.45}],
    ):
        response = client.get("/analytics/top-scripts")
    assert response.status_code == 200
    assert response.json()[0]["id"] == 2


def test_list_jobs(api_db):
    db, client = api_db
    data = _seed_pipeline_data(db)
    response = client.get("/jobs", params={"task_name": "render.video"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == data["job"].id


def test_get_script_detail(api_db):
    db, client = api_db
    data = _seed_pipeline_data(db)
    response = client.get(f"/scripts/{data['script'].id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["hook"] == data["script"].hook
    assert payload["metadata_"]["review_source"] == "auto"
    assert payload["topic"]["id"] == data["topic"].id
    assert data["scene_plan"].id in payload["scene_plan_ids"]
    assert data["video"].id in payload["video_ids"]


def test_approve_script_sets_manual_review(api_db):
    db, client = api_db
    data = _seed_pipeline_data(db)
    response = client.post(
        f"/scripts/{data['script'].id}/approve",
        json={"reason": "Good enough for production"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "approved"
    assert payload["metadata_"]["review_source"] == "manual"
    assert payload["metadata_"]["review_reason"] == "Good enough for production"


def test_reject_script_sets_manual_review(api_db):
    db, client = api_db
    data = _seed_pipeline_data(db)
    data["script"].status = ScriptStatus.APPROVED
    db.commit()

    response = client.post(f"/scripts/{data['script'].id}/reject")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert payload["metadata_"]["review_source"] == "manual"


def test_list_and_get_scene_plans(api_db):
    db, client = api_db
    data = _seed_pipeline_data(db)
    list_response = client.get("/scene-plans", params={"script_id": data["script"].id})
    assert list_response.status_code == 200
    plans = list_response.json()
    assert len(plans) == 1
    assert plans[0]["scene_count"] == 1

    detail_response = client.get(f"/scene-plans/{data['scene_plan'].id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["scenes"][0]["text"] == "Scene one"
    assert detail["assets"][0]["preview_url"] == f"/media/asset/{data['asset'].id}"


def test_list_videos_and_preview_url(api_db):
    db, client = api_db
    data = _seed_pipeline_data(db)
    list_response = client.get("/videos", params={"qa_status": "passed"})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = client.get(f"/videos/{data['video'].id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["preview_url"] == f"/media/video/{data['video'].id}"


def test_get_publication_detail(api_db):
    db, client = api_db
    data = _seed_pipeline_data(db)
    response = client.get(f"/publications/{data['publication'].id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["platform_url"] == "https://youtube.com/watch?v=abc123xyz"
    assert payload["video_summary"]["id"] == data["video"].id


def test_get_publication_skips_stub_platform_url(api_db):
    db, client = api_db
    data = _seed_pipeline_data(db)
    data["publication"].external_id = "stub_youtube_1"
    db.commit()

    response = client.get(f"/publications/{data['publication'].id}")
    assert response.status_code == 200
    assert response.json()["platform_url"] is None


def test_media_asset_stream(api_db):
    db, client = api_db
    data = _seed_pipeline_data(db)
    stream_body = io.BytesIO(b"fake-audio-bytes")

    with patch("short_factory.api.media.storage.exists", return_value=True):
        with patch("short_factory.api.media.storage.stream_object", return_value=stream_body):
            response = client.get(f"/media/asset/{data['asset'].id}")

    assert response.status_code == 200
    assert response.content == b"fake-audio-bytes"
    assert response.headers["content-type"].startswith("audio/mpeg")


def test_media_video_download_attachment(api_db):
    db, client = api_db
    data = _seed_pipeline_data(db)
    stream_body = io.BytesIO(b"fake-video-bytes")

    with patch("short_factory.api.media.storage.exists", return_value=True):
        with patch("short_factory.api.media.storage.stream_object", return_value=stream_body):
            response = client.get(f"/media/video/{data['video'].id}/download")

    assert response.status_code == 200
    assert response.content == b"fake-video-bytes"
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["content-type"] == "video/mp4"


def test_extract_entity_ids_unwraps_render_result():
    assert extract_entity_ids("render.video", {"result": 42}) == {"video_ids": [42]}


def test_extract_entity_ids_pipeline_full():
    result = {
        "video_ids": [10, 11],
        "scripts": {"script_ids": [1, 2]},
        "media": [{"scene_plan_id": 5}, {"scene_plan_id": 6}],
    }
    assert extract_entity_ids("pipeline.full", result) == {
        "video_ids": [10, 11],
        "script_ids": [1, 2],
        "scene_plan_ids": [5, 6],
    }
