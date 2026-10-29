"""Fast, low-token vision analysis for uploaded field reports."""
import base64
import hashlib
import io
import logging
import time

import httpx
from PIL import Image, ImageOps

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_http = httpx.AsyncClient(timeout=httpx.Timeout(35.0, connect=5.0), limits=httpx.Limits(max_connections=10, max_keepalive_connections=5))
_analysis_cache: dict[str, tuple[float, str]] = {}
_CACHE_SECONDS = 300

REPORT_PROMPT = """حلل صورة التقرير الميداني بالعربية باحتراف.
أخرج النتيجة بهذا الترتيب:
1) حالة القراءة: واضح / واضح جزئياً / غير واضح.
2) البيانات المؤكدة الظاهرة: أرقام مهام، أرقام اشتراكات، تواريخ، حالات، وإجماليات فقط.
3) ملاحظات التحقق: أي تعارض أو نقص أو رقم غير مقروء.
4) توصية قصيرة لتحسين التقرير.
لا تخمّن أي رقم غير ظاهر، واكتب (غير مقروء) بدلاً منه. اجعل الإجابة مختصرة."""


def _prepare_image(image: bytes, mime: str) -> tuple[bytes, str]:
    """Reduce pixel/token cost while preserving text readability."""
    try:
        with Image.open(io.BytesIO(image)) as source:
            prepared = ImageOps.exif_transpose(source).convert("RGB")
            prepared.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            prepared.save(output, format="JPEG", quality=76, optimize=True)
            result = output.getvalue()
            if len(result) < len(image):
                return result, "image/jpeg"
    except Exception:
        logger.warning("Could not optimize report image", exc_info=True)
    return image, mime


async def analyze_report(image: bytes, mime: str) -> str:
    settings = get_settings()
    if not settings.ai_enabled or not settings.ai_api_key:
        raise RuntimeError("تحليل الصور غير مفعّل. أضف إعدادات AI في الخادم.")
    cache_key = hashlib.sha256(image).hexdigest()
    cached = _analysis_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] <= _CACHE_SECONDS:
        return cached[1]
    optimized, optimized_mime = _prepare_image(image, mime)
    data_url = f"data:{optimized_mime};base64,{base64.b64encode(optimized).decode('ascii')}"
    payload = {"model": settings.ai_model, "messages": [{"role": "system", "content": REPORT_PROMPT}, {"role": "user", "content": [{"type": "text", "text": "حلل التقرير بدقة وباختصار."}, {"type": "image_url", "image_url": {"url": data_url}}]}], "temperature": 0.05, "max_tokens": 420}
    try:
        response = await _http.post(f"{settings.ai_base_url.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {settings.ai_api_key}"}, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        answer = str(content).strip() or "لم ينتج التحليل نصًا مفيدًا."
        if len(_analysis_cache) >= 100:
            _analysis_cache.pop(next(iter(_analysis_cache)))
        _analysis_cache[cache_key] = (time.monotonic(), answer)
        return answer
    except httpx.HTTPStatusError as exc:
        logger.error("Report analysis failed: status=%s body=%s", exc.response.status_code, exc.response.text[:2000])
        raise RuntimeError("تعذر تحليل صورة التقرير حاليًا.") from exc
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        logger.exception("Report analysis response could not be processed")
        raise RuntimeError("تعذر تحليل صورة التقرير حاليًا.") from exc
