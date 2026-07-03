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

# تحويل البيانات بشكل صحيح
df = pd.DataFrame([dict(task) for task in tasks])

# ======================================
# الإحصائيات الرئيسية
# ======================================

total_tasks = len(df)

technical_tasks = len(
    df[
        df["status"]
        .astype(str)
        .str.contains("تقني", na=False)
    ]
)

zira_tasks = len(
    df[
        df["status"]
        .astype(str)
        .str.contains("زيرا", na=False)
    ]
)

best_tech = (
    df["technician"]
    .value_counts()
    .idxmax()
)

col1, col2, col3 = st.columns(3)

col1.metric(
    "📋 إجمالي المهام",
    total_tasks
)

col2.metric(
    "🛠️ مهام تقني",
    technical_tasks
)

col3.metric(
    "🔧 مهام زيرا",
    zira_tasks
)

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
    df[
        df["notes"]
        .astype(str)
        .str.contains("عائق", na=False)
    ]
)

checked = len(
    df[
        df["notes"]
        .astype(str)
        .str.contains("تم الفحص", na=False)
    ]
)

removed = len(
    df[
        df["notes"]
        .astype(str)
        .str.contains("مزال", na=False)
    ]
)

col1, col2, col3 = st.columns(3)

col1.metric(
    "🚧 عائق",
    obstacle
)

col2.metric(
    "✔️ تم الفحص",
    checked
)

col3.metric(
    "🗑️ مزال",
    removed
)

st.divider()

# ======================================
# البحث والتصفية
# ======================================

st.subheader("🔍 البحث والتصفية")

technicians = ["الكل"] + sorted(
    df["technician"].dropna().unique().tolist()
)

selected_tech = st.selectbox(
    "اختر الفني",
    technicians
)

search = st.text_input(
    "ابحث برقم المهمة أو رقم الاشتراك أو اسم الفني"
)

filtered_df = df.copy()

# فلترة حسب الفني

if selected_tech != "الكل":

    filtered_df = filtered_df[
        filtered_df["technician"] == selected_tech
    ]

# البحث

if search:

    filtered_df = filtered_df[
        filtered_df["task_number"]
            .astype(str)
            .str.contains(search, case=False, na=False)

        |

        filtered_df["subscription_number"]
            .astype(str)
            .str.contains(search, case=False, na=False)

        |

        filtered_df["technician"]
            .astype(str)
            .str.contains(search, case=False, na=False)
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
    width="stretch",
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
    width="stretch"
)

st.divider()

# ======================================
# تسجيل الخروج
# ======================================

if st.button(
    "🚪 تسجيل الخروج والعودة للرئيسية",
    width="stretch"
):

    st.session_state.logged_in = False
    st.session_state.fullname = ""
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.city = ""

    st.switch_page("app.py")
