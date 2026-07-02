import streamlit as st
from database.database import add_task

# التحقق من تسجيل الدخول
if not st.session_state.get("logged_in", False):
    st.warning("يرجى تسجيل الدخول أولاً")
    st.stop()

st.title("👷 صفحة الفني")

st.info(f"مرحباً {st.session_state.fullname}")

with st.form("task_form", clear_on_submit=True):

    task_number = st.text_input("📋 رقم المهمة")

    subscription_number = st.text_input("🔢 رقم الاشتراك")

    status = st.selectbox(
        "📌 حالة المهمة",
        [
            "مكتملة",
            "قيد التنفيذ",
            "مؤجلة",
            "العميل غير موجود",
            "يحتاج مراجعة"
        ]
    )

    notes = st.text_area("📝 حالة المهمة")

    submitted = st.form_submit_button(
        "💾 حفظ المهمة",
        use_container_width=True
    )

    if submitted:

        if not task_number or not subscription_number:

            st.warning("⚠️ يرجى إدخال جميع البيانات المطلوبة")

        else:

            try:

                add_task(
                    technician=st.session_state.fullname,
                    task_number=task_number,
                    subscription_number=subscription_number,
                    status=status,
                    notes=notes
                )

                st.success("✅ تم حفظ المهمة بنجاح")

            except Exception as e:
                st.error(f"❌ حدث خطأ: {e}")
                