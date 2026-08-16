"""Validated report storage using R2 in production and the filesystem locally."""
import hashlib
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import boto3
from fastapi import UploadFile
from app.core.config import get_settings

settings = get_settings()


def _r2_client():
    return boto3.client(
        "s3", endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )

async def save_report_image(technician_id: int, report_date: str, file: UploadFile) -> tuple[str, str]:
    content = await file.read()
    if len(content) > settings.max_upload_bytes: raise ValueError("حجم الصورة يتجاوز الحد المسموح")
    mime = file.content_type or ""
    if mime not in {"image/jpeg", "image/png"} or not (content.startswith(b"\xff\xd8\xff") or content.startswith(b"\x89PNG\r\n\x1a\n")):
        raise ValueError("يجب رفع صورة JPEG أو PNG صالحة")
    extension = "jpg" if mime == "image/jpeg" else "png"
    digest = hashlib.sha256(content).hexdigest()[:16]
    key = f"daily-reports/{technician_id}/{report_date}-{digest}-{uuid4().hex[:8]}.{extension}"
    if settings.uses_r2_storage:
        _r2_client().put_object(Bucket=settings.r2_bucket, Key=key, Body=content, ContentType=mime)
    else:
        path = Path(settings.uploads_dir) / key
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content)
    return key, mime

def report_path(key: str) -> Path:
    candidate = (Path(settings.uploads_dir) / key).resolve()
    root = Path(settings.uploads_dir).resolve()
    if root not in candidate.parents: raise FileNotFoundError
    return candidate


def report_bytes(key: str) -> bytes:
    """Read a report without exposing the object-store credentials or bucket publicly."""
    if settings.uses_r2_storage:
        try:
            return _r2_client().get_object(Bucket=settings.r2_bucket, Key=key)["Body"].read()
        except Exception as exc:
            raise FileNotFoundError from exc
    return report_path(key).read_bytes()
