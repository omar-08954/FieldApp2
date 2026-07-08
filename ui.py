import streamlit as st


TASK_TYPES = ["تقني", "زيرا"]
TASK_STATUSES = ["عائق", "تم الفحص", "مزال"]


PAGES = {
    "home": "app.py",
    "dashboard": "pages/📊 لوحة التحكم.py",
    "admin": "pages/👔 لوحة المدير.py",
    "technician": "pages/🛠️ صفحة الفني.py",
    "reports": "pages/📑صفحة التقارير.py",
    "inventory": "pages/📦 المستودع.py",
    "users": "pages/👥 إدارة المستخدمين.py",
    "change_password": "pages/🔑 تغيير كلمة المرور.py",
}


def init_page(title="FieldApp", layout="wide"):
    st.set_page_config(page_title=title, page_icon="🏗️", layout=layout)
    inject_style()
    init_session()


def init_session():
    defaults = {
        "logged_in": False,
        "fullname": "",
        "username": "",
        "role": "",
        "city": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def inject_style():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
        html, body, [class*="css"], .stApp {
            direction: rtl;
            font-family: 'Tajawal', system-ui, sans-serif;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(34, 197, 94, .08), transparent 32rem),
                linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
            color: #172033;
        }
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {
            display: none !important;
        }
        .block-container {
            padding-top: 1.4rem;
            max-width: 1180px;
        }
        h1, h2, h3 {
            color: #172033;
            font-weight: 800 !important;
            letter-spacing: 0;
        }
        .hero, .panel {
            background: rgba(255,255,255,.92);
            border: 1px solid #dbe3ef;
            border-radius: 8px;
            padding: 1.35rem;
            box-shadow: 0 14px 34px rgba(15, 23, 42, .08);
        }
        .hero {
            margin-bottom: 1rem;
        }
        .muted {
            color: #64748b;
            font-size: .98rem;
        }
        div.stButton > button, div.stDownloadButton > button {
            border-radius: 8px;
            border: 1px solid #0f766e;
            background: #0f766e;
            color: white;
            min-height: 2.85rem;
            font-weight: 700;
            transition: transform .12s ease, box-shadow .12s ease;
        }
        div.stButton > button:hover, div.stDownloadButton > button:hover {
            border-color: #115e59;
            background: #115e59;
            color: white;
            transform: translateY(-1px);
            box-shadow: 0 10px 22px rgba(15, 118, 110, .18);
        }
        div.stButton > button[kind="secondary"] {
            background: #ffffff;
            color: #0f766e;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #dbe3ef;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 8px 22px rgba(15, 23, 42, .06);
        }
        [data-testid="stDataFrame"] {
            border: 1px solid #dbe3ef;
            border-radius: 8px;
            overflow: hidden;
        }
        .top-nav {
            background: #ffffff;
            border: 1px solid #dbe3ef;
            border-radius: 8px;
            padding: .85rem 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 10px 26px rgba(15, 23, 42, .06);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def logout():
    for key in ["logged_in", "fullname", "username", "role", "city"]:
        st.session_state[key] = False if key == "logged_in" else ""

    st.session_state.clear()

    st.switch_page("app.py")


def require_login(roles=None):
    init_session()

    if not st.session_state.get("logged_in", False):
        st.switch_page("app.py")
        st.stop()

    if roles and st.session_state.get("role") not in roles:
        st.switch_page("app.py")
        st.stop()

def top_nav():
    st.markdown('<div class="top-nav">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(
            f"**{st.session_state.get('fullname', '')}**  \n"
            f"<span class='muted'>الصلاحية: {st.session_state.get('role', '')}</span>",
            unsafe_allow_html=True,
        )
    with col2:
        if st.button("🏠 الرئيسية", width="stretch"):
            st.switch_page(PAGES["home"])
    with col3:
        if st.button("🚪 تسجيل الخروج", width="stretch"):
            logout()
    st.markdown("</div>", unsafe_allow_html=True)


def page_header(title, caption=""):
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.title(title)
    if caption:
        st.markdown(f"<div class='muted'>{caption}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def task_dataframe(df):
    if df.empty:
        st.info("لا توجد بيانات للعرض.")
        return
    display = df.rename(
        columns={
            "id": "المعرف",
            "technician": "الفني",
            "task_number": "رقم المهمة",
            "subscription_number": "رقم الاشتراك",
            "task_type": "نوع المهمة",
            "task_status": "حالة المهمة",
        }
    )
    st.dataframe(display, hide_index=True, width="stretch")
