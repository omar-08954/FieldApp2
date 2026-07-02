import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = st.secrets["DATABASE_URL"]


def get_connection():

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )


def create_tables():
    pass


def login_user(username, password):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM users
        WHERE username=%s
        AND password=%s
    """, (username, password))

    user = cur.fetchone()

    cur.close()
    conn.close()

    return user


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
        (username,password,fullname,role,city)
        VALUES (%s,%s,%s,%s,%s)
    """, (
        username,
        password,
        fullname,
        role,
        city
    ))

    conn.commit()

    cur.close()
    conn.close()


def delete_user(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM users WHERE id=%s",
        (user_id,)
    )

    conn.commit()

    cur.close()
    conn.close()


def get_all_users():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM users
        ORDER BY fullname
    """)

    users = cur.fetchall()

    cur.close()
    conn.close()

    return users


def change_password(username, new_password):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET password=%s
        WHERE username=%s
    """, (
        new_password,
        username
    ))

    conn.commit()

    cur.close()
    conn.close()


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
        WHERE technician=%s
        AND task_number=%s
        AND subscription_number=%s
        AND status=%s
        AND COALESCE(notes,'')=
            COALESCE(%s,'')
    """, (
        technician,
        task_number,
        subscription_number,
        status,
        notes
    ))

    task = cur.fetchone()

    cur.close()
    conn.close()

    return task is not None


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
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        technician,
        city,
        task_number,
        subscription_number,
        status,
        notes
    ))

    conn.commit()

    cur.close()
    conn.close()


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
        SET task_number=%s,
            subscription_number=%s,
            status=%s,
            notes=%s
        WHERE id=%s
    """, (
        task_number,
        subscription_number,
        status,
        notes,
        task_id
    ))

    conn.commit()

    cur.close()
    conn.close()


def delete_task(task_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM tasks WHERE id=%s",
        (task_id,)
    )

    conn.commit()

    cur.close()
    conn.close()


def get_all_tasks():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM tasks
        ORDER BY id DESC
    """)

    tasks = cur.fetchall()

    cur.close()
    conn.close()

    return tasks
