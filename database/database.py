import sqlite3

DB_NAME = "fieldapp.db"


# ======================================
# الاتصال بقاعدة البيانات
# ======================================

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ======================================
# إنشاء الجداول
# ======================================

def create_tables():

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            fullname TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            technician TEXT NOT NULL,
            task_number TEXT UNIQUE NOT NULL,
            subscription_number TEXT NOT NULL,
            task_type TEXT NOT NULL,
            notes TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ======================================
# إنشاء المستخدمين الافتراضيين
# يتم التنفيذ مرة واحدة فقط
# ======================================

def create_default_users():

    conn = get_connection()
    c = conn.cursor()

    # إضافة المستخدمين فقط إذا كان الجدول فارغاً
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]

    if count == 0:

        users = [
            ("admin", "1234", "أحمد شاهين", "admin"),
            ("hani", "1234", "هاني صلاح", "technician"),
            ("arslan", "1234", "أرسلان", "technician"),
            ("omar", "1234", "عمر", "technician"),
            ("borhan", "1234", "برهان", "technician"),
            ("qasim", "1234", "قاسم", "technician")
        ]

        c.executemany("""
            INSERT INTO users
            (username, password, fullname, role)
            VALUES (?, ?, ?, ?)
        """, users)

        conn.commit()

    conn.close()


# ======================================
# تسجيل الدخول
# ======================================

def login_user(username, password):

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT *
        FROM users
        WHERE username = ? AND password = ?
    """, (username, password))

    user = c.fetchone()

    conn.close()

    return user


# ======================================
# إضافة مهمة
# ======================================

def add_task(
        technician,
        task_number,
        subscription_number,
        task_type,
        notes):

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT INTO tasks
        (
            technician,
            task_number,
            subscription_number,
            task_type,
            notes
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        technician,
        task_number,
        subscription_number,
        task_type,
        notes
    ))

    conn.commit()
    conn.close()


# ======================================
# التحقق من وجود المهمة
# ======================================

def task_exists(task_number):

    conn = get_connection()
    c = conn.cursor()

    c.execute(
        "SELECT id FROM tasks WHERE task_number = ?",
        (task_number,)
    )

    exists = c.fetchone() is not None

    conn.close()

    return exists


# ======================================
# جلب جميع المهام
# ======================================

def get_all_tasks():

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT *
        FROM tasks
        ORDER BY id DESC
    """)

    tasks = c.fetchall()

    conn.close()

    return tasks


# ======================================
# تعديل مهمة
# ======================================

def update_task(
        task_id,
        subscription_number,
        task_type,
        notes):

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        UPDATE tasks
        SET
            subscription_number = ?,
            task_type = ?,
            notes = ?
        WHERE id = ?
    """, (
        subscription_number,
        task_type,
        notes,
        task_id
    ))

    conn.commit()
    conn.close()


# ======================================
# حذف مهمة
# ======================================

def delete_task(task_id):

    conn = get_connection()
    c = conn.cursor()

    c.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,)
    )

    conn.commit()
    conn.close()


# ======================================
# جلب جميع المستخدمين
# ======================================

def get_all_users():

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT id, username, fullname, role
        FROM users
        ORDER BY fullname
    """)

    users = c.fetchall()

    conn.close()

    return users


# ======================================
# إضافة مستخدم
# ======================================

def add_user(
        username,
        password,
        fullname,
        role):

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT INTO users
        (username, password, fullname, role)
        VALUES (?, ?, ?, ?)
    """, (
        username,
        password,
        fullname,
        role
    ))

    conn.commit()
    conn.close()


# ======================================
# حذف مستخدم
# ======================================

def delete_user(user_id):

    conn = get_connection()
    c = conn.cursor()

    c.execute(
        "DELETE FROM users WHERE id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()


# ======================================
# تغيير كلمة المرور
# ======================================

def change_password(
        username,
        new_password):

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        UPDATE users
        SET password = ?
        WHERE username = ?
    """, (
        new_password,
        username
    ))

    conn.commit()
    conn.close()
    