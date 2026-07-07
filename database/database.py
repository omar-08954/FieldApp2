import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor


DATABASE_URL = st.secrets["DATABASE_URL"]


def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def execute(query, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    cur.close()
    conn.close()


def fetch_one(query, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def fetch_all(query, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def create_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            fullname TEXT NOT NULL,
            role TEXT NOT NULL,
            city TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            technician TEXT NOT NULL,
            city TEXT,
            task_number TEXT NOT NULL,
            subscription_number TEXT NOT NULL,
            task_type TEXT NOT NULL,
            task_status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS materials (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            unit TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS notes TEXT DEFAULT ''")
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
    cur.execute("ALTER TABLE materials ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_task_number ON tasks(task_number)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_filters ON tasks(technician, city, task_type, task_status)")
    conn.commit()
    cur.close()
    conn.close()


def login_user(username, password):
    return fetch_one(
        """
        SELECT id, username, fullname, role, city
        FROM users
        WHERE username = %s AND password = %s
        """,
        (username, password),
    )


def check_current_password(username, current_password):
    return fetch_one(
        "SELECT id FROM users WHERE username = %s AND password = %s",
        (username, current_password),
    ) is not None


def add_user(username, password, fullname, role, city):
    execute(
        """
        INSERT INTO users (username, password, fullname, role, city)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (username.strip(), password.strip(), fullname.strip(), role, city),
    )


def delete_user(user_id):
    execute("DELETE FROM users WHERE id = %s", (int(user_id),))


def get_all_users():
    return fetch_all(
        """
        SELECT id, username, fullname, role, city, created_at
        FROM users
        ORDER BY fullname
        """
    )


def change_password(username, new_password):
    execute(
        "UPDATE users SET password = %s WHERE username = %s",
        (new_password, username),
    )


def task_exists(task_number, exclude_id=None):
    if exclude_id:
        return fetch_one(
            "SELECT id FROM tasks WHERE task_number = %s AND id <> %s",
            (task_number.strip(), int(exclude_id)),
        ) is not None
    return fetch_one(
        "SELECT id FROM tasks WHERE task_number = %s",
        (task_number.strip(),),
    ) is not None


def add_task(technician, city, task_number, subscription_number, task_type, task_status, notes=""):
    execute(
        """
        INSERT INTO tasks
        (technician, city, task_number, subscription_number, task_type, task_status, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            technician.strip(),
            city.strip() if city else "",
            task_number.strip(),
            subscription_number.strip(),
            task_type,
            task_status,
            notes.strip(),
        ),
    )


def update_task(task_id, task_number, subscription_number, task_type, task_status, notes=""):
    execute(
        """
        UPDATE tasks
        SET task_number = %s,
            subscription_number = %s,
            task_type = %s,
            task_status = %s,
            notes = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (
            task_number.strip(),
            subscription_number.strip(),
            task_type,
            task_status,
            notes.strip(),
            int(task_id),
        ),
    )


def delete_task(task_id):
    execute("DELETE FROM tasks WHERE id = %s", (int(task_id),))


def get_all_tasks():
    return fetch_all("SELECT * FROM tasks ORDER BY id DESC")


def get_task_by_number(task_number):
    return fetch_one(
        "SELECT * FROM tasks WHERE task_number = %s ORDER BY id DESC LIMIT 1",
        (task_number.strip(),),
    )


def search_tasks(keyword="", technician="", city="", task_type="", task_status=""):
    query = "SELECT * FROM tasks WHERE 1 = 1"
    params = []
    if keyword:
        query += """
            AND (
                task_number ILIKE %s
                OR subscription_number ILIKE %s
                OR technician ILIKE %s
                OR COALESCE(notes, '') ILIKE %s
            )
        """
        like = f"%{keyword.strip()}%"
        params.extend([like, like, like, like])
    if technician and technician != "الكل":
        query += " AND technician = %s"
        params.append(technician)
    if city and city != "الكل":
        query += " AND city = %s"
        params.append(city)
    if task_type and task_type != "الكل":
        query += " AND task_type = %s"
        params.append(task_type)
    if task_status and task_status != "الكل":
        query += " AND task_status = %s"
        params.append(task_status)
    query += " ORDER BY id DESC"
    return fetch_all(query, params)


def create_materials_table():
    create_tables()


def material_exists(name, exclude_id=None):
    if exclude_id:
        return fetch_one(
            "SELECT id FROM materials WHERE LOWER(name) = LOWER(%s) AND id <> %s",
            (name.strip(), int(exclude_id)),
        ) is not None
    return fetch_one(
        "SELECT id FROM materials WHERE LOWER(name) = LOWER(%s)",
        (name.strip(),),
    ) is not None


def add_material(name, quantity, unit, notes):
    execute(
        """
        INSERT INTO materials (name, quantity, unit, notes)
        VALUES (%s, %s, %s, %s)
        """,
        (name.strip(), int(quantity), unit, notes.strip()),
    )


def get_all_materials():
    return fetch_all("SELECT * FROM materials ORDER BY name")


def update_material(material_id, name, unit, notes):
    execute(
        """
        UPDATE materials
        SET name = %s, unit = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (name.strip(), unit, notes.strip(), int(material_id)),
    )


def increase_material(material_id, quantity):
    execute(
        """
        UPDATE materials
        SET quantity = quantity + %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (int(quantity), int(material_id)),
    )


def decrease_material(material_id, quantity):
    material = fetch_one("SELECT quantity FROM materials WHERE id = %s", (int(material_id),))
    if not material or int(material["quantity"]) < int(quantity):
        return False
    execute(
        """
        UPDATE materials
        SET quantity = quantity - %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (int(quantity), int(material_id)),
    )
    return True


def delete_material(material_id):
    execute("DELETE FROM materials WHERE id = %s", (int(material_id),))
