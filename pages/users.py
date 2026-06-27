import streamlit as st
import pandas as pd

from database.database import (
    get_all_users,
    add_user,
    delete_user
)

# ======================================
# التحقق من تسجيل الدخول
# ======================================

if not st.session_state.get("logged_in", False):
    st.warning("يرجى تسجيل الدخول أولاً")
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("هذه الصفحة مخصصة للمدير فقط")
    st.stop()

# ======================================
# زر تسجيل الدخول والخروج
# ======================================

with st.sidebar:

    st.divider()

    if st.session_state.get("logged_in", False):

        if st.button(
            "🚪 تسجيل الخروج",
            use_container_width=True
        ):
            st.switch_page("app.py")

    else:

        if st.button(
            "🔑 تسجيل الدخول",
            use_container_width=True
        ):
            st.switch_page("app.py")

# ======================================
# عنوان الصفحة
# ======================================

st.title("👥 إدارة المستخدمين")

# ======================================
# إضافة مستخدم
# ======================================

st.subheader("➕ إضافة مستخدم")

username = st.text_input("اسم المستخدم")

password = st.text_input(
    "كلمة المرور",
    type="password"
)

fullname = st.text_input("الاسم الكامل")

role = st.selectbox(
    "الصلاحية",
    [
        "admin",
        "technician"
    ]
)

if st.button(
    "إضافة المستخدم",
    use_container_width=True
):

    if not username or not password or not fullname:

        st.error("يرجى تعبئة جميع الحقول")

    else:

        try:

            add_user(
                username,
                password,
                fullname,
                role
            )

            st.success(
                "تمت إضافة المستخدم بنجاح"
            )

            st.rerun()

        except Exception:

            st.error(
                "اسم المستخدم موجود مسبقًا"
            )

st.divider()

# ======================================
# عرض المستخدمين
# ======================================

st.subheader("📋 جميع المستخدمين")

users = get_all_users()

df = pd.DataFrame(
    [dict(row) for row in users]
)

display_df = df.rename(
    columns={
        "username": "اسم المستخدم",
        "fullname": "الاسم الكامل",
        "role": "الصلاحية"
    }
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

st.divider()

# ======================================
# حذف مستخدم
# ======================================

st.subheader("🗑️ حذف مستخدم")

user_ids = df["id"].tolist()

selected_user = st.selectbox(
    "اختر المستخدم",
    user_ids
)

if st.button(
    "حذف المستخدم",
    use_container_width=True
):

    delete_user(selected_user)

    st.success("تم حذف المستخدم")

    st.rerun()
    