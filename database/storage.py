"""Supabase Storage gateway for daily-report images.

Only an object URL/key is persisted in PostgreSQL.  The implementation uses
Supabase's REST Storage API directly, keeping the application dependency set
small and making failures explicit to the caller.
"""

from __future__ import annotations

import hashlib
import mimetypes
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

class StorageConfigurationError(RuntimeError):
    """Raised when the required Supabase storage secrets are not configured."""


class StorageOperationError(RuntimeError):
    """Raised when Supabase rejects an upload, download, or deletion request."""


class ReportImageNotFoundError(StorageOperationError):
    """Raised when the requested report image does not exist in Storage."""


def validate_report_image(image_bytes: bytes, image_mime: str) -> bool:
    """Validate actual JPEG/PNG signatures, not only a client filename/MIME."""
    is_jpeg = image_bytes.startswith(b"\xff\xd8\xff")
    is_png = image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    return (image_mime in {"image/jpeg", "image/png"} or not image_mime) and (is_jpeg or is_png)


def _settings() -> tuple[str, str, str]:
    import streamlit as st

    try:
        base_url = st.secrets["SUPABASE_URL"].rstrip("/")
        service_key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
        bucket = st.secrets["SUPABASE_STORAGE_BUCKET"]
    except (KeyError, AttributeError) as exc:
        raise StorageConfigurationError(
            "Supabase Storage is not configured. Add SUPABASE_URL, "
            "SUPABASE_SERVICE_ROLE_KEY and SUPABASE_STORAGE_BUCKET to secrets."
        ) from exc
    return base_url, service_key, bucket


def _request(url: str, method: str, headers: dict[str, str], data: bytes | None = None) -> bytes:
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:  # nosec B310 - endpoint comes from trusted secrets
            return response.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise StorageOperationError(
        f"HTTP {exc.code}: {body}"
        from exc
    except (URLError, TimeoutError) as exc:
        raise StorageOperationError("Supabase Storage request failed.") from exc


def upload_report_image(technician: str, report_date: object, image_bytes: bytes, image_mime: str) -> str:
    """Upload an image and return its stable object key (not a signed URL)."""
    base_url, service_key, bucket = _settings()
    extension = mimetypes.guess_extension(image_mime or "") or ".jpg"
    digest = hashlib.sha256(image_bytes).hexdigest()[:16]
    safe_technician = quote(str(technician).strip(), safe="")
    object_key = f"daily-reports/{safe_technician}/{report_date}-{digest}{extension}"
    encoded_key = quote(object_key, safe="/")
    _request(
        f"{base_url}/storage/v1/object/{quote(bucket, safe='')}/{encoded_key}",
        "POST",
        {
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": image_mime or "image/jpeg",
            "x-upsert": "false",
        },
        image_bytes,
    )
    return object_key


def report_image_url(object_key: str) -> str:
    """Return the public URL for a stored report object."""
    base_url, _, bucket = _settings()
    return f"{base_url}/storage/v1/object/public/{quote(bucket, safe='')}/{quote(object_key, safe='/')}"


def download_report_image(object_key: str) -> bytes:
    """Download the original object using the service credential.

    This works for both public and private buckets and avoids relying on the
    browser-visible public URL when preparing the Streamlit download button.
    """
    if not object_key:
        raise ReportImageNotFoundError("No report image key was provided.")
    base_url, service_key, bucket = _settings()
    encoded_key = quote(object_key, safe="/")
    return _request(
        f"{base_url}/storage/v1/object/{quote(bucket, safe='')}/{encoded_key}",
        "GET",
        {"Authorization": f"Bearer {service_key}", "apikey": service_key},
    )


def delete_report_image(object_key: str | None) -> None:
    if not object_key:
        return
    base_url, service_key, bucket = _settings()
    encoded_key = quote(object_key, safe="/")
    _request(
        f"{base_url}/storage/v1/object/{quote(bucket, safe='')}/{encoded_key}",
        "DELETE",
        {"Authorization": f"Bearer {service_key}", "apikey": service_key},
    )
