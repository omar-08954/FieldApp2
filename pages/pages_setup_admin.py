import streamlit as st
from database.database import (
    get_all_users,
    add_user
)

# ======================================
# التحقق من وجود مدير
# ======================================

users = get_all_users()

admin_exists = False

for user in users:
    if user["role"] == "admin":
        admin_exists = True
        break

# إذا كان هناك مدير بالفعل
if admin_exists:

    st.success("تم إنشاء حساب المدير بالفعل")

    st.info(
        "يمكنك حذف هذه الصفحة من المشروع الآن"
    )

    st.stop()

# ======================================
# إنشاء المدير الأول
# ======================================

st.title("👔 إنشاء حساب المدير الأول")

st.warning(
    "هذه الصفحة تعمل مرة واحدة فقط"
)

with st.form("create_admin"):

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

    submitted = st.form_submit_button(
        "💾 إنشاء حساب المدير",
        use_container_width=True
    )

if submitted:

    if not fullname or not username or not password:

        st.warning(
            "يرجى تعبئة جميع الحقول"
        )

    else:

        try:

            add_user(
                username=username,
                password=password,
                fullname=fullname,
                role="admin"
            )

            st.success(
                "✅ تم إنشاء حساب المدير بنجاح"
            )

            st.info(
                "يمكنك الآن حذف هذه الصفحة"
            )

            st.balloons()

        except Exception:

            st.error(
                "اسم المستخدم مستخدم مسبقاً"
            )
            