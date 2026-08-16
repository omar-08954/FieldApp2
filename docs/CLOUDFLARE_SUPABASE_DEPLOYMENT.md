# نشر FieldApp على Cloudflare مع Supabase

## البنية

`المتصفح → fieldapp-web (Cloudflare Pages) → api.<domain> (Cloudflare Worker/Container) → Supabase PostgreSQL`

صور التقارير تحفظ في R2، ولا يعتمد الإنتاج على قرص الحاوية المؤقت. النسخة اليومية المنفصلة من PostgreSQL تحفظ في bucket R2 آخر عبر GitHub Actions؛ لا تستخدم bucket صور التقارير للنسخ الاحتياطي.

## إعداد Supabase

1. أنشئ مشروع Supabase وخذ **Session pooler** connection string مع `sslmode=require` وضعه في `DATABASE_URL`.
2. فعّل النسخ اليومية في صفحة Database > Backups. للبيانات الحرجة فعّل PITR.
3. لا تعرض مفاتيح Supabase أو سلسلة الاتصال في Next.js أو في المستودع.

## إعداد Cloudflare من VS Code

1. استخدم Node.js 22 في VS Code (`nvm use` يقرأ ملف `.nvmrc`)؛ إصدار Node.js 26 الموجود في بعض البيئات لا يدعمه Next.js 15 رسمياً.
2. أنشئ bucket باسم `fieldapp-reports` لـR2، وbucket مختلف مثل `fieldapp-db-backups` للنسخ الاحتياطية.
3. من طرفية VS Code نفّذ `cd cloudflare/api && npm install && npx wrangler login` ثم عيّن أسرار API عبر `npx wrangler secret put <NAME>` لكل من: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `FRONTEND_ORIGINS`, `INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_PASSWORD`, `INITIAL_ADMIN_NAME`, `DEFAULT_TECHNICIAN_PASSWORD`, `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.
4. نفّذ `npm run deploy` من `cloudflare/api`. تتطلب العملية Docker يعمل محلياً لبناء صورة FastAPI؛ عند أول تشغيل يُطبّق Alembic ثم ينشئ المدير والفنيين الناقصين.
5. أضف custom domain للـAPI مثل `api.example.com`، ثم اضبط `FRONTEND_ORIGINS=https://app.example.com`.
6. في إعدادات Cloudflare Pages اربط المستودع واختر root directory: `frontend`، وbuild command: `npm run build`، وbuild output directory: `out`. أضف متغير البناء `NEXT_PUBLIC_API_URL=https://api.example.com` ثم انشر الموقع على `app.example.com`.

## النسخ الاحتياطي المنفصل

أضف أسرار المستودع في GitHub: `SUPABASE_DATABASE_URL`, `R2_BACKUP_ACCESS_KEY_ID`, `R2_BACKUP_SECRET_ACCESS_KEY`, `R2_BACKUP_ENDPOINT_URL`, `R2_BACKUP_BUCKET`. workflow `database-backup.yml` ينشئ كل يوم dump بصيغة PostgreSQL custom ويرفعه إلى bucket R2 مستقل بتشفير SSE. فعّل Object Lock/retention على bucket النسخ إذا كانت سياسة الحساب متاحة.

لا تبدأ نشر الإنتاج قبل تغيير كلمة مرور المدير الأولية وتخزين جميع القيم الحساسة كـWorker/GitHub secrets فقط.

عند أول تشغيل، ينشئ الـAPI المدير الأولي وكل حسابات الفنيين المعرفة في النظام. العملية idempotent: لا تعيد ضبط كلمات المرور أو تعيد تفعيل الحسابات الموجودة.
