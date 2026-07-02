import streamlit as st

from database.database import add_user

# ======================================
# عنوان الصفحة
# ======================================

st.title("👔 إنشاء حساب مدير")

st.info(
    "يمكنك إنشاء أي عدد من حسابات المديرين من هذه الصفحة"
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
        use_container_width=True
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

            st.success(
                "✅ تم إنشاء حساب المدير بنجاح"
            )

            st.balloons()

        except Exception:

            st.error(
                "❌ اسم المستخدم مستخدم مسبقاً"
            )

# ======================================
# العودة للصفحة الرئيسية
# ======================================

st.divider()

if st.button(
    "🏠 العودة للرئيسية",
    width="stretch"
):

    st.switch_page("app.py")
    