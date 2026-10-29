"""Fast, low-token server-side assistant for FieldApp."""
import json
import logging
import time

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Task

logger = logging.getLogger(__name__)
settings = get_settings()
_http = httpx.AsyncClient(timeout=httpx.Timeout(18.0, connect=5.0), limits=httpx.Limits(max_connections=20, max_keepalive_connections=10))
_answer_cache: dict[str, tuple[float, str]] = {}
_CACHE_SECONDS = 20

SYSTEM_PROMPT = """أنت مساعد FieldApp التشغيلي.
أجب بالعربية المهنية وباختصار، اعتماداً على بيانات السياق فقط.
لا تخترع أرقاماً أو صلاحيات أو أسماء. إذا لم توجد بيانات كافية فاذكر ذلك.
رتّب الإجابة في نقاط قصيرة عند الحاجة، واذكر النسبة أو الفرق فقط إذا أمكن حسابه من السياق."""


def _metrics(db: Session) -> dict:
    total = int(db.scalar(select(func.count()).select_from(Task)) or 0)
    subscriptions = int(db.scalar(select(func.count(func.distinct(Task.subscription_number))).where(Task.subscription_number.is_not(None), Task.subscription_number != "غير مسجل")) or 0)
    by_status = db.execute(select(Task.task_status, func.count()).group_by(Task.task_status).order_by(Task.task_status)).all()
    return {"إجمالي المهام": total, "الاشتراكات الفريدة": subscriptions, "المهام حسب الحالة": {str(status): int(count) for status, count in by_status}}


def _quick_answer(question: str, metrics: dict) -> str | None:
    q = question.strip().lower()
    if any(p in q for p in ("عدد المهام", "إجمالي المهام", "المهام الموجودة", "كم مهمة")):
        return f"عدد المهام الموجودة في قاعدة بيانات التطبيق هو {metrics['إجمالي المهام']} مهمة."
    if any(p in q for p in ("عدد الاشتراكات", "إجمالي الاشتراكات", "كم اشتراك")):
        return f"عدد الاشتراكات الفريدة المسجلة هو {metrics['الاشتراكات الفريدة']} اشتراك."
    if any(p in q for p in ("حالات المهام", "توزيع المهام", "المهام حسب الحالة")):
        distribution = metrics["المهام حسب الحالة"]
        if not distribution:
            return "لا توجد مهام مسجلة في قاعدة البيانات."
        return "توزيع المهام حسب الحالة: " + "، ".join(f"{status}: {count}" for status, count in distribution.items()) + "."
    return None


def _cache_get(key: str) -> str | None:
    item = _answer_cache.get(key)
    if not item:
        return None
    if time.monotonic() - item[0] > _CACHE_SECONDS:
        _answer_cache.pop(key, None)
        return None
    return item[1]


def _cache_put(key: str, answer: str) -> None:
    if len(_answer_cache) >= 200:
        _answer_cache.pop(next(iter(_answer_cache)))
    _answer_cache[key] = (time.monotonic(), answer)


async def ask(db: Session, question: str) -> str:
    question = question.strip()[:1200]
    metrics = _metrics(db)
    quick = _quick_answer(question, metrics)
    if quick:
        return quick
    cache_key = question.casefold()
    cached = _cache_get(cache_key)
    if cached:
        return cached
    if not settings.ai_enabled or not settings.ai_api_key:
        return "المساعد الذكي غير مفعّل بعد. أضف إعدادات AI في بيئة الخادم ليصبح متاحاً."
    context = json.dumps(metrics, ensure_ascii=False, separators=(",", ":"))
    payload = {"model": settings.ai_model, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"السياق الموثوق: {context}\nسؤال المستخدم: {question}"}], "temperature": 0.1, "max_tokens": 280}
    try:
        response = await _http.post(f"{settings.ai_base_url.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {settings.ai_api_key}"}, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        answer = str(content).strip() or "لم أتمكن من إنشاء إجابة مفيدة."
        _cache_put(cache_key, answer)
        return answer
    except httpx.HTTPStatusError as exc:
        logger.error("AI assistant failed: status=%s body=%s", exc.response.status_code, exc.response.text[:2000])
        return "تعذر الاتصال بالمساعد الذكي حالياً. تم تسجيل المشكلة، ويمكنك المحاولة لاحقاً."
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        logger.exception("AI assistant response could not be processed")
        return "تعذر الاتصال بالمساعد الذكي حالياً. تم تسجيل المشكلة، ويمكنك المحاولة لاحقاً."
