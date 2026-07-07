import pandas as pd
import streamlit as st

from database.database import get_all_tasks
from ui import CITIES, init_page, page_header, require_login, task_dataframe, top_nav


init_page("التقارير")
require_login(["admin"])
top_nav()
page_header("📑 التقارير", "تقارير المدن والمهام قابلة للتصفية والتصدير.")

df = pd.DataFrame(get_all_tasks())
if df.empty:
    st.info("لا توجد بيانات.")
    st.stop()

city = st.selectbox("المدينة", ["الكل"] + CITIES)
filtered = df if city == "الكل" else df[df["city"] == city]

c1, c2, c3 = st.columns(3)
c1.metric("إجمالي النتائج", len(filtered))
c2.metric("مكة", int((df["city"] == "مكة").sum()))
c3.metric("جدة", int((df["city"] == "جدة").sum()))

task_dataframe(filtered)
csv = filtered.to_csv(index=False).encode("utf-8-sig")
st.download_button("📥 تحميل التقرير", csv, "tasks_report.csv", "text/csv", use_container_width=True)
