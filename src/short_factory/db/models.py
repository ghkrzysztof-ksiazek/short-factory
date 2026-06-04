import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class JobStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class ScriptStatus(enum.StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class QAStatus(enum.StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class PublishStatus(enum.StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class AssetType(enum.StrEnum):
    VOICE = "voice"
    VISUAL = "visual"
    SUBTITLE = "subtitle"


class Platform(enum.StrEnum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    voice_id: Mapped[str | None] = mapped_column(String(255))
    style_config: Mapped[dict | None] = mapped_column(JSON)
    platform_credentials_ref: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    publications: Mapped[list["Publication"]] = relationship(back_populates="channel")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), index=True)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.PENDING)
    payload: Mapped[dict | None] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    emotion: Mapped[str | None] = mapped_column(String(100))
    emotional_score: Mapped[float | None] = mapped_column(Float)
    virality_score: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scripts: Mapped[list["Script"]] = relationship(back_populates="topic")


class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False)
    hook: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    ending: Mapped[str] = mapped_column(Text, nullable=False)
    cta: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_duration_sec: Mapped[float | None] = mapped_column(Float)
    quality_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[ScriptStatus] = mapped_column(Enum(ScriptStatus), default=ScriptStatus.PENDING_REVIEW)
    hook_variant: Mapped[int] = mapped_column(Integer, default=1)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    topic: Mapped["Topic"] = relationship(back_populates="scripts")
    scene_plans: Mapped[list["ScenePlan"]] = relationship(back_populates="script")
    videos: Mapped[list["Video"]] = relationship(back_populates="script")


class ScenePlan(Base):
    __tablename__ = "scene_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id"), nullable=False)
    scenes: Mapped[list] = mapped_column(JSON, nullable=False)
    total_duration_sec: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    script: Mapped["Script"] = relationship(back_populates="scene_plans")
    assets: Mapped[list["Asset"]] = relationship(back_populates="scene_plan")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scene_plan_id: Mapped[int] = mapped_column(ForeignKey("scene_plans.id"), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    scene_index: Mapped[int | None] = mapped_column(Integer)
    duration_sec: Mapped[float | None] = mapped_column(Float)
    timing_metadata: Mapped[dict | None] = mapped_column(JSON)
    verified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scene_plan: Mapped["ScenePlan"] = relationship(back_populates="assets")


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id"), nullable=False)
    s3_key: Mapped[str | None] = mapped_column(String(512))
    duration_sec: Mapped[float | None] = mapped_column(Float)
    qa_status: Mapped[QAStatus] = mapped_column(Enum(QAStatus), default=QAStatus.PENDING)
    qa_details: Mapped[dict | None] = mapped_column(JSON)
    publish_status: Mapped[PublishStatus] = mapped_column(Enum(PublishStatus), default=PublishStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    script: Mapped["Script"] = relationship(back_populates="videos")
    publications: Mapped[list["Publication"]] = relationship(back_populates="video")


class Publication(Base):
    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), nullable=False)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"))
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[PublishStatus] = mapped_column(Enum(PublishStatus), default=PublishStatus.DRAFT)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    video: Mapped["Video"] = relationship(back_populates="publications")
    channel: Mapped["Channel | None"] = relationship(back_populates="publications")
    analytics_events: Mapped[list["AnalyticsEvent"]] = relationship(back_populates="publication")


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    publication_id: Mapped[int] = mapped_column(ForeignKey("publications.id"), nullable=False)
    views: Mapped[int | None] = mapped_column(Integer)
    avg_view_duration_sec: Mapped[float | None] = mapped_column(Float)
    ctr: Mapped[float | None] = mapped_column(Float)
    comments: Mapped[int | None] = mapped_column(Integer)
    shares: Mapped[int | None] = mapped_column(Integer)
    retention_rate: Mapped[float | None] = mapped_column(Float)
    raw_data: Mapped[dict | None] = mapped_column(JSON)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    publication: Mapped["Publication"] = relationship(back_populates="analytics_events")


class OptimizationWeight(Base):
    __tablename__ = "optimization_weights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dimension: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
