import streamlit as st
import time

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
# السماح للمدير والفني فقط
# ======================================

if st.session_state.get("role") not in [
    "admin",
    "technician"
]:

    st.error(
        "ليس لديك صلاحية للوصول لهذه الصفحة."
    )

    st.stop()

# ======================================
# عنوان الصفحة
# ======================================

st.title("🛠️ صفحة الفني")

st.success(
    f"مرحباً {st.session_state.fullname}"
)

# ======================================
# نموذج إضافة المهمة
# ======================================

with st.form(
    "task_form",
    clear_on_submit=True
):

    task_number = st.text_input(
        "📋 رقم المهمة"
    )

    subscription_number = st.text_input(
        "🔢 رقم الاشتراك"
    )

    task_type = st.selectbox(
        "🛠️ نوع المهمة",
        [
            "تقني",
            "زيرا"
        ]
    )

    task_status = st.selectbox(
        "📝 حالة المهمة",
        [
            "عائق",
            "تم الفحص",
            "مزال"
        ]
    )

    submitted = st.form_submit_button(
        "💾 حفظ المهمة",
        use_container_width=True
    )

# ======================================
# حفظ المهمة
# ======================================

if submitted:

    if not task_number or not subscription_number:

        st.warning(
            "⚠️ يرجى إدخال جميع البيانات المطلوبة."
        )

    elif task_exists(
        st.session_state.fullname,
        task_number,
        subscription_number,
        task_type,
        task_status
    ):

        st.error(
            "❌ هذه المهمة مسجلة مسبقاً."
        )

    else:

        add_task(
            technician=st.session_state.fullname,
            city=st.session_state.city,
            task_number=task_number,
            subscription_number=subscription_number,
            task_type=task_type,
            task_status=task_status
        )

        msg = st.success(
            "✅ تم تسجيل المهمة بنجاح."
        )

        time.sleep(3)

        msg.empty()

        st.rerun()

# ======================================
# العودة للرئيسية
# ======================================

st.divider()

if st.button(
    "🏠 العودة للرئيسية",
    use_container_width=True
):

    st.switch_page("app.py")

# ======================================
# تسجيل الخروج
# ======================================

if st.button(
    "🚪 تسجيل الخروج",
    use_container_width=True
):

    st.session_state.logged_in = False
    st.session_state.fullname = ""
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.city = ""

    st.switch_page("app.py")
    
