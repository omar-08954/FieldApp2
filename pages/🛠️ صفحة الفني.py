import time

import streamlit as st

from database.database import add_task, task_exists
from ui import TASK_STATUSES, TASK_TYPES, init_page, page_header, require_login, top_nav


init_page("صفحة الفني")
require_login(["admin", "technician"])
top_nav()
page_header("👷 صفحة الفني", "تسجيل المهام اليومية بسرعة وبدون تكرار رقم المهمة.")

with st.form("task_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        task_number = st.text_input("رقم المهمة")
        task_type = st.selectbox("نوع المهمة", TASK_TYPES)
    with col2:
        subscription_number = st.text_input("رقم الاشتراك")
        task_status = st.selectbox("حالة المهمة", TASK_STATUSES)
    notes = st.text_area("الملاحظات", height=110)
    submitted = st.form_submit_button("💾 تسجيل المهمة", use_container_width=True)

if submitted:
    task_number = task_number.strip()
    subscription_number = subscription_number.strip()
    if not task_number or not subscription_number:
        st.warning("يرجى إدخال رقم المهمة ورقم الاشتراك.")
    elif task_exists(task_number):
        st.error("❌ لا يمكن إضافة نفس رقم المهمة مرتين.")
    else:
        with st.spinner("جاري تسجيل المهمة..."):
            add_task(
                technician=st.session_state.fullname,
                city=st.session_state.city,
                task_number=task_number,
                subscription_number=subscription_number,
                task_type=task_type,
                task_status=task_status,
                notes=notes,
            )
            time.sleep(0.4)
        st.success("✅ تم تسجيل المهمة بنجاح")
