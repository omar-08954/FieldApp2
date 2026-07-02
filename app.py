import streamlit as st

from database.database import (
    create_tables,
    login_user
)

# ======================================
# إعداد الصفحة
# ======================================

st.set_page_config(
    page_title="شركة الفكر الصاعد للمقاولات",
    page_icon="🏗️",
    layout="centered"
)

# ======================================
# إنشاء الجداول
# ======================================

create_tables()

# ======================================
# Session State
# ======================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "fullname" not in st.session_state:
    st.session_state.fullname = ""

if "username" not in st.session_state:
    st.session_state.username = ""

if "role" not in st.session_state:
    st.session_state.role = ""

if "city" not in st.session_state:
    st.session_state.city = ""

# ======================================
# الشريط الجانبي
# ======================================

with st.sidebar:

    st.image(
        "images/logo.png",
        width=120
    )

    st.title("🏗️ FieldApp")

    st.divider()

    if st.session_state.logged_in:

        st.success(
            f"مرحباً {st.session_state.fullname}"
        )

        st.info(
            f"الصلاحية: {st.session_state.role}"
        )

        if st.button(
            "🚪 تسجيل الخروج",
            width="stretch"
        ):

            st.session_state.logged_in = False
            st.session_state.fullname = ""
            st.session_state.username = ""
            st.session_state.role = ""
            st.session_state.city = ""

            st.switch_page("app.py")

    else:

        st.info(
            "يرجى تسجيل الدخول"
        )

# ======================================
# الصفحة الرئيسية بعد تسجيل الدخول
# ======================================

if st.session_state.logged_in:

    col1, col2 = st.columns([1, 4])

with col1:
    st.image(
        "images/logo.png",
        width=100
    )

with col2:
    st.markdown(
        """
        <h1 style='margin-top:20px;'>
        شركة الفكر الصاعد للمقاولات
        </h1>
        """,
        unsafe_allow_html=True
    )

    st.success(
        f"مرحباً {st.session_state.fullname}"
    )

    st.info(
        "اختر الصفحة المطلوبة من القائمة الجانبية"
    )

    st.markdown("---")

    if st.session_state.role == "admin":

        st.subheader("👔 صلاحيات المدير")

        st.write("📊 Dashboard")
        st.write("👔 لوحة المدير")
        st.write("👥 إدارة المستخدمين")
        st.write("🛠️ صفحة الفني")
        st.write("🔑 تغيير كلمة المرور")
        st.write("📑 صفحة التقارير")

    else:

        st.subheader("👷 صلاحيات الفني")

        st.write("🛠️ صفحة الفني")
        st.write("🔑 تغيير كلمة المرور")

    st.stop()

# ======================================
# شاشة تسجيل الدخول
# ======================================

st.title(
    "🏗️ شركة الفكر الصاعد للمقاولات"
)

st.subheader("تسجيل الدخول")

username = st.text_input(
    "اسم المستخدم"
)

password = st.text_input(
    "كلمة المرور",
    type="password"
)

if st.button(
    "🔑 تسجيل الدخول",
    width="stretch"
):

    user = login_user(
        username,
        password
    )

    if user:

        st.session_state.logged_in = True
        st.session_state.fullname = user["fullname"]
        st.session_state.username = user["username"]
        st.session_state.role = user["role"]
        st.session_state.city = user["city"]

        st.success(
            "✅ تم تسجيل الدخول بنجاح"
        )

        st.rerun()

    else:

        st.error(
            "❌ اسم المستخدم أو كلمة المرور غير صحيحة"
        )
