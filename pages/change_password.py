import streamlit as st

from database.database import change_password

# ======================================
# التحقق من تسجيل الدخول
# ======================================

if not st.session_state.get("logged_in", False):
    st.warning("يرجى تسجيل الدخول أولاً")
    st.stop()

# ======================================
# العنوان
# ======================================

st.title("🔑 تغيير كلمة المرور")

st.info(
    f"المستخدم الحالي: {st.session_state.fullname}"
)

# ======================================
# نموذج تغيير كلمة المرور
# ======================================

with st.form("change_password_form"):

    current_password = st.text_input(
        "كلمة المرور الحالية",
        type="password"
    )

    new_password = st.text_input(
        "كلمة المرور الجديدة",
        type="password"
    )

    confirm_password = st.text_input(
        "تأكيد كلمة المرور الجديدة",
        type="password"
    )

    submitted = st.form_submit_button(
        "💾 حفظ",
        use_container_width=True
    )

# ======================================
# تغيير كلمة المرور
# ======================================

if submitted:

    if (
        not current_password
        or not new_password
        or not confirm_password
    ):

        st.warning(
            "⚠️ يرجى تعبئة جميع الحقول"
        )

    elif new_password != confirm_password:

        st.error(
            "❌ كلمتا المرور غير متطابقتين"
        )

    elif len(new_password) < 4:

        st.error(
            "❌ يجب أن تكون كلمة المرور 4 أحرف على الأقل"
        )

    else:

        change_password(
            st.session_state.username,
            new_password
        )

        st.success(
            "✅ تم تغيير كلمة المرور بنجاح"
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

    st.switch_page("app.py")
    