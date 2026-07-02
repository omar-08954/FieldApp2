import streamlit as st
import pandas as pd

from database.database import get_all_tasks

# ======================================
# التحقق من تسجيل الدخول
# ======================================

if not st.session_state.get("logged_in", False):
    st.warning("يرجى تسجيل الدخول أولاً")
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("ليس لديك صلاحية للوصول لهذه الصفحة")
    st.stop()

# ======================================
# العنوان
# ======================================

st.title("📊 Dashboard")

# ======================================
# جلب البيانات
# ======================================

tasks = get_all_tasks()

if not tasks:
    st.info("لا توجد مهام حتى الآن")
    st.stop()

df = pd.DataFrame(tasks)

# ======================================
# الإحصائيات الرئيسية
# ======================================

total_tasks = len(df)

technical_tasks = len(
    df[df["status"].astype(str)
    .str.contains("تقني", na=False)]
)

zira_tasks = len(
    df[df["status"].astype(str)
    .str.contains("زيرا", na=False)]
)

today_tasks = len(
    df[
        pd.to_datetime(df["created_at"])
        .dt.date ==
        pd.Timestamp.now().date()
    ]
)

best_tech = (
    df["technician"]
    .value_counts()
    .idxmax()
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("📋 إجمالي المهام", total_tasks)
col2.metric("🛠️ مهام تقني", technical_tasks)
col3.metric("🔧 مهام زيرا", zira_tasks)
col4.metric("📅 مهام اليوم", today_tasks)

st.divider()

# ======================================
# أفضل فني
# ======================================

st.subheader("🏆 أفضل فني")

st.success(best_tech)

st.divider()

# ======================================
# حالات المهام
# ======================================

obstacle = len(
    df[df["notes"].astype(str)
    .str.contains("عائق", na=False)]
)

checked = len(
    df[df["notes"].astype(str)
    .str.contains("تم الفحص", na=False)]
)

removed = len(
    df[df["notes"].astype(str)
    .str.contains("مزال", na=False)]
)

col1, col2, col3 = st.columns(3)

col1.metric("🚧 عائق", obstacle)
col2.metric("✔️ تم الفحص", checked)
col3.metric("🗑️ مزال", removed)

st.divider()

# ======================================
# البحث والتصفية
# ======================================

st.subheader("🔍 البحث والتصفية")

technicians = ["الكل"] + sorted(
    df["technician"].unique().tolist()
)

selected_tech = st.selectbox(
    "اختر الفني",
    technicians
)

search = st.text_input(
    "ابحث برقم المهمة أو رقم الاشتراك"
)

filtered_df = df.copy()

if selected_tech != "الكل":
    filtered_df = filtered_df[
        filtered_df["technician"] == selected_tech
    ]

if search:
    filtered_df = filtered_df[
        filtered_df.astype(str)
        .apply(
            lambda row:
            row.str.contains(
                search,
                case=False
            ).any(),
            axis=1
        )
    ]

st.divider()

# ======================================
# أداء الفنيين
# ======================================

st.subheader("📈 أداء الفنيين")

chart_df = (
    df.groupby("technician")
      .size()
      .reset_index(name="عدد المهام")
      .set_index("technician")
)

st.bar_chart(chart_df)

st.divider()

# ======================================
# عرض المهام
# ======================================

st.subheader("📋 المهام")

st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True
)

st.divider()

# ======================================
# تصدير Excel
# ======================================

csv = filtered_df.to_csv(
    index=False
).encode("utf-8-sig")

st.download_button(
    "📥 تحميل Excel",
    csv,
    "tasks.csv",
    "text/csv",
    use_container_width=True
)
