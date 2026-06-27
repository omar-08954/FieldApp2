import streamlit as st

from database.database import change_password

# ======================================
# التحقق من تسجيل الدخول
# ======================================

if not st.session_state.get("logged_in", False):
    st.warning("يرجى تسجيل الدخول أولاً")
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

st.title("🔑 تغيير كلمة المرور")

st.write(
    f"المستخدم الحالي: {st.session_state.username}"
)

st.divider()

# ======================================
# تغيير كلمة المرور
# ======================================

new_password = st.text_input(
    "كلمة المرور الجديدة",
    type="password"
)

confirm_password = st.text_input(
    "تأكيد كلمة المرور الجديدة",
    type="password"
)

if st.button(
        "💾 حفظ كلمة المرور",
        use_container_width=True):

    if not new_password:

        st.error(
            "يرجى إدخال كلمة المرور الجديدة"
        )

    elif new_password != confirm_password:

        st.error(
            "كلمتا المرور غير متطابقتين"
        )

    else:

        change_password(
            st.session_state.username,
            new_password
        )

        st.success(
            "تم تغيير كلمة المرور بنجاح"
        )
        