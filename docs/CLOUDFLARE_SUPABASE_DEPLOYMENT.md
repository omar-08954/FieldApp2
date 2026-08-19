# نشر FieldApp على Cloudflare مع Supabase

## البنية

`المتصفح → Cloudflare Pages → Cloudflare Worker/Container → Supabase PostgreSQL + Supabase Storage`

Cloudflare للاستضافة والتشغيل فقط. صور التقارير والنسخ الاحتياطية تحفظ في Supabase Storage، لذلك لا يحتاج المشروع إلى R2 أو R2 API token.

## إعداد Supabase

1. أنشئ مشروع Supabase وخذ **Session pooler** connection string مع `sslmode=require` وضعه في `DATABASE_URL`.
2. أنشئ bucket خاصًا باسم `fieldapp-reports` للصور وbucket خاصًا مختلفًا باسم `fieldapp-db-backups` للنسخ الاحتياطية.
3. خذ `Project URL` و`service_role key` من Supabase. لا تضع المفتاح أو سلسلة الاتصال في Next.js أو المستودع.

## أسرار Cloudflare

من `cloudflare/api` نفّذ `npx wrangler login` ثم عيّن الأسرار عبر `npx wrangler secret put <NAME>`:

`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `FRONTEND_ORIGINS`, `INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_PASSWORD`, `INITIAL_ADMIN_NAME`, `DEFAULT_TECHNICIAN_PASSWORD`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_REPORTS_BUCKET`.

بعد ذلك نفّذ `npm run deploy`. في Cloudflare Pages استخدم `frontend` كـ root directory، و`npm run build` كأمر البناء، و`out` كمجلد الإخراج، ثم أضف `NEXT_PUBLIC_API_URL`.

## النسخ الاحتياطي

أضف أسرار GitHub التالية: `SUPABASE_DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_BACKUPS_BUCKET`.

يسجل workflow `database-backup.yml` نسخة PostgreSQL يومية بصيغة custom ويرفعها إلى bucket النسخ الاحتياطية في Supabase Storage. اترك bucket خاصًا واحذف النسخ القديمة دوريًا عند الحاجة.

غيّر كلمات المرور ومفاتيح الأسرار قبل نشر الإنتاج.
