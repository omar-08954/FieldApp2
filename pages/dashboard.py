import streamlit as st
import pandas as pd

from database.database import get_all_tasks

# ======================================
# التحقق من تسجيل الدخول
# ======================================

if not st.session_state.get("logged_in", False):
    st.warning("يرجى تسجيل الدخول أولاً")
    st.stop()

# ======================================
# زر تسجيل الدخول والخروج
# ======================================

with st.sidebar:

    st.divider()

    if st.session_state.get("logged_in", False):

        if st.button(
            "🚪 تسجيل الخروج",
            use_container_width=True
        ):
            st.switch_page("app.py")

    else:

        if st.button(
            "🔑 تسجيل الدخول",
            use_container_width=True
        ):
            st.switch_page("app.py")

# ======================================
# عنوان الصفحة
# ======================================

st.title("📊 لوحة التحكم")
st.caption("شركة الفكر الصاعد للمقاولات")

# ======================================
# جلب البيانات
# ======================================

tasks = get_all_tasks()

if len(tasks) == 0:
    st.info("لا توجد بيانات حتى الآن")
    st.stop()

df = pd.DataFrame([dict(row) for row in tasks])

# ======================================
# الإحصائيات
# ======================================

total_tasks = len(df)

technical_tasks = len(
    df[df["task_type"] == "تقني"]
)

zera_tasks = len(
    df[df["task_type"] == "زيرا"]
)

checked_tasks = len(
    df[df["notes"] == "تم الفحص"]
)

obstacle_tasks = len(
    df[df["notes"] == "عائق"]
)

still_tasks = len(
    df[df["notes"] == "مزال"]
)

today = pd.Timestamp.now().strftime("%Y-%m-%d")

today_tasks = len(
    df[
        df["created_at"]
        .astype(str)
        .str.startswith(today)
    ]
)

# ======================================
# بطاقات الإحصائيات
# ======================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "📋 إجمالي المهام",
        total_tasks
    )

with col2:
    st.metric(
        "🛠️ مهام تقني",
        technical_tasks
    )

with col3:
    st.metric(
        "⚡ مهام زيرا",
        zera_tasks
    )

st.divider()

col4, col5, col6 = st.columns(3)

with col4:
    st.metric(
        "✅ تم الفحص",
        checked_tasks
    )

with col5:
    st.metric(
        "🚧 عائق",
        obstacle_tasks
    )

with col6:
    st.metric(
        "⏳ مزال",
        still_tasks
    )

st.divider()

col7, col8 = st.columns(2)


with col8:
    st.metric(
        "👷 عدد الفنيين",
        df["technician"].nunique()
    )

st.divider()

# ======================================
# الرسوم البيانية
# ======================================

st.subheader("📈 توزيع أنواع المهام")

task_chart = (
    df["task_type"]
    .value_counts()
)

st.bar_chart(task_chart)

st.subheader("📈 توزيع حالات المهام")

status_chart = (
    df["notes"]
    .value_counts()
)

st.bar_chart(status_chart)

st.divider()

# ======================================
# عرض آخر المهام
# ======================================

st.subheader("📋 آخر 10 مهام")

display_df = df.rename(
    columns={
        "technician": "الفني",
        "task_number": "رقم المهمة",
        "subscription_number": "رقم الاشتراك",
        "task_type": "نوع المهمة",
        "notes": "حالة المهمة",
        "created_at": "تاريخ الإنشاء"
    }
)

st.dataframe(
    display_df.head(10),
    use_container_width=True,
    hide_index=True
)
