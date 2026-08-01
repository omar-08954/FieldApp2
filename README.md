# FieldApp Enterprise

منصة لإدارة العمليات الميدانية باللغة العربية. هذه النسخة تعمل فقط بـ **Next.js + FastAPI + PostgreSQL**؛ تمت إزالة تطبيق Streamlit القديم وملفاته المرجعية.

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

## النشر الفعلي مع HTTPS

1. أنشئ خادماً Linux، وافتح المنافذ `80` و`443` فقط، ثم وجّه سجلّي DNS من نوع A/AAAA للدومين إلى عنوانه.
2. انسخ [.env.production.example](.env.production.example) إلى `.env.production`، واملأ الدومين وكلمات المرور و`JWT_SECRET` و`FRONTEND_ORIGINS` بعنوان HTTPS الفعلي.
3. شغّل:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
```

ملف [deploy/Caddyfile](deploy/Caddyfile) يصدر ويجدد شهادة TLS تلقائياً عبر Let’s Encrypt، ويوجه الويب وواجهة API خلف نفس الدومين. افحص الحالة عبر `docker compose --env-file .env.production -f docker-compose.production.yml ps` واحتفظ بنسخ احتياطية منتظمة من volume قاعدة البيانات قبل كل ترقية.

## تجربة Render بدون دومين

يوجد [render.yaml](render.yaml) جاهز لإنشاء واجهة Next.js وFastAPI وPostgreSQL وRender Key Value. من Render اختر **New → Blueprint**، اربط مستودع GitHub، ثم اختر الفرع الذي يحتوي هذا الملف. ستحصل الواجهة على رابط `onrender.com` مع HTTPS تلقائياً.

الخطة المجانية مناسبة للعرض والتجربة فقط: خدمة الويب قد تتوقف عند عدم الاستخدام، وملفات صور التقارير لا تملك قرصاً دائماً، وقاعدة PostgreSQL المجانية تنتهي بعد 30 يوماً. قبل استخدام النظام فعلياً، رقِّ قاعدة البيانات والخدمات إلى خطة مدفوعة، ثم أضف الدومين من إعدادات خدمة الواجهة.

## التحقق

```bash
python -m compileall -q backend/app
cd backend && ruff check app
cd frontend && npm run build
```
