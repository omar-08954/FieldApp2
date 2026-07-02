import streamlit as st
from database.database import change_password

# التحقق من تسجيل الدخول
if not st.session_state.get("logged_in", False):
    st.warning("يرجى تسجيل الدخول أولاً")
    st.stop()

st.title("🔑 تغيير كلمة المرور")

new_password = st.text_input(
    "كلمة المرور الجديدة",
    type="password"
)

confirm_password = st.text_input(
    "تأكيد كلمة المرور",
    type="password"
)

if st.button(
    "💾 حفظ",
    use_container_width=True
):

    if not new_password or not confirm_password:
        st.warning("يرجى تعبئة جميع الحقول")

    elif new_password != confirm_password:
        st.error("كلمتا المرور غير متطابقتين")

    else:

        change_password(
            st.session_state.username,
            new_password
        )

        st.success("✅ تم تغيير كلمة المرور بنجاح")
        