from abc import ABC, abstractmethod
from datetime import UTC, datetime

from short_factory.config.logging import get_logger
from short_factory.db.models import Platform, Publication, PublishStatus, Video
from short_factory.db.session import SessionLocal

logger = get_logger(__name__)


class Publisher(ABC):
    platform: Platform

    @abstractmethod
    def publish(
        self, video: Video, title: str, description: str, scheduled_at: datetime | None = None
    ) -> str:
        pass


class YouTubePublisher(Publisher):
    platform = Platform.YOUTUBE

    def publish(
        self, video: Video, title: str, description: str, scheduled_at: datetime | None = None
    ) -> str:
        from short_factory.config.settings import settings
        from short_factory.shared.storage import storage

        if not settings.youtube_refresh_token:
            logger.warning("youtube_not_configured", action="stub_publish")
            return f"stub_youtube_{video.id}"

        if not settings.youtube_client_id or not settings.youtube_client_secret:
            raise NotConfiguredError(
                "YouTube OAuth client_id and client_secret must be configured for uploads."
            )

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds = Credentials(
            token=None,
            refresh_token=settings.youtube_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.youtube_client_id,
            client_secret=settings.youtube_client_secret,
        )
        youtube = build("youtube", "v3", credentials=creds)

        local_path = f"/tmp/upload_{video.id}.mp4"
        storage.download_file(video.s3_key, local_path)

        privacy = "private" if scheduled_at else "public"
        body = {
            "snippet": {"title": title, "description": description, "categoryId": "22"},
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
                "publishAt": scheduled_at.isoformat() if scheduled_at else None,
            },
        }
        if not scheduled_at:
            body["status"].pop("publishAt", None)

        media = MediaFileUpload(local_path, mimetype="video/mp4", resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        return response["id"]


class TikTokPublisher(Publisher):
    platform = Platform.TIKTOK

    def publish(
        self, video: Video, title: str, description: str, scheduled_at: datetime | None = None
    ) -> str:
        raise NotConfiguredError("TikTok publisher not configured. Add TikTok API credentials.")


class InstagramPublisher(Publisher):
    platform = Platform.INSTAGRAM

    def publish(
        self, video: Video, title: str, description: str, scheduled_at: datetime | None = None
    ) -> str:
        raise NotConfiguredError(
            "Instagram publisher not configured. Add Instagram API credentials."
        )


class NotConfiguredError(Exception):
    pass


PUBLISHERS: dict[Platform, Publisher] = {
    Platform.YOUTUBE: YouTubePublisher(),
    Platform.TIKTOK: TikTokPublisher(),
    Platform.INSTAGRAM: InstagramPublisher(),
}


def publish_video(
    video_id: int,
    platform: Platform = Platform.YOUTUBE,
    channel_id: int | None = None,
    scheduled_at: datetime | None = None,
) -> int:
    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        script = video.script
        title = script.hook[:100] if script else f"Short #{video_id}"
        description = f"{script.body}\n\n{script.cta}" if script else ""

        now = datetime.now(UTC)
        if scheduled_at and scheduled_at > now:
            publication = Publication(
                video_id=video_id,
                channel_id=channel_id,
                platform=platform,
                scheduled_at=scheduled_at,
                status=PublishStatus.SCHEDULED,
            )
            db.add(publication)
            video.publish_status = PublishStatus.SCHEDULED
            db.commit()
            db.refresh(publication)

            from short_factory.workers.tasks import run_scheduled_publish

            run_scheduled_publish.apply_async(args=[publication.id], eta=scheduled_at)
            return publication.id

        publisher = PUBLISHERS[platform]
        try:
            external_id = publisher.publish(video, title, description, scheduled_at)
            status = PublishStatus.PUBLISHED
        except NotConfiguredError as exc:
            logger.warning("publisher_not_configured", platform=platform.value, error=str(exc))
            external_id = f"stub_{platform.value}_{video_id}"
            status = PublishStatus.DRAFT

        publication = Publication(
            video_id=video_id,
            channel_id=channel_id,
            platform=platform,
            external_id=external_id,
            scheduled_at=scheduled_at,
            published_at=datetime.now(UTC) if status == PublishStatus.PUBLISHED else None,
            status=status,
        )
        db.add(publication)
        video.publish_status = status
        db.commit()
        db.refresh(publication)
        return publication.id
    finally:
        db.close()


def execute_scheduled_publication(publication_id: int) -> dict:
    db = SessionLocal()
    try:
        publication = db.get(Publication, publication_id)
        if not publication:
            raise ValueError(f"Publication {publication_id} not found")
        if publication.status != PublishStatus.SCHEDULED:
            return {"publication_id": publication_id, "skipped": True, "reason": publication.status.value}

        video = publication.video
        script = video.script if video else None
        title = script.hook[:100] if script else f"Short #{video.id}"
        description = f"{script.body}\n\n{script.cta}" if script else ""

        publisher = PUBLISHERS[publication.platform]
        external_id = publisher.publish(video, title, description, publication.scheduled_at)
        publication.external_id = external_id
        publication.status = PublishStatus.PUBLISHED
        publication.published_at = datetime.now(UTC)
        if video:
            video.publish_status = PublishStatus.PUBLISHED
        db.commit()
        return {"publication_id": publication_id, "external_id": external_id}
    finally:
        db.close()


def enqueue_due_publications() -> dict:
    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        due = (
            db.query(Publication)
            .filter(Publication.status == PublishStatus.SCHEDULED, Publication.scheduled_at <= now)
            .all()
        )
        from short_factory.workers.tasks import run_scheduled_publish

        queued = []
        for pub in due:
            run_scheduled_publish.delay(pub.id)
            queued.append(pub.id)
        return {"queued": len(queued), "publication_ids": queued}
    finally:
        db.close()
