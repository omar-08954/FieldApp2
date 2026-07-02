# pages/admin.py

import streamlit as st
import pandas as pd

from database.database import (
    get_all_tasks,
    get_all_users,
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
    st.error("ليس لديك صلاحية الوصول لهذه الصفحة")
    st.stop()

# ======================================
# عنوان الصفحة
# ======================================

st.title("👔 لوحة المدير")

# ======================================
# جلب المهام
# ======================================

tasks = get_all_tasks()

if tasks:

    df = pd.DataFrame(tasks)

    # ======================================
    # الإحصائيات
    # ======================================

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "إجمالي المهام",
        len(df)
    )

    col2.metric(
        "المكتملة",
        len(
            df[df["status"].astype(str)
            .str.contains("مكتملة", na=False)]
        )
    )

    col3.metric(
        "قيد التنفيذ",
        len(
            df[df["status"].astype(str)
            .str.contains("قيد التنفيذ", na=False)]
        )
    )

    col4.metric(
        "المؤجلة",
        len(
            df[df["status"].astype(str)
            .str.contains("مؤجلة", na=False)]
        )
    )

    st.divider()

    # ======================================
    # عرض جميع المهام
    # ======================================

    st.subheader("📋 جميع المهام")

    st.dataframe(
        df,
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
        "اختر المهمة",
        task_ids
    )

    selected_task = (
        df[df["id"] == selected_id]
        .iloc[0]
    )

    with st.form("edit_task_form"):

        task_number = st.text_input(
            "رقم المهمة",
            value=selected_task["task_number"]
        )

        subscription_number = st.text_input(
            "رقم الاشتراك",
            value=selected_task["subscription_number"]
        )

        status = st.text_input(
            "الحالة",
            value=selected_task["status"]
        )

        notes = st.text_input(
            "حالة المهمة",
            value=selected_task["notes"]
            if selected_task["notes"]
            else ""
        )

        update_btn = st.form_submit_button(
            "💾 حفظ التعديلات"
        )

        if update_btn:

            update_task(
                selected_id,
                task_number,
                subscription_number,
                status,
                notes
            )

            st.success(
                "✅ تم تحديث المهمة بنجاح"
            )

            st.rerun()

    st.divider()

    # ======================================
    # حذف مهمة
    # ======================================

    st.subheader("🗑️ حذف مهمة")

    delete_id = st.selectbox(
        "اختر المهمة المراد حذفها",
        task_ids,
        key="delete_task"
    )

    if st.button(
        "🗑️ حذف المهمة",
        use_container_width=True
    ):

        delete_task(delete_id)

        st.success(
            "✅ تم حذف المهمة بنجاح"
        )

        st.rerun()

    st.divider()

    # ======================================
    # تحميل Excel
    # ======================================

    csv = df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "📥 تحميل Excel",
        csv,
        "tasks.csv",
        "text/csv",
        use_container_width=True
    )

else:

    st.info("لا توجد مهام")

# ======================================
# المستخدمون
# ======================================

st.divider()

st.subheader("👥 المستخدمون")

users = get_all_users()

if users:

    users_df = pd.DataFrame(users)

    st.dataframe(
        users_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info("لا يوجد مستخدمون")
    