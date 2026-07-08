import time
from io import BytesIO

import pandas as pd
import streamlit as st

from database.database import (
    add_task,
    delete_task,
    get_task_by_search,
    search_tasks,
    task_exists,
    update_task,
)
from ui import TASK_STATUSES, TASK_TYPES, init_page, page_header, require_login, task_dataframe, top_nav


init_page("لوحة المدير")
require_login(["admin"])
top_nav()
page_header("📋 لوحة المدير", "إدارة المهام، البحث، الاستيراد، التعديل، والحذف.")


def load_tasks():
    return pd.DataFrame(search_tasks())


df = load_tasks()
if df.empty:
    df = pd.DataFrame(columns=["id", "technician", "task_number", "subscription_number", "task_type", "task_status"])

tab_manage, tab_data, tab_transfer = st.tabs(["📋 إدارة المهام", "✏️ إدارة البيانات", "📥 الاستيراد والتصدير"])

with tab_manage:
    total = len(df)
    done = int((df["task_status"] == "مزال").sum()) if total else 0
    blocked = int((df["task_status"] == "عائق").sum()) if total else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي المهام", total)
    c2.metric("المزالة", done)
    c3.metric("العوائق", blocked)

    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        keyword = st.text_input("بحث ذكي")
    with col2:
        status = st.selectbox("الحالة", ["الكل"] + TASK_STATUSES)
    with col3:
        task_type = st.selectbox("النوع", ["الكل"] + TASK_TYPES)

    filtered = pd.DataFrame(search_tasks(keyword, task_type=task_type, task_status=status))
    task_dataframe(filtered)
    st.caption(f"عدد النتائج: {len(filtered)}")

with tab_data:
    edit_col, delete_col = st.columns(2)

    with edit_col:
        st.subheader("✏️ تعديل مهمة")
        edit_keyword = st.text_input("بحث ذكي للتعديل", key="edit_search")
        if st.button("🔍 البحث", key="edit_btn", width="stretch"):
            st.session_state.edit_task = get_task_by_search(edit_keyword)
        task = st.session_state.get("edit_task")
        if task:
            with st.form("edit_form"):
                new_number = st.text_input("رقم المهمة", value=task["task_number"])
                new_subscription = st.text_input("رقم الاشتراك", value=task["subscription_number"])
                new_type = st.selectbox(
                    "نوع المهمة",
                    TASK_TYPES,
                    index=TASK_TYPES.index(task["task_type"]) if task["task_type"] in TASK_TYPES else 0,
                )
                new_status = st.selectbox(
                    "حالة المهمة",
                    TASK_STATUSES,
                    index=TASK_STATUSES.index(task["task_status"]) if task["task_status"] in TASK_STATUSES else 0,
                )
                save = st.form_submit_button("💾 حفظ التعديلات", width="stretch")
            if save:
                if task_exists(new_number, exclude_id=task["id"]):
                    st.error("رقم المهمة مستخدم في مهمة أخرى.")
                else:
                    with st.spinner("جاري حفظ التعديلات..."):
                        update_task(task["id"], new_number, new_subscription, new_type, new_status)
                        time.sleep(0.4)
                    st.success("✅ تم حفظ التعديلات بنجاح.")
                    del st.session_state.edit_task
                    st.rerun()
        elif edit_keyword:
            st.info("اكتب قيمة البحث ثم اضغط بحث.")

    with delete_col:
        st.subheader("🗑 حذف مهمة")
        delete_keyword = st.text_input("بحث ذكي للحذف", key="delete_search")
        if st.button("🔍 البحث", key="delete_btn", width="stretch"):
            st.session_state.delete_task = get_task_by_search(delete_keyword)
        task = st.session_state.get("delete_task")
        if task:
            task_dataframe(pd.DataFrame([task]))
            st.warning("هل أنت متأكد من حذف المهمة؟")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("نعم، حذف", width="stretch"):
                    with st.spinner("جاري حذف المهمة..."):
                        delete_task(task["id"])
                        time.sleep(0.4)
                    st.success("✅ تم حذف المهمة بنجاح.")
                    del st.session_state.delete_task
                    st.rerun()
            with col2:
                if st.button("إلغاء", width="stretch"):
                    del st.session_state.delete_task
                    st.rerun()
        elif delete_keyword:
            st.info("اكتب قيمة البحث ثم اضغط بحث.")

with tab_transfer:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📥 استيراد Excel")
        uploaded = st.file_uploader("اختر ملف Excel", type=["xlsx"])
        if uploaded:
            incoming = pd.read_excel(uploaded)
            preview_columns = ["الفني", "رقم المهمة", "رقم الاشتراك", "نوع المهمة", "حالة المهمة"]
            available_columns = [column for column in preview_columns if column in incoming.columns]
            st.dataframe(incoming[available_columns].head(20), hide_index=True, width="stretch")
            if st.button("بدء الاستيراد", width="stretch"):
                added = duplicated = 0
                with st.spinner("جاري استيراد المهام..."):
                    for _, row in incoming.iterrows():
                        number = str(row.get("رقم المهمة", "")).strip()
                        if not number or task_exists(number):
                            duplicated += 1
                            continue
                        add_task(
                            technician=str(row.get("الفني", "")).strip() or "غير محدد",
                            task_number=number,
                            subscription_number=str(row.get("رقم الاشتراك", "")).strip(),
                            task_type=str(row.get("نوع المهمة", "تقني")).strip(),
                            task_status=str(row.get("حالة المهمة", "عائق")).strip(),
                        )
                        added += 1
                    time.sleep(0.4)
                st.success(f"✅ تمت إضافة {added} مهمة، وتجاهل {duplicated} مهمة مكررة.")
                st.rerun()

    with col2:
        st.subheader("📤 تصدير Excel")
        output = BytesIO()
        export_df = df.drop(columns=["id"], errors="ignore")
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False)
        st.download_button(
            "تحميل ملف Excel",
            data=output.getvalue(),
            file_name="tasks.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
