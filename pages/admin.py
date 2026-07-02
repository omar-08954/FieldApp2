import streamlit as st
import pandas as pd

from database.database import (
    get_all_tasks,
    get_all_users
)

# التحقق من تسجيل الدخول
if not st.session_state.get("logged_in", False):
    st.warning("يرجى تسجيل الدخول أولاً")
    st.stop()

# السماح للمدير فقط
if st.session_state.role != "admin":
    st.error("ليس لديك صلاحية للوصول لهذه الصفحة")
    st.stop()

st.title("👔 لوحة المدير")

# ======================================
# المهام
# ======================================

tasks = get_all_tasks()

if tasks:

    df = pd.DataFrame(tasks)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "إجمالي المهام",
        len(df)
    )

    col2.metric(
        "المكتملة",
        len(df[df["status"].str.contains("مكتملة")])
    )

    col3.metric(
        "قيد التنفيذ",
        len(df[df["status"].str.contains("قيد التنفيذ")])
    )

    st.subheader("📋 جميع المهام")

    st.dataframe(
        df,
        use_container_width=True
    )

    csv = df.to_csv(index=False).encode("utf-8-sig")

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
        use_container_width=True
    )

else:
    st.info("لا يوجد مستخدمون")
    