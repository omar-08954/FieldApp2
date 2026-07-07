import time
from io import BytesIO

import pandas as pd
import streamlit as st

from database.database import (
    add_task,
    delete_task,
    get_all_tasks,
    get_task_by_number,
    task_exists,
    update_task,
)
from ui import TASK_STATUSES, TASK_TYPES, init_page, page_header, require_login, task_dataframe, top_nav


init_page("لوحة المدير")
require_login(["admin"])
top_nav()
page_header("📋 لوحة المدير", "إدارة المهام، البحث، الاستيراد، التعديل، والحذف.")


def tasks_df():
    return pd.DataFrame(get_all_tasks())


df = tasks_df()
if df.empty:
    df = pd.DataFrame(columns=["id", "technician", "city", "task_number", "subscription_number", "task_type", "task_status", "notes"])

total = len(df)
done = int((df["task_status"] == "مزال").sum()) if total else 0
blocked = int((df["task_status"] == "عائق").sum()) if total else 0
c1, c2, c3 = st.columns(3)
c1.metric("إجمالي المهام", total)
c2.metric("المزالة", done)
c3.metric("العوائق", blocked)

tab_tasks, tab_import, tab_edit, tab_delete = st.tabs(["📋 المهام", "📥 استيراد وتصدير", "✏️ تعديل مهمة", "🗑 حذف مهمة"])

with tab_tasks:
    col1, col2, col3 = st.columns(3)
    with col1:
        keyword = st.text_input("بحث")
    with col2:
        status = st.selectbox("الحالة", ["الكل"] + TASK_STATUSES)
    with col3:
        task_type = st.selectbox("النوع", ["الكل"] + TASK_TYPES)
    filtered = df.copy()
    if keyword:
        mask = (
            filtered["task_number"].astype(str).str.contains(keyword, case=False, na=False)
            | filtered["subscription_number"].astype(str).str.contains(keyword, case=False, na=False)
            | filtered["technician"].astype(str).str.contains(keyword, case=False, na=False)
        )
        filtered = filtered[mask]
    if status != "الكل":
        filtered = filtered[filtered["task_status"] == status]
    if task_type != "الكل":
        filtered = filtered[filtered["task_type"] == task_type]
    task_dataframe(filtered)
    st.caption(f"عدد النتائج: {len(filtered)}")

with tab_import:
    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("اختر ملف Excel", type=["xlsx"])
        if uploaded:
            incoming = pd.read_excel(uploaded)
            st.dataframe(incoming.head(20), hide_index=True, use_container_width=True)
            if st.button("بدء الاستيراد", use_container_width=True):
                added = duplicated = 0
                with st.spinner("جاري استيراد المهام..."):
                    for _, row in incoming.iterrows():
                        number = str(row.get("رقم المهمة", "")).strip()
                        if not number or task_exists(number):
                            duplicated += 1
                            continue
                        add_task(
                            str(row.get("الفني", "")).strip() or "غير محدد",
                            str(row.get("المدينة", "")).strip(),
                            number,
                            str(row.get("رقم الاشتراك", "")).strip(),
                            str(row.get("نوع المهمة", "تقني")).strip(),
                            str(row.get("حالة المهمة", "عائق")).strip(),
                            str(row.get("الملاحظات", "")).strip(),
                        )
                        added += 1
                    time.sleep(0.4)
                st.success(f"✅ تمت إضافة {added} مهمة، وتجاهل {duplicated} مهمة مكررة.")
                st.rerun()
    with col2:
        output = BytesIO()
        export_df = df.drop(columns=["id"], errors="ignore")
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False)
        st.download_button(
            "تحميل ملف Excel",
            data=output.getvalue(),
            file_name="tasks.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

with tab_edit:
    search_number = st.text_input("البحث برقم المهمة", key="edit_search")
    if st.button("🔍 البحث", key="edit_btn", use_container_width=True):
        st.session_state.edit_task = get_task_by_number(search_number)
    task = st.session_state.get("edit_task")
    if task:
        with st.form("edit_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_number = st.text_input("رقم المهمة", value=task["task_number"])
                new_type = st.selectbox("نوع المهمة", TASK_TYPES, index=TASK_TYPES.index(task["task_type"]) if task["task_type"] in TASK_TYPES else 0)
            with col2:
                new_subscription = st.text_input("رقم الاشتراك", value=task["subscription_number"])
                new_status = st.selectbox("حالة المهمة", TASK_STATUSES, index=TASK_STATUSES.index(task["task_status"]) if task["task_status"] in TASK_STATUSES else 0)
            new_notes = st.text_area("الملاحظات", value=task.get("notes") or "", height=120)
            save = st.form_submit_button("💾 حفظ التعديلات", use_container_width=True)
        if save:
            if task_exists(new_number, exclude_id=task["id"]):
                st.error("رقم المهمة مستخدم في مهمة أخرى.")
            else:
                update_task(task["id"], new_number, new_subscription, new_type, new_status, new_notes)
                st.success("✅ تم حفظ التعديلات بنجاح.")
                del st.session_state.edit_task
                st.rerun()
    elif search_number:
        st.info("اضغط بحث لعرض بيانات المهمة.")

with tab_delete:
    delete_number = st.text_input("البحث برقم المهمة", key="delete_search")
    if st.button("🔍 البحث", key="delete_btn", use_container_width=True):
        st.session_state.delete_task = get_task_by_number(delete_number)
        st.session_state.confirm_delete_task = False
    task = st.session_state.get("delete_task")
    if task:
        task_dataframe(pd.DataFrame([task]))
        st.warning("هل أنت متأكد من حذف المهمة؟")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("نعم، حذف", use_container_width=True):
                delete_task(task["id"])
                st.success("✅ تم حذف المهمة بنجاح.")
                del st.session_state.delete_task
                st.rerun()
        with col2:
            if st.button("إلغاء", use_container_width=True):
                del st.session_state.delete_task
                st.rerun()
