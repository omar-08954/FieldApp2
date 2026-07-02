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
        WHERE username = ?
        AND password = ?
    """, (username, password))

    user = cur.fetchone()

    conn.close()

    return user


# ======================================
# التحقق من تكرار المهمة بالكامل
# ======================================
def task_exists(
        technician,
        task_number,
        subscription_number,
        status,
        notes):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id
        FROM tasks
        WHERE technician = ?
        AND task_number = ?
        AND subscription_number = ?
        AND status = ?
        AND IFNULL(notes, '') = IFNULL(?, '')
    """, (
        technician,
        task_number,
        subscription_number,
        status,
        notes
    ))

    task = cur.fetchone()

    conn.close()

    return task is not None


# ======================================
# إضافة مهمة
# ======================================
def add_task(
        technician,
        task_number,
        subscription_number,
        status,
        notes):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO tasks (
            technician,
            task_number,
            subscription_number,
            status,
            notes
        )
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
# مهام اليوم لفني معين
# ======================================
def get_today_tasks(technician):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM tasks
        WHERE technician = ?
        AND DATE(created_at) = DATE('now', 'localtime')
        ORDER BY id DESC
    """, (technician,))

    tasks = cur.fetchall()

    conn.close()

    return tasks


# ======================================
# جميع المستخدمين
# ======================================
# ======================================
# حذف مهمة
# ======================================

def delete_task(task_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,)
    )

    conn.commit()
    conn.close()


# ======================================
# تعديل مهمة
# ======================================

def update_task(
        task_id,
        task_number,
        subscription_number,
        status,
        notes):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE tasks
        SET task_number = ?,
            subscription_number = ?,
            status = ?,
            notes = ?
        WHERE id = ?
    """, (
        task_number,
        subscription_number,
        status,
        notes,
        task_id
    ))

    conn.commit()
    conn.close()
    
def get_all_users():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id,
               username,
               fullname,
               role
        FROM users
        ORDER BY fullname
    """)

    users = cur.fetchall()

    conn.close()

    return users
 def change_password(username, new_password):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET password = ?
        WHERE username = ?
    """, (new_password, username))

    conn.commit()
    conn.close()
   # ======================================
# إضافة مستخدم
# ======================================
def add_user(
        username,
        password,
        fullname,
        role):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
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
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM users WHERE id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()
