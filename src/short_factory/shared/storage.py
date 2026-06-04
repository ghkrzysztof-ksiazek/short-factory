import io
from pathlib import Path

import boto3
from botocore.client import Config

from short_factory.config.settings import settings


class StorageClient:
    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = settings.s3_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except Exception:
                pass

    def upload_file(self, local_path: str | Path, s3_key: str) -> str:
        self.client.upload_file(str(local_path), self.bucket, s3_key)
        return s3_key

    def upload_bytes(self, data: bytes, s3_key: str, content_type: str = "application/octet-stream") -> str:
        self.client.upload_fileobj(io.BytesIO(data), self.bucket, s3_key, ExtraArgs={"ContentType": content_type})
        return s3_key

    def download_file(self, s3_key: str, local_path: str | Path) -> Path:
        path = Path(local_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, s3_key, str(path))
        return path

    def exists(self, s3_key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except Exception:
            return False

    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": s3_key},
            ExpiresIn=expires_in,
        )


storage = StorageClient()
