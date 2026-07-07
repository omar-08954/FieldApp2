import streamlit as st

from database.database import create_tables, login_user
from ui import PAGES, init_page, logout, page_header


init_page("شركة الفكر الصاعد للمقاولات", "wide")
create_tables()


def login_screen():
    left, right = st.columns([1, 1.25], vertical_alignment="center")
    with left:
        st.image("images/logo.png", width=220)
        st.markdown(
            """
            <div class="hero">
                <h1>شركة الفكر الصاعد للمقاولات</h1>
                <div class="muted">منصة متابعة المهام والفنيين والمستودع</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("تسجيل الدخول")
        with st.form("login_form"):
            username = st.text_input("اسم المستخدم", placeholder="أدخل اسم المستخدم")
            password = st.text_input("كلمة المرور", type="password", placeholder="أدخل كلمة المرور")
            submitted = st.form_submit_button("🔑 تسجيل الدخول", use_container_width=True)
        if submitted:
            username = username.strip()
            password = password.strip()
            if not username or not password:
                st.warning("يرجى إدخال اسم المستخدم وكلمة المرور.")
            else:
                user = login_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.fullname = user["fullname"]
                    st.session_state.username = user["username"]
                    st.session_state.role = user["role"]
                    st.session_state.city = user.get("city") or ""
                    st.success("✅ تم تسجيل الدخول بنجاح")
                    st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة.")
        st.markdown("</div>", unsafe_allow_html=True)


def nav_card(label, page_key):
    if st.button(label, use_container_width=True):
        st.switch_page(PAGES[page_key])


def home_screen():
    page_header(
        "🏠 الرئيسية",
        f"مرحباً {st.session_state.fullname}، اختر القسم المطلوب للانتقال مباشرة.",
    )
    if st.session_state.role == "admin":
        cards = [
            ("📊 لوحة التحكم", "dashboard"),
            ("📋 لوحة المدير", "admin"),
            ("👷 الفنيين", "technician"),
            ("📊 التقارير", "reports"),
            ("📦 المستودع", "inventory"),
            ("👥 المستخدمون", "users"),
            ("⚙️ الإعدادات", "settings"),
            ("🔒 تغيير كلمة المرور", "settings"),
        ]
    else:
        cards = [
            ("👷 صفحة الفني", "technician"),
            ("🔒 تغيير كلمة المرور", "settings"),
        ]

    for row_start in range(0, len(cards), 3):
        cols = st.columns(3)
        for col, (label, page_key) in zip(cols, cards[row_start:row_start + 3]):
            with col:
                nav_card(label, page_key)

    st.divider()
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        logout()


if st.session_state.logged_in:
    home_screen()
else:
    login_screen()
