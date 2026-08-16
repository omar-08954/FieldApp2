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

## النشر على Cloudflare مع Supabase (المسار المعتمد)

التطبيق مجهز للنشر بواجهة Next.js على Cloudflare Pages وFastAPI داخل Cloudflare Container وقاعدة PostgreSQL مستقلة في Supabase. استخدم دليل [النشر من VS Code](docs/CLOUDFLARE_SUPABASE_DEPLOYMENT.md). يشمل الدليل التخزين الدائم لصور التقارير في R2 ونسخة PostgreSQL يومية مستقلة في bucket R2 مختلف، إلى جانب نسخ Supabase اليومية وPITR.

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
