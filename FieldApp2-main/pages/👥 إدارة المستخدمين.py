import time

import pandas as pd
import streamlit as st

from database.database import add_user, delete_user, execute, get_all_users
from ui import init_page, page_header, require_login, top_nav


ROLE_LABELS = {
    "admin": "مدير",
    "technician": "فني",
}
ROLE_VALUES = {label: value for value, label in ROLE_LABELS.items()}


init_page("إدارة المستخدمين")
require_login(["admin"])
top_nav()
page_header("👥 إدارة المستخدمين", "إدارة المستخدمين والصلاحيات من مكان واحد.")


def load_users_df():
    users = get_all_users()
    if not users:
        return pd.DataFrame(columns=["id", "username", "fullname", "role", "city", "created_at"])
    return pd.DataFrame(users)


def username_exists(df, username, exclude_id=None):
    username = username.strip().lower()
    matches = df[df["username"].astype(str).str.lower() == username]
    if exclude_id is not None:
        matches = matches[matches["id"].astype(int) != int(exclude_id)]
    return not matches.empty


def update_user(user_id, fullname, password, role):
    if password:
        execute(
            """
            UPDATE users
            SET fullname = %s, password = %s, role = %s
            WHERE id = %s
            """,
            (fullname.strip(), password.strip(), role, int(user_id)),
        )
    else:
        execute(
            """
            UPDATE users
            SET fullname = %s, role = %s
            WHERE id = %s
            """,
            (fullname.strip(), role, int(user_id)),
        )


def users_table(df):
    if df.empty:
        st.info("لا يوجد مستخدمون حالياً.")
        return
    display = df.copy()
    display["نوع المستخدم"] = display["role"].map(ROLE_LABELS).fillna(display["role"])
    columns = {
        "fullname": "الاسم الكامل",
        "username": "اسم المستخدم",
        "created_at": "تاريخ الإنشاء",
    }
    visible_columns = ["fullname", "username", "نوع المستخدم"]
    if "created_at" in display.columns:
        visible_columns.append("created_at")
    st.dataframe(
        display[visible_columns].rename(columns=columns),
        hide_index=True,
        width="stretch",
    )


def user_options(df):
    if df.empty:
        return {}
    return {
        f"{row['fullname']} ({row['username']})": row
        for _, row in df.sort_values("fullname").iterrows()
    }


users_df = load_users_df()
tab_view, tab_add, tab_edit, tab_delete = st.tabs(
    [
        "👥 عرض المستخدمين",
        "➕ إضافة مستخدم",
        "✏️ تعديل مستخدم",
        "🗑️ حذف مستخدم",
    ]
)

with tab_view:
    search = st.text_input("بحث بالاسم أو اسم المستخدم")
    filtered_df = users_df.copy()
    if search.strip() and not filtered_df.empty:
        keyword = search.strip()
        filtered_df = filtered_df[
            filtered_df["fullname"].astype(str).str.contains(keyword, case=False, na=False)
            | filtered_df["username"].astype(str).str.contains(keyword, case=False, na=False)
        ]
    users_table(filtered_df)
    st.caption(f"عدد المستخدمين: {len(filtered_df)}")

with tab_add:
    with st.form("add_user_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fullname = st.text_input("الاسم الكامل")
            username = st.text_input("اسم المستخدم")
        with col2:
            password = st.text_input("كلمة المرور", type="password")
            confirm_password = st.text_input("تأكيد كلمة المرور", type="password")
        role_label = st.selectbox("نوع المستخدم", ["مدير", "فني"])
        add_submitted = st.form_submit_button("➕ إضافة المستخدم", width="stretch")

    if add_submitted:
        fullname = fullname.strip()
        username = username.strip()
        password = password.strip()
        confirm_password = confirm_password.strip()
        if not fullname or not username or not password or not confirm_password:
            st.warning("يرجى تعبئة جميع الحقول.")
        elif password != confirm_password:
            st.error("كلمة المرور وتأكيدها غير متطابقين.")
        elif username_exists(users_df, username):
            st.error("اسم المستخدم مستخدم بالفعل")
        else:
            try:
                with st.spinner("جاري إضافة المستخدم..."):
                    add_user(username, password, fullname, ROLE_VALUES[role_label], "")
                    time.sleep(0.4)
                st.success("✅ تم إضافة المستخدم بنجاح")
                time.sleep(0.6)
                st.rerun()
            except Exception as exc:
                if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                    st.error("اسم المستخدم مستخدم بالفعل")
                else:
                    st.error(f"تعذر إضافة المستخدم: {exc}")

with tab_edit:
    options = user_options(users_df)
    if not options:
        st.info("لا يوجد مستخدمون للتعديل.")
    else:
        selected_label = st.selectbox("اختر المستخدم", list(options.keys()), key="edit_user_select")
        selected_user = options[selected_label]

        with st.form("edit_user_form"):
            fullname = st.text_input("الاسم الكامل", value=selected_user["fullname"])
            password = st.text_input("كلمة المرور الجديدة (اتركها فارغة بدون تغيير)", type="password")
            role_current = ROLE_LABELS.get(selected_user["role"], selected_user["role"])
            role_label = st.selectbox(
                "نوع المستخدم",
                ["مدير", "فني"],
                index=["مدير", "فني"].index(role_current) if role_current in ["مدير", "فني"] else 0,
            )
            save_submitted = st.form_submit_button("💾 حفظ التعديلات", width="stretch")

        if save_submitted:
            if not fullname.strip():
                st.warning("يرجى إدخال الاسم الكامل.")
            else:
                with st.spinner("جاري حفظ التعديلات..."):
                    update_user(selected_user["id"], fullname, password, ROLE_VALUES[role_label])
                    time.sleep(0.4)
                st.success("✅ تم حفظ التعديلات بنجاح")
                time.sleep(0.6)
                st.rerun()

with tab_delete:
    options = user_options(users_df)
    if not options:
        st.info("لا يوجد مستخدمون للحذف.")
    else:
        selected_label = st.selectbox("اختر المستخدم", list(options.keys()), key="delete_user_select")
        selected_user = options[selected_label]
        admins_count = int((users_df["role"] == "admin").sum()) if not users_df.empty else 0

        st.info(
            f"""
الاسم الكامل: {selected_user['fullname']}

اسم المستخدم: {selected_user['username']}

نوع المستخدم: {ROLE_LABELS.get(selected_user['role'], selected_user['role'])}
"""
        )
        st.warning("تأكيد واضح: سيتم حذف هذا المستخدم نهائياً من قاعدة البيانات.")
        confirm_delete = st.checkbox("نعم، أؤكد حذف المستخدم", key="confirm_delete_user")

        if st.button("🗑️ حذف المستخدم", width="stretch", disabled=not confirm_delete):
            if selected_user["username"] == st.session_state.username:
                st.error("لا يمكن حذف المستخدم الذي قام بتسجيل الدخول حالياً.")
            elif selected_user["role"] == "admin" and admins_count <= 1:
                st.error("لا يمكن حذف آخر مدير في النظام.")
            else:
                with st.spinner("جاري حذف المستخدم..."):
                    delete_user(selected_user["id"])
                    time.sleep(0.4)
                st.success("✅ تم حذف المستخدم بنجاح")
                time.sleep(0.6)
                st.rerun()
