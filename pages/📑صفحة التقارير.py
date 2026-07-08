import pandas as pd
import streamlit as st

from database.database import search_tasks
from ui import TASK_STATUSES, TASK_TYPES, init_page, page_header, require_login, task_dataframe, top_nav


init_page("التقارير")
require_login(["admin"])
top_nav()
page_header("📑 التقارير", "تقارير المهام حسب النوع والحالة مع إمكانية التصدير.")

df = pd.DataFrame(search_tasks())
if df.empty:
    st.info("لا توجد بيانات.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    task_type = st.selectbox("نوع المهمة", ["الكل"] + TASK_TYPES)
with col2:
    task_status = st.selectbox("حالة المهمة", ["الكل"] + TASK_STATUSES)
search = st.text_input("بحث ذكي برقم المهمة أو الاشتراك أو نوع المهمة أو حالتها")

filtered = pd.DataFrame(search_tasks(search, task_type=task_type, task_status=task_status))

c1, c2, c3 = st.columns(3)
c1.metric("إجمالي النتائج", len(filtered))
c2.metric("مهام تقني", int((filtered["task_type"] == "تقني").sum()) if not filtered.empty else 0)
c3.metric("مهام زيرا", int((filtered["task_type"] == "زيرا").sum()) if not filtered.empty else 0)

task_dataframe(filtered)
csv = filtered.to_csv(index=False).encode("utf-8-sig")
st.download_button("📥 تحميل التقرير", csv, "tasks_report.csv", "text/csv", width="stretch")
