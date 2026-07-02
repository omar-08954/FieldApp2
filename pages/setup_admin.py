import streamlit as st

from database.database import (
    add_user,
    get_all_users
)

# ======================================
# التحقق من وجود مدير
# ======================================

users = get_all_users()

admin_exists = False

if users:
    for user in users:

        user_data = dict(user)

        if user_data["role"] == "admin":
            admin_exists = True
            break

# ======================================
# إذا كان المدير موجوداً
# ======================================

if admin_exists:

    st.success("✅ يوجد حساب مدير بالفعل")

    st.info(
        "يمكنك حذف هذه الصفحة من المشروع الآن"
    )

    st.stop()

# ======================================
# إنشاء المدير الأول
# ======================================

st.title("👔 إنشاء حساب المدير الأول")

st.warning(
    "⚠️ هذه الصفحة تعمل مرة واحدة فقط"
)

with st.form("create_admin_form"):

    fullname = st.text_input(
        "الاسم الكامل"
    )

    username = st.text_input(
        "اسم المستخدم"
    )

    password = st.text_input(
        "كلمة المرور",
        type="password"
    )

    city = st.selectbox(
        "المدينة",
        [
            "مكة",
            "جدة"
        ]
    )

    submitted = st.form_submit_button(
        "💾 إنشاء المدير",
        use_container_width=True
    )

if submitted:

    if not fullname or not username or not password:

        st.warning(
            "⚠️ يرجى تعبئة جميع الحقول"
        )

    else:

        try:

            add_user(
                username=username,
                password=password,
                fullname=fullname,
                role="admin",
                city=city
            )

            st.success(
                "✅ تم إنشاء حساب المدير بنجاح"
            )

            st.balloons()

            st.info(
                "يمكنك الآن تسجيل الدخول وحذف هذه الصفحة إذا أردت"
            )

        except Exception as e:

            st.error(
                f"❌ حدث خطأ: {e}"
            )
            