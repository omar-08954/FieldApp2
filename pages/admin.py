import streamlit as st
import pandas as pd

from database.database import (
    get_all_tasks,
    get_all_users,
    update_task,
    delete_task
)

# ======================================
# التحقق من تسجيل الدخول
# ======================================

if not st.session_state.get("logged_in", False):
    st.warning("يرجى تسجيل الدخول أولاً")
    st.stop()

# ======================================
# السماح للمدير فقط
# ======================================

if st.session_state.get("role") != "admin":
    st.error("ليس لديك صلاحية للوصول لهذه الصفحة")
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

    df = pd.DataFrame([dict(task) for task in tasks])

    # ======================================
    # الإحصائيات
    # ======================================

    total_tasks = len(df)

    technical_tasks = len(
        df[
            df["status"]
            .astype(str)
            .str.contains("تقني", na=False)
        ]
    )

    zira_tasks = len(
        df[
            df["status"]
            .astype(str)
            .str.contains("زيرا", na=False)
        ]
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "📋 إجمالي المهام",
        total_tasks
    )

    col2.metric(
        "🛠️ مهام تقني",
        technical_tasks
    )

    col3.metric(
        "🔧 مهام زيرا",
        zira_tasks
    )

    st.divider()

    # ======================================
    # عرض المهام
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
            value=str(selected_task["task_number"])
        )

        subscription_number = st.text_input(
            "رقم الاشتراك",
            value=str(selected_task["subscription_number"])
        )

        status = st.selectbox(
            "نوع المهمة",
            ["تقني", "زيرا"],
            index=0 if selected_task["status"] == "تقني" else 1
        )

        notes = st.selectbox(
            "حالة المهمة",
            ["", "عائق", "تم الفحص", "مزال"],
            index=["", "عائق", "تم الفحص", "مزال"].index(
                selected_task["notes"]
            )
            if selected_task["notes"] in
            ["", "عائق", "تم الفحص", "مزال"]
            else 0
        )

        submitted = st.form_submit_button(
            "💾 حفظ التعديلات"
        )

        if submitted:

            update_task(
                selected_id,
                task_number,
                subscription_number,
                status,
                notes
            )

            st.success(
                "✅ تم تعديل المهمة بنجاح"
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

# ======================================
# تسجيل الخروج
# ======================================

st.divider()

if st.button(
    "🚪 تسجيل الخروج والعودة للرئيسية",
    width="stretch"
):

    st.session_state.logged_in = False
    st.session_state.fullname = ""
    st.session_state.username = ""
    st.session_state.role = ""

    st.switch_page("app.py")
