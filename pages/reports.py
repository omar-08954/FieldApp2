import streamlit as st
import pandas as pd

from database.database import get_all_tasks

if not st.session_state.get("logged_in", False):
    st.warning("يرجى تسجيل الدخول أولاً")
    st.stop()

if st.session_state.role != "admin":
    st.error("ليس لديك صلاحية")
    st.stop()

st.title("📑 التقارير")

tasks = get_all_tasks()

if not tasks:
    st.info("لا توجد بيانات")
    st.stop()

df = pd.DataFrame([dict(task) for task in tasks])

tab1, tab2 = st.tabs([
    "🕋 تقارير مكة",
    "🌊 تقارير جدة"
])

with tab1:

    makkah = df[df["city"] == "مكة"]

    st.metric(
        "إجمالي مهام مكة",
        len(makkah)
    )

    st.dataframe(
        makkah,
        use_container_width=True
    )

    csv = makkah.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "📥 تحميل تقرير مكة",
        csv,
        "makkah_report.csv",
        "text/csv"
    )

with tab2:

    jeddah = df[df["city"] == "جدة"]

    st.metric(
        "إجمالي مهام جدة",
        len(jeddah)
    )

    st.dataframe(
        jeddah,
        use_container_width=True
    )

    csv = jeddah.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "📥 تحميل تقرير جدة",
        csv,
        "jeddah_report.csv",
        "text/csv"
    )
    