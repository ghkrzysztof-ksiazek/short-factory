from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from short_factory.db.models import Asset, Video
from short_factory.db.session import get_db
from short_factory.shared.storage import content_type_from_extension, storage

router = APIRouter(prefix="/media", tags=["media"])


def _streaming_response(s3_key: str, *, attachment: bool = False, filename: str | None = None) -> StreamingResponse:
    if not storage.exists(s3_key):
        raise HTTPException(status_code=404, detail="File not found")

    headers: dict[str, str] = {}
    if attachment:
        name = filename or Path(s3_key).name
        headers["Content-Disposition"] = f'attachment; filename="{name}"'

    return StreamingResponse(
        storage.stream_object(s3_key),
        media_type=content_type_from_extension(s3_key),
        headers=headers,
    )


@router.get("/asset/{asset_id}")
def stream_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _streaming_response(asset.s3_key)


@router.get("/asset/{asset_id}/download")
def download_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _streaming_response(asset.s3_key, attachment=True, filename=Path(asset.s3_key).name)


@router.get("/video/{video_id}")
def stream_video(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video or not video.s3_key:
        raise HTTPException(status_code=404, detail="Video not found")
    return _streaming_response(video.s3_key)


@router.get("/video/{video_id}/download")
def download_video(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video or not video.s3_key:
        raise HTTPException(status_code=404, detail="Video not found")
    filename = Path(video.s3_key).name or f"video_{video_id}.mp4"
    return _streaming_response(video.s3_key, attachment=True, filename=filename)
