import pandas as pd
import streamlit as st

from database.database import get_all_tasks
from ui import TASK_STATUSES, TASK_TYPES, init_page, page_header, require_login, task_dataframe, top_nav


init_page("لوحة التحكم")
require_login(["admin"])
top_nav()
page_header("📊 لوحة التحكم", "نظرة تنفيذية على المهام وأداء الفنيين.")

df = pd.DataFrame(get_all_tasks())
if df.empty:
    st.info("لا توجد مهام حتى الآن.")
    st.stop()

total = len(df)
technical = int((df["task_type"] == "تقني").sum())
zira = int((df["task_type"] == "زيرا").sum())
best_tech = df["technician"].value_counts().idxmax() if total else "-"

c1, c2, c3, c4 = st.columns(4)
c1.metric("إجمالي المهام", total)
c2.metric("مهام تقني", technical)
c3.metric("مهام زيرا", zira)
c4.metric("أفضل فني", best_tech)

st.divider()
status_counts = df["task_status"].value_counts()
cols = st.columns(len(TASK_STATUSES))
for col, status in zip(cols, TASK_STATUSES):
    col.metric(status, int(status_counts.get(status, 0)))

st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    technician = st.selectbox("الفني", ["الكل"] + sorted(df["technician"].dropna().unique().tolist()))
with col2:
    task_type = st.selectbox("نوع المهمة", ["الكل"] + TASK_TYPES)
with col3:
    task_status = st.selectbox("حالة المهمة", ["الكل"] + TASK_STATUSES)
search = st.text_input("بحث برقم المهمة أو الاشتراك أو الفني")

filtered = df.copy()
if technician != "الكل":
    filtered = filtered[filtered["technician"] == technician]
if task_type != "الكل":
    filtered = filtered[filtered["task_type"] == task_type]
if task_status != "الكل":
    filtered = filtered[filtered["task_status"] == task_status]
if search:
    filtered = filtered[
        filtered["task_number"].astype(str).str.contains(search, case=False, na=False)
        | filtered["subscription_number"].astype(str).str.contains(search, case=False, na=False)
        | filtered["technician"].astype(str).str.contains(search, case=False, na=False)
    ]

st.subheader("📈 أداء الفنيين")
chart_df = df.groupby("technician").size().reset_index(name="عدد المهام").set_index("technician")
st.bar_chart(chart_df)

st.subheader("📋 المهام")
task_dataframe(filtered)
