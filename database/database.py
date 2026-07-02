import sqlite3
from pathlib import Path

# اسم قاعدة البيانات
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
    cur = conn.cursor()

    # جدول المستخدمين
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            fullname TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # جدول المهام
    # لاحظ أنه تم إزالة UNIQUE من task_number
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            technician TEXT NOT NULL,
            task_number TEXT NOT NULL,
            subscription_number TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ======================================
# إنشاء المستخدمين الافتراضيين
# ======================================
def create_default_users():
    users = [
        ("admin", "1234", "أحمد شاهين", "admin"),
        ("hani", "1234", "هاني صلاح", "technician"),
        ("arslan", "1234", "أرسلان", "technician"),
        ("omar", "1234", "عمر", "technician"),
        ("borhan", "1234", "برهان", "technician"),
        ("qasim", "1234", "قاسم", "technician"),
    ]

    conn = get_connection()
    cur = conn.cursor()

    for username, password, fullname, role in users:
        cur.execute("""
            INSERT OR IGNORE INTO users
            (username, password, fullname, role)
            VALUES (?, ?, ?, ?)
        """, (username, password, fullname, role))

    conn.commit()
    conn.close()


# ======================================
# تسجيل الدخول
# ======================================
def login_user(username, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM users
        WHERE username = ? AND password = ?
    """, (username, password))

    user = cur.fetchone()

    conn.close()

    return user


# ======================================
# إضافة مهمة
# ======================================
def add_task(
    technician,
    task_number,
    subscription_number,
    status,
    notes
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO tasks
        (technician,
         task_number,
         subscription_number,
         status,
         notes)

        VALUES (?, ?, ?, ?, ?)
    """, (
        technician,
        task_number,
        subscription_number,
        status,
        notes
    ))

    conn.commit()
    conn.close()


# ======================================
# جميع المهام
# ======================================
def get_all_tasks():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM tasks
        ORDER BY id DESC
    """)

    tasks = cur.fetchall()

    conn.close()

    return tasks


# ======================================
# مهام فني معين
# ======================================
def get_tasks_by_technician(technician):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM tasks
        WHERE technician = ?
        ORDER BY id DESC
    """, (technician,))

    tasks = cur.fetchall()

    conn.close()

    return tasks


# ======================================
# جميع المستخدمين
# ======================================
def get_all_users():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            username,
            fullname,
            role
        FROM users
        ORDER BY fullname
    """)

    users = cur.fetchall()

    conn.close()

    return users
    