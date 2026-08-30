"""Validated report storage using Supabase Storage in production and the filesystem locally."""
import hashlib
from pathlib import Path
from uuid import uuid4
from urllib.parse import quote
import httpx
from fastapi import UploadFile
from app.core.config import get_settings

settings = get_settings()


def _storage_url(key: str) -> str:
    base = settings.supabase_url.rstrip("/")
    bucket = quote(settings.supabase_reports_bucket, safe="")
    return f"{base}/storage/v1/object/{bucket}/{quote(key, safe='/')}"


def _storage_headers(content_type: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers

async def save_report_image(technician_id: int, report_date: str, file: UploadFile) -> tuple[str, str]:
    content = await file.read()
    if len(content) > settings.max_upload_bytes: raise ValueError("حجم الصورة يتجاوز الحد المسموح")
    mime = file.content_type or ""
    if mime not in {"image/jpeg", "image/png"} or not (content.startswith(b"\xff\xd8\xff") or content.startswith(b"\x89PNG\r\n\x1a\n")):
        raise ValueError("يجب رفع صورة JPEG أو PNG صالحة")
    extension = "jpg" if mime == "image/jpeg" else "png"
    digest = hashlib.sha256(content).hexdigest()[:16]
    key = f"daily-reports/{technician_id}/{report_date}-{digest}-{uuid4().hex[:8]}.{extension}"
    if settings.uses_supabase_storage:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(_storage_url(key), content=content, headers={**_storage_headers(mime), "x-upsert": "true"})
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"تعذر حفظ الصورة في التخزين السحابي (HTTP {exc.response.status_code}). تأكد من اسم bucket وصلاحيات مفتاح Supabase.") from exc
        except httpx.RequestError as exc:
            raise ValueError("تعذر الوصول إلى تخزين التقارير. تحقق من اتصال API بخدمة Supabase.") from exc
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
    if settings.uses_supabase_storage:
        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(_storage_url(key), headers=_storage_headers())
            response.raise_for_status()
            return response.content
        except Exception as exc:
            raise FileNotFoundError from exc
    return report_path(key).read_bytes()
