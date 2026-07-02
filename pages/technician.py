import streamlit as st
import time

from database.database import (
    add_task,
    task_exists,
    get_today_tasks
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
        "ليس لديك صلاحية للوصول لهذه الصفحة"
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
        clear_on_submit=True):

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

    status = st.selectbox(
        "📌 حالة التنفيذ",
        [
            "مكتملة",
            "قيد التنفيذ",
            "مؤجلة",
            "العميل غير موجود",
            "يحتاج مراجعة"
        ]
    )

    notes = st.selectbox(
        "📝 حالة المهمة",
        [
            "",
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
            "⚠️ يرجى إدخال جميع البيانات المطلوبة"
        )

    elif task_exists(
            st.session_state.fullname,
            task_number,
            subscription_number,
            f"{task_type} - {status}",
            notes):

        st.error(
            "❌ هذه المهمة مسجلة مسبقاً"
        )

    else:

        add_task(
            technician=st.session_state.fullname,
            task_number=task_number,
            subscription_number=subscription_number,
            status=f"{task_type} - {status}",
            notes=notes
        )

        msg = st.success(
            "✅ تم تسجيل المهمة بنجاح"
        )

        # إبقاء الرسالة 3 ثوانٍ
        time.sleep(3)

        msg.empty()

        # الانتقال مباشرة للمهمة التالية
        st.rerun()

# ======================================
# مهمات اليوم
# ======================================

st.divider()

st.subheader("📅 مهمات اليوم")

today_tasks = get_today_tasks(
    st.session_state.fullname
)

if today_tasks:

    for task in today_tasks:

        with st.container(border=True):

            st.write(
                f"📋 رقم المهمة: "
                f"{task['task_number']}"
            )

            st.write(
                f"🔢 رقم الاشتراك: "
                f"{task['subscription_number']}"
            )

            st.write(
                f"📌 الحالة: "
                f"{task['status']}"
            )

            if task["notes"]:

                st.write(
                    f"📝 حالة المهمة: "
                    f"{task['notes']}"
                )

            st.caption(
                task["created_at"]
            )

else:

    st.info(
        "لا توجد مهمات اليوم"
    )
