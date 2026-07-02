import streamlit as st
import pandas as pd
import time

from database.database import (
    add_user,
    delete_user,
    get_all_users
)

# ======================================
# التحقق من تسجيل الدخول
# ======================================

if not st.session_state.get("logged_in", False):
    st.warning("يرجى تسجيل الدخول أولاً")
    st.stop()

# ======================================
# السماح للمدير فقط
# ======================================

if st.session_state.get("role") != "admin":
    st.error("ليس لديك صلاحية للوصول لهذه الصفحة")
    st.stop()

# ======================================
# عنوان الصفحة
# ======================================

st.title("👥 إدارة المستخدمين")

# ======================================
# إضافة مستخدم جديد
# ======================================

st.subheader("➕ إضافة مستخدم جديد")

with st.form(
    "add_user_form",
    clear_on_submit=True
):

    username = st.text_input(
        "اسم المستخدم"
    )

    password = st.text_input(
        "كلمة المرور",
        type="password"
    )

    fullname = st.text_input(
        "الاسم الكامل"
    )

    role = st.selectbox(
        "الصلاحية",
        [
            "admin",
            "technician"
        ]
    )

    city = st.selectbox(
        "المدينة",
        [
            "مكة",
            "جدة"
        ]
    )

    submitted = st.form_submit_button(
        "💾 إضافة المستخدم",
        width="stretch"
    )

# ======================================
# حفظ المستخدم
# ======================================

if submitted:

    if not username or not password or not fullname:

        st.warning(
            "⚠️ يرجى تعبئة جميع الحقول"
        )

    else:

        try:

            add_user(
                username,
                password,
                fullname,
                role,
                city
            )

            msg = st.success(
                "✅ تم إضافة المستخدم بنجاح"
            )

            # إظهار الرسالة لمدة 3 ثوانٍ
            time.sleep(3)

            # حذف الرسالة
            msg.empty()

            # تحديث الصفحة
            st.rerun()

        except Exception as e:

            st.error(
                f"❌ {e}"
            )

# ======================================
# عرض المستخدمين
# ======================================

st.divider()

st.subheader("📋 جميع المستخدمين")

users = get_all_users()

if users:

    df = pd.DataFrame(
        [dict(user) for user in users]
    )

    st.dataframe(
        df,
        width="stretch",
        hide_index=True
    )

    st.divider()

    # ======================================
    # حذف مستخدم
    # ======================================

    st.subheader("🗑️ حذف مستخدم")

    user_options = {
        f"{row['fullname']} ({row['username']})":
        row["id"]

        for _, row in df.iterrows()
    }

    selected_user = st.selectbox(
        "اختر المستخدم",
        list(user_options.keys())
    )

    selected_id = user_options[
        selected_user
    ]

    selected_row = (
        df[df["id"] == selected_id]
        .iloc[0]
    )

    st.info(
        f"المستخدم المحدد: "
        f"{selected_row['fullname']}"
    )

    if st.button(
        "🗑️ حذف المستخدم",
        width="stretch"
    ):

        # منع حذف الحساب الحالي

        if (
            selected_row["username"]
            ==
            st.session_state.username
        ):

            st.error(
                "❌ لا يمكنك حذف حسابك الحالي"
            )

        else:

            delete_user(selected_id)

            msg = st.success(
                "✅ تم حذف المستخدم بنجاح"
            )

            time.sleep(3)

            msg.empty()

            st.rerun()

else:

    st.info(
        "لا يوجد مستخدمون"
    )

# ======================================
# تسجيل الخروج
# ======================================

st.divider()

if st.button(
    "🚪 تسجيل الخروج والعودة للرئيسية",
    width="stretch"
):

    st.session_state.logged_in = False
    st.session_state.fullname = ""
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.city = ""

    st.switch_page("app.py")
    
    users = get_all_users()

for user in users:
    st.write(dict(user))
