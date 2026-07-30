"""Local development report storage boundary; replace implementation with Supabase/S3 in production."""
import hashlib
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile
from app.core.config import get_settings

settings = get_settings()

async def save_report_image(technician_id: int, report_date: str, file: UploadFile) -> tuple[str, str]:
    content = await file.read()
    if len(content) > settings.max_upload_bytes: raise ValueError("حجم الصورة يتجاوز الحد المسموح")
    mime = file.content_type or ""
    if mime not in {"image/jpeg", "image/png"} or not (content.startswith(b"\xff\xd8\xff") or content.startswith(b"\x89PNG\r\n\x1a\n")):
        raise ValueError("يجب رفع صورة JPEG أو PNG صالحة")
    extension = "jpg" if mime == "image/jpeg" else "png"
    digest = hashlib.sha256(content).hexdigest()[:16]
    key = f"daily-reports/{technician_id}/{report_date}-{digest}-{uuid4().hex[:8]}.{extension}"
    path = Path(settings.uploads_dir) / key
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content)
    return key, mime

def report_path(key: str) -> Path:
    candidate = (Path(settings.uploads_dir) / key).resolve()
    root = Path(settings.uploads_dir).resolve()
    if root not in candidate.parents: raise FileNotFoundError
    return candidate
