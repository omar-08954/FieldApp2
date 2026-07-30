"""Server-side AI boundary. The browser never receives provider credentials."""
import logging
import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import Task

logger = logging.getLogger(__name__)
settings = get_settings()
SYSTEM_PROMPT = """أنت مساعد FieldApp الداخلي. أجب بالعربية باختصار ووضوح.
ساعد فقط في فهم بيانات وتشغيل نظام المهام الميدانية. لا تخترع أرقاماً أو صلاحيات،
ولا تكشف كلمات مرور أو أسراراً أو رسائل أخطاء داخلية. إذا لم تملك بيانات كافية فقل ذلك."""


def _context(db: Session) -> str:
    total = db.scalar(select(func.count()).select_from(Task)) or 0
    by_status = db.execute(select(Task.task_status, func.count()).group_by(Task.task_status)).all()
    distribution = ", ".join(f"{status}: {count}" for status, count in by_status)
    return f"ملخص حي من قاعدة البيانات: إجمالي المهام {total}. توزيع الحالات: {distribution or 'لا توجد بيانات'}"


async def ask(db: Session, question: str) -> str:
    if not settings.ai_enabled or not settings.ai_api_key:
        return "المساعد الذكي غير مفعّل بعد. أضف إعدادات AI في بيئة الخادم ليصبح متاحاً."
    payload = {"model": settings.ai_model, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "system", "content": _context(db)}, {"role": "user", "content": question}], "temperature": 0.2}
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.post(f"{settings.ai_base_url.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {settings.ai_api_key}"}, json=payload)
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return str(content).strip() or "لم أتمكن من إنشاء إجابة مفيدة."
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        logger.exception("AI assistant provider request failed")
        return "تعذر الاتصال بالمساعد الذكي حالياً. تم تسجيل المشكلة، ويمكنك المحاولة لاحقاً."
