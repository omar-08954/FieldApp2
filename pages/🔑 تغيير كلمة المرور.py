import streamlit as st

from database.database import change_password, check_current_password
from ui import init_page, page_header, require_login, top_nav


init_page("تغيير كلمة المرور")
require_login(["admin", "technician"])
top_nav()
page_header("🔒 تغيير كلمة المرور", f"المستخدم الحالي: {st.session_state.fullname}")

with st.form("change_password_form"):
    current_password = st.text_input("كلمة المرور الحالية", type="password")
    new_password = st.text_input("كلمة المرور الجديدة", type="password")
    confirm_password = st.text_input("تأكيد كلمة المرور الجديدة", type="password")
    submitted = st.form_submit_button("💾 حفظ", use_container_width=True)

if submitted:
    current_password = current_password.strip()
    new_password = new_password.strip()
    confirm_password = confirm_password.strip()
    if not current_password or not new_password or not confirm_password:
        st.warning("يرجى تعبئة جميع الحقول.")
    elif new_password != confirm_password:
        st.error("كلمتا المرور غير متطابقتين.")
    elif len(new_password) < 4:
        st.error("يجب أن تكون كلمة المرور 4 أحرف على الأقل.")
    elif not check_current_password(st.session_state.username, current_password):
        st.error("كلمة المرور الحالية غير صحيحة.")
    else:
        change_password(st.session_state.username, new_password)
        st.success("✅ تم تغيير كلمة المرور بنجاح.")
