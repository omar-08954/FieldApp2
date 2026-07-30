# FieldApp Enterprise

منصة إدارة عمليات ميدانية عربية، مبنية كـ API وواجهة ويب منفصلتين وقابلتين للنشر. النسخة القديمة من Streamlit بقيت في جذر المشروع كمرجع وظيفي أثناء الترحيل؛ النظام الجديد موجود في `backend/` و`frontend/`.

## المعمارية

```text
Next.js 15 / React 19  →  FastAPI REST + WebSocket  →  PostgreSQL
        React Query          Service / Repository         Alembic
                                  ↓
                                Redis (events/cache)
```

- Backend: طبقات `api → services → repositories → models`، جلسات SQLAlchemy 2، connection pool، OpenAPI تلقائي في `/docs`.
- Frontend: Next.js App Router، TypeScript strict، Tailwind، React Query، TanStack Table، Framer Motion، Recharts، وIBM Plex Sans Arabic. التنقل العلوي والتبويبات الداخلية يحاكيان تنظيم صفحات Streamlit القديمة؛ لا يوجد Sidebar.
- الأمان: Access/Refresh JWT قصيرا العمر، أدوار `admin / manager / technician`، CORS قابل للضبط. يجب نقل refresh token إلى Cookie `HttpOnly` عند إتمام طبقة BFF قبل النشر العام.
- الاستيراد: كل صف يعمل داخل savepoint؛ الأعمدة غير الضرورية وخصوصاً ID تتجاهل، والقيم الافتراضية هي `غير مسجل` للاشتراك و`تم الفحص` للحالة. أي استثناء يُسجل في ملف API وينشئ `ImportReview` بدل تعطيل الدفعة.
- المساعد الذكي: نافذة محادثة مشتركة في الشريط العلوي، تمرّر الطلب إلى API فقط. فعّل `AI_ENABLED=true` وأدخل `AI_API_KEY` و`AI_MODEL` في ملف البيئة؛ لا تضع المفتاح في `NEXT_PUBLIC_*` أبداً.

## التشغيل المحلي

```bash
cp .env.example .env
docker compose up --build
```

ثم افتح `http://localhost:3000`، وواجهة Swagger على `http://localhost:8000/docs`.

للتشغيل بدون Docker:

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
cd backend && alembic upgrade head && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

## قاعدة البيانات والترحيل

لا تستخدم `Base.metadata.create_all()` في بيئة الإنتاج. نفّذ فقط:

```bash
cd backend && alembic upgrade head
```

قبل نقل بيانات Streamlit، خذ نسخة احتياطية ثم أنشئ migration مخصصة تقوم بقراءة الجداول القديمة (`users`, `tasks`, `assigned_tasks`, `daily_reports`, `materials`) وكتابة الحقول المكافئة. لا تُنسخ كلمة مرور قديمة قبل تحويل hash bcrypt إلى الحقل الجديد أو اعتماد مسار انتقال آمن.

## ضمانات الاستيراد

1. لا يُستخدم أي ID قادم من Excel؛ قاعدة البيانات تولّد المفاتيح دائماً.
2. خطأ `KeyError` أو `ValueError` أو `IndexError` أو `TypeError` أو خطأ PostgreSQL لا يعبر إلى المستخدم كـ traceback.
3. تسجل الأخطاء في `fieldapp-api.log`، ويضاف صف إلى Import Review بالمصدر والسبب ونوع الاستثناء ورسالة PostgreSQL والإجراء المتخذ.
4. الملف المعطوب نفسه ينشئ سجل مراجعة بدلاً من HTTP 500.

## خريطة الترحيل الوظيفية

الـ API الجديدة تتضمن مهاماً، مستخدمين، استيراد Excel ومراجعته، المهام المسندة، المخزون، الإشعارات، وملخص لوحة التحكم. يبقى رفع تقارير الصور وترحيل البيانات التاريخية من Supabase/Streamlit خطوة ترحيل مستقلة؛ لا ينبغي مزجها مع إنشاء مخطط قاعدة بيانات جديد.

## التحقق

```bash
python -m compileall -q backend/app
cd backend && ruff check app
cd frontend && npm run build
```

## ملاحظات النشر

- استبدل كل أسرار `.env`، فعّل TLS عبر Nginx، واستخدم managed PostgreSQL مع نسخ احتياطي واختبار استعادة.
- اضبط Redis مشتركاً إذا شغلت أكثر من نسخة API؛ broker الحالي داخل الذاكرة مناسب لنسخة واحدة فقط ويجب استبداله بـ Redis Pub/Sub للتوسع الأفقي.
- أضف rate limiting، تخزين refresh-token/revocation، خدمة Push/VAPID، ومراقبة مركزية قبل تعريض النظام للإنترنت.
