# FieldApp Enterprise

منصة لإدارة العمليات الميدانية باللغة العربية، مبنية بـ **Next.js + FastAPI + PostgreSQL**.

## الصفحات والوظائف

- شريط جانبي متجاوب: لوحة التحكم، لوحة المدير، المهام، الفنيون، التقارير، المستودع، المستخدمون، الاستيراد، الإعدادات، ومركز المطور.
- تبويبات التطبيق القديم محفوظة في صفحات المدير، الفني، التقارير، المستخدمين، والمستودع.
- الإشعارات والمساعد الذكي متاحان دائماً؛ وتوجد أزرارهما، مع تسجيل الخروج، في أسفل الشريط الجانبي.
- الإعدادات تتضمن تبديل المظهر وتغيير كلمة المرور الفعلي.

## التشغيل المحلي

```bash
cp .env.example .env
docker compose up --build
```

بعد الإقلاع افتح `http://localhost`. لا تُعرّض منافذ قاعدة البيانات أو API مباشرة للإنترنت.

## النشر المجاني على Render مع Supabase (المسار المعتمد)

ملف [render.yaml](render.yaml) يجهز خدمتين فقط على Render: FastAPI كـ Web Service والواجهة كـ Static Site. لا ينشئ الملف PostgreSQL أو Redis على Render؛ قاعدة البيانات وتخزين الملفات يبقيان مستقلين على Supabase.

1. اربط المستودع في Render واختر **New → Blueprint**. سيقرأ Render ملف `render.yaml` تلقائياً.
2. عند إنشاء خدمة `fieldapp-api` اختر الخطة `Free` وأدخل أسرار API الموضحة أدناه.
3. استخدم رابط خدمة API في `NEXT_PUBLIC_API_URL` لخدمة `fieldapp-frontend`، مثل `https://fieldapp-api.onrender.com`.
4. بعد ظهور رابط الواجهة، حدّث `FRONTEND_ORIGINS` في خدمة API بالرابط الكامل للواجهة ثم أعد نشرها.

خدمة Render المجانية تتوقف بعد 15 دقيقة من عدم الاستخدام، وقد يستغرق أول طلب بعدها نحو دقيقة. لا تحفظ الملفات المرفوعة محلياً؛ إعداد الإنتاج يستخدم Supabase Storage.

### إعداد Supabase

أنشئ مشروع Supabase مجانياً، ثم أنشئ bucket خاصاً باسم `fieldapp-reports` للصور وbucket خاصاً مختلفاً باسم `fieldapp-db-backups` للنسخ الاحتياطية. استخدم **Session pooler connection string** مع `sslmode=require` في `DATABASE_URL`.

### النسخ الاحتياطي اليومي

الملف `.github/workflows/database-backup.yml` ينشئ نسخة PostgreSQL بصيغة custom يومياً ويرفعها إلى Supabase Storage. فعّل GitHub Actions وأضف أسرار المستودع التالية من **Settings → Secrets and variables → Actions**:

- `SUPABASE_DATABASE_URL`: نفس اتصال PostgreSQL المستخدم في `DATABASE_URL`.
- `SUPABASE_URL`: رابط مشروع Supabase.
- `SUPABASE_SERVICE_ROLE_KEY`: مفتاح `service_role` فقط، ولا تضعه في الواجهة أو المستودع.
- `SUPABASE_BACKUPS_BUCKET`: اسم bucket النسخ الاحتياطية، مثلاً `fieldapp-db-backups`.

يمكن تشغيل النسخ الاحتياطي يدوياً من تبويب **Actions** عبر workflow `Database backup`. اترك bucket خاصاً واحتفظ بنسخ خارجية دورية إذا كانت البيانات مهمة.

### أسرار خدمة API على Render

أضف هذه القيم في خدمة `fieldapp-api` فقط:

`DATABASE_URL`, `JWT_SECRET`, `FRONTEND_ORIGINS`, `INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_PASSWORD`, `INITIAL_ADMIN_NAME`, `DEFAULT_TECHNICIAN_PASSWORD`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_REPORTS_BUCKET`.

لا تضف `NEXT_PUBLIC_API_URL` إلى خدمة API؛ أضفه إلى خدمة الواجهة فقط. لا تضع `DATABASE_URL` أو `SUPABASE_SERVICE_ROLE_KEY` في الواجهة.

## النشر الاختياري على Cloudflare

يوجد إعداد Cloudflare قديم داخل `cloudflare/api`، لكنه يستخدم Cloudflare Containers ويتطلب Workers Paid. لا تستخدمه إذا كان الهدف هو الاستضافة المجانية.

## النشر الفعلي مع HTTPS

1. أنشئ خادماً Linux، وافتح المنافذ `80` و`443` فقط، ثم وجّه سجلّي DNS من نوع A/AAAA للدومين إلى عنوانه.
2. انسخ [.env.production.example](.env.production.example) إلى `.env.production`، واملأ الدومين وكلمات المرور و`JWT_SECRET` و`FRONTEND_ORIGINS` بعنوان HTTPS الفعلي.
3. شغّل:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
```

ملف [deploy/Caddyfile](deploy/Caddyfile) يصدر ويجدد شهادة TLS تلقائياً عبر Let’s Encrypt، ويوجه الويب وواجهة API خلف نفس الدومين. افحص الحالة عبر `docker compose --env-file .env.production -f docker-compose.production.yml ps` واحتفظ بنسخ احتياطية منتظمة من volume قاعدة البيانات قبل كل ترقية.

## التحقق

```bash
python -m compileall -q backend/app
cd backend && ruff check app
cd frontend && npm run build
```
