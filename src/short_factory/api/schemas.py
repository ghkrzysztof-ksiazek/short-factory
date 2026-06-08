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


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int


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


class TopicSummary(BaseModel):
    id: int
    topic: str
    category: str | None
    virality_score: float | None

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


class ScriptDetailResponse(ScriptResponse):
    metadata_: dict | None = None
    topic: TopicSummary
    scene_plan_ids: list[int]
    video_ids: list[int]


class ScriptReviewRequest(BaseModel):
    reason: str | None = None


class AssetResponse(BaseModel):
    id: int
    asset_type: str
    scene_index: int | None
    s3_key: str
    duration_sec: float | None
    verified: bool
    preview_url: str


class ScenePlanResponse(BaseModel):
    id: int
    script_id: int
    scene_count: int
    total_duration_sec: float | None
    created_at: datetime


class ScenePlanDetailResponse(ScenePlanResponse):
    scenes: list[dict]
    assets: list[AssetResponse]


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
    channel_id: int | None
    platform: str
    external_id: str | None
    status: str
    scheduled_at: datetime | None
    published_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VideoSummary(BaseModel):
    id: int
    script_id: int
    duration_sec: float | None
    qa_status: str


class PublicationDetailResponse(PublicationResponse):
    platform_url: str | None = None
    video_summary: VideoSummary | None = None


class AnalyticsSummary(BaseModel):
    total_views: int
    avg_retention: float
    publications: int
    top_categories: list[dict]


class RankedItem(BaseModel):
    id: int
    label: str
    category: str | None = None
    views: int
    avg_retention: float
    avg_ctr: float
    score: float


class CategoryPerformance(BaseModel):
    category: str
    avg_score: float
    samples: int
