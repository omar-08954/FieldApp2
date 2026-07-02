import streamlit as st

from database.database import add_user

# ======================================
# عنوان الصفحة
# ======================================

st.title("👔 إنشاء حساب مدير")

st.warning(
    "هذه الصفحة مؤقتة ويمكن حذفها بعد إنشاء المدير"
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
        "💾 إنشاء حساب المدير",
        use_container_width=True
    )

# ======================================
# إنشاء المدير
# ======================================

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
    use_container_width=True
):

    st.switch_page("app.py")
    