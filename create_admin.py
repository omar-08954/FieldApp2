from database.database import create_tables, add_user

create_tables()

add_user(
    "admin",
    "1234",
    "أحمد شاهين",
    "admin"
)

print("تم إنشاء حساب الأدمن بنجاح")
