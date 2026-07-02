import streamlit as st
import time

from database.database import add_user

# ======================================
# عنوان الصفحة
# ======================================

st.title("👔 إنشاء حساب مدير")

st.warning(
    "⚠️ هذه صفحة مؤقتة لإنشاء حسابات المدير"
)

# ======================================
# نموذج إنشاء المدير
# ======================================

with st.form(
    "create_admin_form",
    clear_on_submit=True
):

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
        width="stretch"
    )

# ======================================
# حفظ المدير
# ======================================

if submitted:

    if not fullname or not username or not password:

        st.warning(
            "⚠️ يرجى تعبئة جميع الحقول"
        )

    elif len(password) < 4:

        st.error(
            "❌ يجب أن تكون كلمة المرور 4 أحرف على الأقل"
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

            msg = st.success(
                "✅ تم إنشاء حساب المدير بنجاح"
            )

            st.balloons()

            time.sleep(3)

            msg.empty()

            st.rerun()

        except Exception as e:

            st.error(
                f"❌ {e}"
            )

# ======================================
# العودة للرئيسية
# ======================================

st.divider()

if st.button(
    "🏠 العودة للرئيسية",
    width="stretch"
):

    st.switch_page("app.py")
