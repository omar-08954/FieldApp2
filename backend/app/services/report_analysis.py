"""Optional server-side vision analysis for uploaded field reports."""
import base64
import logging
import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def analyze_report(image: bytes, mime: str) -> str:
    settings = get_settings()
    if not settings.ai_enabled or not settings.ai_api_key:
        raise RuntimeError("تحليل الصور غير مفعّل. أضف إعدادات AI في الخادم.")
    data_url = f"data:{mime};base64,{base64.b64encode(image).decode('ascii')}"
    payload = {
        "model": settings.ai_model,
        "messages": [{"role": "system", "content": "حلل صورة تقرير ميداني بالعربية. اذكر بوضوح هل الصورة مقروءة، وما المعلومات الظاهرة، وأي نقص أو مشكلة في جودة التقرير. لا تخترع بيانات غير ظاهرة."}, {"role": "user", "content": [{"type": "text", "text": "حلل هذا التقرير الميداني باختصار."}, {"type": "image_url", "image_url": {"url": data_url}}]}],
        "temperature": 0.1,
    }
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(f"{settings.ai_base_url.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {settings.ai_api_key}"}, json=payload)
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return str(content).strip() or "لم ينتج التحليل نصًا مفيدًا."
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        logger.exception("Report image analysis failed")
        raise RuntimeError("تعذر تحليل صورة التقرير حاليًا.") from exc
