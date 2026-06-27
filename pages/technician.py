import streamlit as st

from database.database import (
    add_task,
    task_exists
)

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

st.title("🛠️ صفحة الفني")

st.write(
    f"مرحبًا {st.session_state.fullname}"
)

st.divider()

# ======================================
# نموذج إضافة مهمة
# ======================================

task_number = st.text_input(
    "رقم المهمة"
)

subscription_number = st.text_input(
    "رقم الاشتراك"
)

task_type = st.selectbox(
    "نوع المهمة",
    [
        "تقني",
        "زيرا"
    ]
)

task_status = st.selectbox(
    "حالة المهمة",
    [
        "تم الفحص",
        "عائق",
        "مزال"
    ]
)

if st.button(
    "💾 حفظ المهمة",
    use_container_width=True
):

    if not task_number or not subscription_number:

        st.error(
            "يرجى إدخال جميع البيانات"
        )

    elif task_exists(task_number):

        st.warning(
            "رقم المهمة موجود مسبقًا"
        )

    else:

        add_task(
            st.session_state.fullname,
            task_number,
            subscription_number,
            task_type,
            task_status
        )

        st.success(
            "تم حفظ المهمة بنجاح"
        )

        st.rerun()
        