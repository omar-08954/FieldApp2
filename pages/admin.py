import os
import streamlit as st
import pandas as pd

from database.database import (
    get_all_tasks,
    delete_task,
    update_task
)

# ======================================
# التحقق من تسجيل الدخول
# ======================================

if not st.session_state.get("logged_in", False):
    st.warning("يرجى تسجيل الدخول أولاً")
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("هذه الصفحة مخصصة للمدير فقط")
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

st.title("👔 لوحة المدير")

tasks = get_all_tasks()

if len(tasks) == 0:
    st.info("لا توجد مهام")
    st.stop()

df = pd.DataFrame([dict(row) for row in tasks])

# ======================================
# البحث
# ======================================

search = st.text_input("🔍 البحث")

if search:

    df = df[
        df["technician"].astype(str).str.contains(search, case=False)
        |
        df["task_number"].astype(str).str.contains(search, case=False)
        |
        df["subscription_number"].astype(str).str.contains(search, case=False)
    ]

# ======================================
# عرض المهام
# ======================================

st.subheader("📋 جميع المهام")

display_df = df.rename(
    columns={
        "technician": "الفني",
        "task_number": "رقم المهمة",
        "subscription_number": "رقم الاشتراك",
        "task_type": "نوع المهمة",
        "notes": "حالة المهمة",
        "created_at": "تاريخ الإنشاء"
    }
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

st.divider()

# ======================================
# تعديل مهمة
# ======================================

st.subheader("✏️ تعديل مهمة")

task_ids = df["id"].tolist()

selected_id = st.selectbox(
    "اختر رقم المهمة",
    task_ids
)

selected_task = df[
    df["id"] == selected_id
].iloc[0]

new_subscription = st.text_input(
    "رقم الاشتراك",
    value=selected_task["subscription_number"]
)

task_types = ["تقني", "زيرا"]

new_task_type = st.selectbox(
    "نوع المهمة",
    task_types,
    index=task_types.index(
        selected_task["task_type"]
    )
)

status_list = [
    "تم الفحص",
    "عائق",
    "مزال"
]

new_status = st.selectbox(
    "حالة المهمة",
    status_list,
    index=status_list.index(
        selected_task["notes"]
    )
)

if st.button("💾 حفظ التعديلات"):

    update_task(
        selected_id,
        new_subscription,
        new_task_type,
        new_status
    )

    st.success("تم تعديل المهمة بنجاح")
    st.rerun()

st.divider()

# ======================================
# حذف مهمة
# ======================================

st.subheader("🗑️ حذف مهمة")

delete_id = st.selectbox(
    "اختر المهمة للحذف",
    task_ids,
    key="delete_box"
)

if st.button("حذف المهمة"):

    delete_task(delete_id)

    st.success("تم حذف المهمة")
    st.rerun()

# ======================================
# تحميل Excel
# ======================================

st.divider()

os.makedirs(
    "exports",
    exist_ok=True
)

excel_path = "exports/all_tasks.xlsx"

display_df.to_excel(
    excel_path,
    index=False
)

with open(excel_path, "rb") as file:

    st.download_button(
        "📥 تحميل Excel",
        file,
        file_name="all_tasks.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    