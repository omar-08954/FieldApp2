"""Supabase Storage gateway for daily-report images.

Only an object URL/key is persisted in PostgreSQL.  The implementation uses
Supabase's REST Storage API directly, keeping the application dependency set
small and making failures explicit to the caller.

Object Key Strategy
-------------------
Supabase Storage rejects any key that contains non-ASCII characters (Arabic,
Chinese, etc.) or special characters such as spaces, parentheses, and most
punctuation.  The only safe characters are:

    A-Z  a-z  0-9  -  _  .  /

For this reason the object key is **never** derived from the technician's
display name.  Instead it is built exclusively from:

    daily-reports/{technician_id}/{date}-{sha256_digest[:16]}.{ext}

where ``technician_id`` is the numeric database ID of the user row — an
integer that is always ASCII, unique, stable, and language-independent.

All four storage operations (upload, download, replace, delete) share the
single ``_build_object_key`` helper so the key is always constructed
identically regardless of the call site.
"""

from __future__ import annotations

import hashlib
import mimetypes
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from logging_config import get_logger

LOGGER = get_logger(__name__)

# Characters that are safe for every segment of a Supabase Storage object key.
# Anything outside this set is stripped (not encoded) so the key stays clean.
_SAFE_SEGMENT_RE = re.compile(r"[^A-Za-z0-9\-_]")


class StorageConfigurationError(RuntimeError):
    """Raised when the required Supabase storage secrets are not configured."""


class StorageOperationError(RuntimeError):
    """Raised when Supabase rejects an upload, download, or deletion request."""


class ReportImageNotFoundError(StorageOperationError):
    """Raised when the requested report image does not exist in Storage."""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def validate_report_image(image_bytes: bytes, image_mime: str) -> bool:
    """Validate actual JPEG/PNG signatures, not only a client filename/MIME."""
    is_jpeg = image_bytes.startswith(b"\xff\xd8\xff")
    is_png = image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    return (image_mime in {"image/jpeg", "image/png"} or not image_mime) and (is_jpeg or is_png)


def build_object_key(technician_id: int | str, report_date: object, image_bytes: bytes, image_mime: str) -> str:
    """Return a Supabase-safe object key for a daily-report image.

    The key format is::

        daily-reports/{technician_id}/{date}-{sha256[:16]}.{ext}

    ``technician_id`` is the numeric database ID of the user — always ASCII,
    unique, and completely independent of the technician's display name or
    language.  This is the **only** correct way to build the key; callers
    must never pass a display name here.

    Parameters
    ----------
    technician_id:
        The integer primary key from the ``users`` table.
    report_date:
        Any value accepted by ``str()`` that produces an ISO-8601 date string
        (e.g. ``datetime.date`` objects, ``"2026-07-20"``).
    image_bytes:
        The raw image bytes; used to derive the content-addressed digest.
    image_mime:
        MIME type string (``"image/jpeg"`` or ``"image/png"``).
    """
    # Sanitise the technician_id segment: keep only safe ASCII characters.
    safe_id = _SAFE_SEGMENT_RE.sub("", str(technician_id))
    if not safe_id:
        # Fallback: use a generic placeholder rather than an empty segment.
        safe_id = "unknown"

    # Sanitise the date segment.
    safe_date = _SAFE_SEGMENT_RE.sub("", str(report_date))
    if not safe_date:
        safe_date = "nodate"

    # Content-addressed digest makes the key idempotent for the same bytes.
    digest = hashlib.sha256(image_bytes).hexdigest()[:16]

    # Derive extension from MIME type; default to .jpg for unknown types.
    extension = mimetypes.guess_extension(image_mime or "") or ".jpg"
    # mimetypes sometimes returns ".jpe" for JPEG — normalise it.
    if extension in {".jpe", ".jpeg"}:
        extension = ".jpg"

    return f"daily-reports/{safe_id}/{safe_date}-{digest}{extension}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
        # Supabase always sends a JSON body describing the real reason for a
        # failed request (e.g. "Duplicate", "InvalidKey", "Bucket not
        # found", "InvalidJWT" ...). urllib does not expose this body via
        # str(exc), so without reading it explicitly the original cause is
        # completely lost and only a bare HTTP status code remains. Read and
        # log it in full here so the true cause is always available, even
        # though the Streamlit UI intentionally keeps showing a generic,
        # user-friendly message.
        try:
            detail = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:  # pragma: no cover - body already consumed/unavailable
            detail = ""
        LOGGER.error(
            "Supabase Storage request failed: %s %s -> HTTP %s. Supabase response: %s",
            method,
            url,
            exc.code,
            detail or "<no response body>",
        )
        if exc.code == 404:
            raise ReportImageNotFoundError("Report image was not found in Supabase Storage.") from exc
        message = f"Supabase Storage request failed with HTTP {exc.code}."
        if detail:
            message = f"{message} Supabase response: {detail}"
        raise StorageOperationError(message) from exc
    except (URLError, TimeoutError) as exc:
        LOGGER.error("Supabase Storage request failed: %s %s -> %s", method, url, exc)
        raise StorageOperationError(f"Supabase Storage request failed: {exc}") from exc


def _object_url(base_url: str, bucket: str, object_key: str) -> str:
    """Build the Supabase Storage REST URL for an object key.

    ``object_key`` must always be the raw, human-readable key exactly as
    returned by ``upload_report_image`` and stored in PostgreSQL — it is
    percent-encoded exactly once, here, and nowhere else.  This single
    encoding point is shared by upload, download, delete, and public URL
    helpers so the same key always resolves to the exact same Supabase object.
    """
    return f"{base_url}/storage/v1/object/{quote(bucket, safe='')}/{quote(object_key, safe='/')}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def upload_report_image(
    technician_id: int | str,
    report_date: object,
    image_bytes: bytes,
    image_mime: str,
) -> str:
    """Upload an image and return its stable object key (not a signed URL).

    Parameters
    ----------
    technician_id:
        The integer primary key from the ``users`` table.  **Never** pass the
        technician's display name here — it may contain Arabic or other
        non-ASCII characters that Supabase Storage rejects as an InvalidKey.
    report_date:
        ISO-8601 date string or ``datetime.date`` object.
    image_bytes:
        Raw image bytes.
    image_mime:
        MIME type (``"image/jpeg"`` or ``"image/png"``).

    Returns
    -------
    str
        The stable object key to be stored in ``daily_reports.image_url``.
    """
    base_url, service_key, bucket = _settings()
    object_key = build_object_key(technician_id, report_date, image_bytes, image_mime)
    _request(
        _object_url(base_url, bucket, object_key),
        "POST",
        {
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": image_mime or "image/jpeg",
            # The object key embeds a sha256 digest of the exact bytes being
            # uploaded, so two different requests can only ever collide on
            # the same key when they carry byte-identical content (e.g. the
            # same photo re-uploaded, or a retry after a dropped response).
            # Rejecting that re-upload with "already exists" (x-upsert:
            # false) is what previously surfaced as HTTP 400 on a plain
            # re-save. Since a same-key request is always the same file,
            # allowing the upsert is safe and makes the upload idempotent.
            "x-upsert": "true",
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
    return _request(
        _object_url(base_url, bucket, object_key),
        "GET",
        {"Authorization": f"Bearer {service_key}", "apikey": service_key},
    )


def delete_report_image(object_key: str | None) -> None:
    """Delete a stored report image.  Silently returns when ``object_key`` is
    empty or ``None`` (nothing to delete)."""
    if not object_key:
        return
    base_url, service_key, bucket = _settings()
    _request(
        _object_url(base_url, bucket, object_key),
        "DELETE",
        {"Authorization": f"Bearer {service_key}", "apikey": service_key},
    )
