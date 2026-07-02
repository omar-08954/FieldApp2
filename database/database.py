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

    # ======================================
    # جدول المستخدمين
    # ======================================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            fullname TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # إضافة عمود المدينة إذا لم يكن موجوداً

    try:
        cur.execute(
            "ALTER TABLE users ADD COLUMN city TEXT DEFAULT 'جدة'"
        )
    except:
        pass

    # ======================================
    # جدول المهام
    # ======================================

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

    # إضافة عمود المدينة إذا لم يكن موجوداً

    try:
        cur.execute(
            "ALTER TABLE tasks ADD COLUMN city TEXT DEFAULT 'جدة'"
        )
    except:
        pass

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
# إضافة مستخدم
# ======================================

def add_user(
        username,
        password,
        fullname,
        role,
        city):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users
        (username, password, fullname, role, city)
        VALUES (?, ?, ?, ?, ?)
    """, (
        username,
        password,
        fullname,
        role,
        city
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


# ======================================
# تغيير كلمة المرور
# ======================================

def change_password(username, new_password):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET password = ?
        WHERE username = ?
    """, (
        new_password,
        username
    ))

    conn.commit()
    conn.close()


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
        AND IFNULL(notes,'') = IFNULL(?, '')
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
        city,
        task_number,
        subscription_number,
        status,
        notes):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO tasks
        (
            technician,
            city,
            task_number,
            subscription_number,
            status,
            notes
        )

        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        technician,
        city,
        task_number,
        subscription_number,
        status,
        notes
    ))

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
# جلب جميع المهام
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
# جلب جميع المستخدمين
# ======================================

def get_all_users():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            username,
            fullname,
            role,
            city
        FROM users
        ORDER BY fullname
    """)

    users = cur.fetchall()

    conn.close()

    return users
    