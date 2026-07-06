import streamlit as st
import pandas as pd
import time
from io import BytesIO

from database.database import (
    get_all_tasks,
    update_task,
    delete_task,
    task_exists,
    add_task
)

# ======================================
# التحقق من تسجيل الدخول
# ======================================

if not st.session_state.get("logged_in", False):

    st.warning(
        "يرجى تسجيل الدخول أولاً."
    )

    st.stop()

# ======================================
# صلاحيات المدير فقط
# ======================================

if st.session_state.role != "admin":

    st.error(
        "ليس لديك صلاحية للوصول لهذه الصفحة."
    )

    st.stop()

# ======================================
# عنوان الصفحة
# ======================================

st.title("👔 لوحة المدير")

st.caption(
    "إدارة جميع مهام الفنيين"
)

# ======================================
# جلب جميع المهام
# ======================================

tasks = get_all_tasks()

if tasks:

    df = pd.DataFrame(tasks)

else:

    df = pd.DataFrame(
        columns=[
            "id",
            "technician",
            "city",
            "task_number",
            "subscription_number",
            "status",
            "notes",
            "created_at"
        ]
    )

# ======================================
# الإحصائيات
# ======================================

total_tasks = len(df)

completed_tasks = 0

if len(df):

    completed_tasks = len(

        df[
            df["status"].astype(str).str.contains(
                "تم",
                case=False,
                na=False
            )
        ]

    )

remaining_tasks = total_tasks - completed_tasks

c1, c2, c3 = st.columns(3)

c1.metric(
    "📋 إجمالي المهام",
    total_tasks
)

c2.metric(
    "✅ المنجزة",
    completed_tasks
)

c3.metric(
    "📌 المتبقية",
    remaining_tasks
)

st.divider()

# ======================================
# التبويبات
# ======================================

tab_tasks, tab_edit, tab_delete = st.tabs(

    [

        "📋 المهام",

        "✏️ تعديل المهمة",

        "🗑 حذف المهمة"

    ]

)

# ======================================
# تبويب المهام
# ======================================

with tab_tasks:

    st.subheader("📋 إدارة المهام")

    # ======================================
    # أدوات Excel
    # ======================================

    col1, col2 = st.columns(2)

    # --------------------------------------
    # استيراد المهام
    # --------------------------------------

    with col1:

        st.markdown("### 📥 استيراد المهام")

        uploaded_file = st.file_uploader(
            "اختر ملف Excel",
            type=["xlsx"]
        )

        if uploaded_file is not None:

            try:

                excel_df = pd.read_excel(uploaded_file)

                st.success(
                    f"تم العثور على {len(excel_df)} مهمة."
                )

                st.markdown("### 👀 معاينة الملف")

                st.dataframe(
                    excel_df.head(20),
                    hide_index=True,
                    width="stretch"
                )

                if st.button(
                    "📥 بدء الاستيراد",
                    width="stretch"
                ):

                    with st.spinner(
                        "⏳ جاري استيراد المهام..."
                    ):

                        added = 0
                        duplicated = 0

                        for _, row in excel_df.iterrows():

                            technician = str(
                                row["الفني"]
                            ).strip()

                            task_number = str(
                                row["رقم المهمة"]
                            ).strip()

                            subscription_number = str(
                                row["رقم الاشتراك"]
                            ).strip()

                            task_type = str(
                                row["نوع المهمة"]
                            ).strip()

                            task_status = str(
                                row["حالة المهمة"]
                            ).strip()

                            if task_exists(
                                technician,
                                task_number,
                                subscription_number,
                                task_type,
                                task_status
                            ):

                                duplicated += 1

                                continue

                            add_task(
                                technician,
                                "",
                                task_number,
                                subscription_number,
                                task_type,
                                task_status
                            )

                            added += 1

                        time.sleep(1)

                    success = st.success(

                        f"""
✅ تمت إضافة {added} مهمة.

⚠️ تم تجاهل {duplicated} مهمة مكررة.
"""

                    )

                    time.sleep(3)

                    success.empty()

                    st.rerun()

            except Exception as e:

                st.error(
                    f"خطأ أثناء قراءة الملف:\n{e}"
                )

    # --------------------------------------
    # تصدير المهام
    # --------------------------------------

    with col2:

        st.markdown("### 📤 تصدير المهام")

        export_df = df.copy()

        export_df = export_df.drop(
            columns=[
                "id",
                "city",
                "created_at"
            ],
            errors="ignore"
        )

        export_df = export_df.rename(
            columns={
                "technician":"الفني",
                "task_number":"رقم المهمة",
                "subscription_number":"رقم الاشتراك",
                "status":"نوع المهمة",
                "notes":"حالة المهمة"
            }
        )

        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            export_df.to_excel(
                writer,
                index=False
            )

        st.download_button(

            "📤 تحميل ملف Excel",

            data=output.getvalue(),

            file_name="tasks.xlsx",

            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

            width="stretch"

        )

    st.divider()

    # ======================================
    # البحث
    # ======================================

    st.subheader("🔍 البحث")

    keyword = st.text_input(
        "ابحث برقم المهمة أو الاشتراك أو الفني"
    )

    filtered_df = df.copy()

    if keyword.strip():

        keyword = keyword.strip().lower()

        filtered_df = filtered_df[

            filtered_df.apply(

                lambda row:

                keyword in str(row["technician"]).lower()

                or

                keyword in str(row["task_number"]).lower()

                or

                keyword in str(row["subscription_number"]).lower(),

                axis=1

            )

        ]

    display_df = filtered_df.copy()

    display_df = display_df.drop(

        columns=[

            "id",

            "city",

            "created_at"

        ],

        errors="ignore"

    )

    display_df = display_df.rename(

        columns={

            "technician":"الفني",

            "task_number":"رقم المهمة",

            "subscription_number":"رقم الاشتراك",

            "status":"نوع المهمة",

            "notes":"حالة المهمة"

        }

    )

    st.dataframe(

        display_df,

        hide_index=True,

        width="stretch"

    )

    st.caption(

        f"عدد المهام: {len(display_df)}"

    )

# ======================================
# تبويب تعديل المهمة
# ======================================

with tab_edit:

    st.subheader("✏️ تعديل مهمة")

    task_number = st.text_input(
        "رقم المهمة",
        key="edit_task_number"
    )

    subscription_number = ""

    selected_task = None

    if st.button(
        "🔍 البحث",
        key="search_edit",
        width="stretch"
    ):

        search_df = df[
            df["task_number"].astype(str)
            == task_number.strip()
        ]

        if len(search_df) == 0:

            st.error(
                "❌ لم يتم العثور على المهمة."
            )

        elif len(search_df) == 1:

            selected_task = search_df.iloc[0]

            st.session_state.edit_task = selected_task

        else:

            st.warning(
                "⚠ يوجد أكثر من مهمة بنفس الرقم."
            )

            st.session_state.need_subscription = True

    # ======================================
    # إذا كان رقم المهمة مكررًا
    # ======================================

    if st.session_state.get(
        "need_subscription",
        False
    ):

        subscription_number = st.text_input(
            "رقم الاشتراك",
            key="edit_subscription"
        )

        if st.button(
            "🔍 متابعة",
            key="search_subscription",
            width="stretch"
        ):

            search_df = df[
                (df["task_number"].astype(str)
                 == task_number.strip())

                &

                (df["subscription_number"].astype(str)
                 == subscription_number.strip())
            ]

            if len(search_df) == 1:

                st.session_state.edit_task = search_df.iloc[0]

                st.session_state.need_subscription = False

            else:

                st.error(
                    "❌ رقم الاشتراك غير صحيح."
                )

    # ======================================
    # عرض بيانات المهمة
    # ======================================

    if "edit_task" in st.session_state:

        task = st.session_state.edit_task

        st.divider()

        technician = st.text_input(
            "الفني",
            value=task["technician"]
        )

        task_type = st.selectbox(

            "نوع المهمة",

            [

                "تقني",

                "زيرا"

            ],

            index=0
            if task["status"] == "تقني"
            else 1

        )

        task_status = st.text_input(

            "حالة المهمة",

            value=task["notes"]

        )

        if st.button(

            "💾 حفظ التعديلات",

            width="stretch"

        ):

            with st.spinner(

                "⏳ جاري حفظ التعديلات..."

            ):

                update_task(

        int(task["id"]),

        task["task_number"],

        task["subscription_number"],

        task_type,

        task_status

)

                time.sleep(1)

            msg = st.success(

                "✅ تم تعديل المهمة بنجاح."

            )

            time.sleep(3)

            msg.empty()

            del st.session_state["edit_task"]

            st.rerun()

# ======================================
# تبويب حذف المهمة
# ======================================

with tab_delete:

    st.subheader("🗑 حذف مهمة")

    delete_task_number = st.text_input(
        "رقم المهمة",
        key="delete_task_number"
    )

    if st.button(
        "🔍 البحث",
        key="search_delete",
        width="stretch"
    ):

        search_df = df[
            df["task_number"].astype(str)
            == delete_task_number.strip()
        ]

        if len(search_df) == 0:

            st.error(
                "❌ لم يتم العثور على المهمة."
            )

        elif len(search_df) == 1:

            st.session_state.delete_task = (
                search_df.iloc[0]
            )

            if "delete_need_subscription" in st.session_state:
                del st.session_state["delete_need_subscription"]

        else:

            st.warning(
                "⚠ يوجد أكثر من مهمة بنفس الرقم."
            )

            st.session_state.delete_need_subscription = True

    # ======================================
    # في حالة وجود أكثر من مهمة بنفس الرقم
    # ======================================

    if st.session_state.get(
        "delete_need_subscription",
        False
    ):

        delete_subscription = st.text_input(
            "رقم الاشتراك",
            key="delete_subscription"
        )

        if st.button(
            "🔍 متابعة",
            key="search_delete_subscription",
            width="stretch"
        ):

            search_df = df[
                (df["task_number"].astype(str)
                 == delete_task_number.strip())

                &

                (df["subscription_number"].astype(str)
                 == delete_subscription.strip())
            ]

            if len(search_df) == 1:

                st.session_state.delete_task = (
                    search_df.iloc[0]
                )

                st.session_state.delete_need_subscription = False

            else:

                st.error(
                    "❌ رقم الاشتراك غير صحيح."
                )

    # ======================================
    # عرض بيانات المهمة
    # ======================================

    if "delete_task" in st.session_state:

        task = st.session_state.delete_task

        st.divider()

        st.info(
            f"""
الفني : {task["technician"]}

رقم المهمة : {task["task_number"]}

رقم الاشتراك : {task["subscription_number"]}

نوع المهمة : {task["status"]}

حالة المهمة : {task["notes"]}
"""
        )

        confirm_delete = st.checkbox(
            "أؤكد حذف المهمة نهائياً"
        )

        if st.button(
            "🗑 حذف المهمة",
            width="stretch",
            disabled=not confirm_delete
        ):

            with st.spinner(
                "⏳ جاري حذف المهمة..."
            ):

                delete_task(
      int(task["id"])
   )

                time.sleep(1)

            msg = st.success(
                "✅ تم حذف المهمة بنجاح."
            )

            time.sleep(3)

            msg.empty()

            del st.session_state["delete_task"]

            st.rerun()

# ======================================
# تسجيل الخروج والعودة للرئيسية
# ======================================

st.divider()

col1, col2 = st.columns(2)

with col1:

    if st.button(
        "🏠 العودة للرئيسية",
        width="stretch"
    ):

        st.switch_page("app.py")

with col2:

    if st.button(
        "🚪 تسجيل الخروج",
        width="stretch"
    ):

        st.session_state.logged_in = False
        st.session_state.fullname = ""
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.city = ""

        st.switch_page("app.py")
