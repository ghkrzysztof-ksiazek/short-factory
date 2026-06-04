from datetime import datetime

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: int
    celery_task_id: str | None
    task_name: str
    status: str
    payload: dict | None
    result: dict | None
    error: str | None
    retries: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TopicResponse(BaseModel):
    id: int
    topic: str
    category: str | None
    emotion: str | None
    emotional_score: float | None
    virality_score: float | None
    source: str | None
    source_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScriptResponse(BaseModel):
    id: int
    topic_id: int
    hook: str
    body: str
    ending: str
    cta: str
    estimated_duration_sec: float | None
    quality_score: float | None
    status: str
    hook_variant: int
    created_at: datetime

    model_config = {"from_attributes": True}


class VideoResponse(BaseModel):
    id: int
    script_id: int
    s3_key: str | None
    duration_sec: float | None
    qa_status: str
    qa_details: dict | None
    publish_status: str
    preview_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PublicationResponse(BaseModel):
    id: int
    video_id: int
    platform: str
    external_id: str | None
    status: str
    scheduled_at: datetime | None
    published_at: datetime | None

    model_config = {"from_attributes": True}


class AnalyticsSummary(BaseModel):
    total_views: int
    avg_retention: float
    publications: int
    top_categories: list[dict]
