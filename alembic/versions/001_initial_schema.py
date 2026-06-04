"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("voice_id", sa.String(length=255), nullable=True),
        sa.Column("style_config", sa.JSON(), nullable=True),
        sa.Column("platform_credentials_ref", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED", "DEAD_LETTER", name="jobstatus"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_celery_task_id", "jobs", ["celery_task_id"])
    op.create_table(
        "optimization_weights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dimension", sa.String(length=100), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("emotion", sa.String(length=100), nullable=True),
        sa.Column("emotional_score", sa.Float(), nullable=True),
        sa.Column("virality_score", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scripts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("hook", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("ending", sa.Text(), nullable=False),
        sa.Column("cta", sa.Text(), nullable=False),
        sa.Column("estimated_duration_sec", sa.Float(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("status", sa.Enum("PENDING_REVIEW", "APPROVED", "REJECTED", name="scriptstatus"), nullable=False),
        sa.Column("hook_variant", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scene_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("scenes", sa.JSON(), nullable=False),
        sa.Column("total_duration_sec", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("s3_key", sa.String(length=512), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("qa_status", sa.Enum("PENDING", "PASSED", "FAILED", name="qastatus"), nullable=False),
        sa.Column("qa_details", sa.JSON(), nullable=True),
        sa.Column("publish_status", sa.Enum("DRAFT", "SCHEDULED", "PUBLISHED", "FAILED", name="publishstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scene_plan_id", sa.Integer(), nullable=False),
        sa.Column("asset_type", sa.Enum("VOICE", "VISUAL", "SUBTITLE", name="assettype"), nullable=False),
        sa.Column("s3_key", sa.String(length=512), nullable=False),
        sa.Column("scene_index", sa.Integer(), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("timing_metadata", sa.JSON(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["scene_plan_id"], ["scene_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "publications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=True),
        sa.Column("platform", sa.Enum("YOUTUBE", "TIKTOK", "INSTAGRAM", name="platform"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("DRAFT", "SCHEDULED", "PUBLISHED", "FAILED", name="publishstatus", create_type=False), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"]),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("publication_id", sa.Integer(), nullable=False),
        sa.Column("views", sa.Integer(), nullable=True),
        sa.Column("avg_view_duration_sec", sa.Float(), nullable=True),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("comments", sa.Integer(), nullable=True),
        sa.Column("shares", sa.Integer(), nullable=True),
        sa.Column("retention_rate", sa.Float(), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["publication_id"], ["publications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("analytics_events")
    op.drop_table("publications")
    op.drop_table("assets")
    op.drop_table("videos")
    op.drop_table("scene_plans")
    op.drop_table("scripts")
    op.drop_table("topics")
    op.drop_table("optimization_weights")
    op.drop_index("ix_jobs_celery_task_id", "jobs")
    op.drop_table("jobs")
    op.drop_table("channels")
    sa.Enum(name="jobstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="scriptstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="qastatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="publishstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="assettype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="platform").drop(op.get_bind(), checkfirst=True)
