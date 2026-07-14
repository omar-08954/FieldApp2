# FieldApp

## تشغيل التطبيق

1. أنشئ بيئة Python وثبّت الحزم من `requirements.txt`.
2. انسخ `.streamlit/secrets.toml.example` إلى `.streamlit/secrets.toml` وأدخل قيم الاتصال الفعلية.
3. أنشئ bucket باسم القيمة المحددة في `SUPABASE_STORAGE_BUCKET` داخل Supabase Storage. يجب ألا تُحفظ المفاتيح أو كلمات المرور في Git.
4. شغّل `streamlit run app.py`.

## ترحيلات آمنة

تُنفّذ `create_tables()` ترحيلات إضافية فقط: لا تستخدم `DROP TABLE` أو `DROP COLUMN`. وهي تضيف مفاتيح الصور في `daily_reports.image_url` وتُبقي `image_data` مؤقتاً لقراءة التقارير القديمة. التقارير الجديدة تُرفع إلى Supabase Storage، ولا تُخزَّن بيانات الصورة داخل PostgreSQL.

## ملاحظات النشر

- فعّل امتداد `pg_trgm` حيث تسمح قاعدة PostgreSQL بذلك؛ التطبيق يستمر بأمان إذا لم تتوفر صلاحية تفعيله.
- افحص وجود أرقام مهام مكررة قديمة قبل أن تُنشأ الفهارس الفريدة. لا يحذف التطبيق بيانات قديمة تلقائياً.
- خادم Streamlit ليس طبقة خلفية مستقلة؛ للوصول العام يوصى بوضعه خلف HTTPS وبوابة مصادقة/عكسية، مع تنفيذ signed URLs للـ bucket الخاص.
