import datetime
import time
from contextlib import contextmanager

import streamlit as st
from difflib import SequenceMatcher


TASK_TYPES = ["تقني", "زيرا"]
TASK_STATUSES = ["عائق", "تم الفحص", "مزال"]


@contextmanager
def timed_spinner(message, min_seconds=1.0):
    """Same as st.spinner(message), except: if the wrapped operation
    finishes very quickly (< ~1 second) the spinner stays visible for
    about a second so the user gets clear feedback that something
    happened, instead of a flash. If the operation naturally takes
    longer than that, it disappears immediately with no extra delay."""
    with st.spinner(message):
        start = time.time()
        yield
        elapsed = time.time() - start
        if elapsed < min_seconds:
            time.sleep(min_seconds - elapsed)


def confirm_delete_button(key_prefix, selected_ids, button_label, confirm_noun):
    """Two-step delete confirmation. Shows the delete button; once
    pressed, shows a warning with the selected count plus Confirm/Cancel
    buttons, and only returns True on the run where the user presses
    Confirm (caller performs the actual deletion at that point)."""
    pending_key = f"{key_prefix}_confirm_pending"
    if st.button(button_label, use_container_width=True, disabled=not selected_ids, key=f"{key_prefix}_delete_btn"):
        st.session_state[pending_key] = True

    if st.session_state.get(pending_key) and selected_ids:
        st.warning(f"سيتم حذف {len(selected_ids)} {confirm_noun}. هل أنت متأكد؟")
        c1, c2 = st.columns(2)
        with c1:
            confirmed = st.button("✅ تأكيد الحذف", key=f"{key_prefix}_confirm_yes", use_container_width=True)
        with c2:
            cancelled = st.button("❌ إلغاء", key=f"{key_prefix}_confirm_no", use_container_width=True)
        if cancelled:
            st.session_state.pop(pending_key, None)
            st.rerun()
        if confirmed:
            st.session_state.pop(pending_key, None)
            return True
    return False


def selectable_table(df, id_column, display_columns, key_prefix):
    """Render a full table using st.data_editor with a 'تحديد' checkbox
    column, plus two explicit buttons ('تحديد الكل' / 'إلغاء التحديد').
    Returns the list of ids the user has checked. Used for the
    multi-select delete tables (tasks / users / materials)."""
    if df.empty:
        st.info("لا توجد بيانات لعرضها.")
        return []

    ids = df[id_column].tolist()
    state_key = f"{key_prefix}_selection"
    if state_key not in st.session_state or set(st.session_state[state_key].keys()) != set(ids):
        st.session_state[state_key] = {row_id: False for row_id in ids}

    col1, col2 = st.columns(2)
    with col1:
        if st.button("☑ تحديد الكل", key=f"{key_prefix}_select_all_btn", use_container_width=True):
            st.session_state[state_key] = {row_id: True for row_id in ids}
            st.rerun()
    with col2:
        if st.button("⬜ إلغاء التحديد", key=f"{key_prefix}_deselect_all_btn", use_container_width=True):
            st.session_state[state_key] = {row_id: False for row_id in ids}
            st.rerun()

    table = df[[id_column] + list(display_columns.keys())].copy()
    table.insert(0, "تحديد", table[id_column].map(st.session_state[state_key]))
    table = table.rename(columns=display_columns)

    edited = st.data_editor(
        table,
        hide_index=True,
        use_container_width=True,
        key=f"{key_prefix}_editor",
        column_config={
            "تحديد": st.column_config.CheckboxColumn("تحديد"),
            id_column: st.column_config.NumberColumn(disabled=True),
        },
        disabled=list(display_columns.values()),
    )

    # مزامنة أي تحديد يدوي داخل الجدول مع حالة التحديد المحفوظة
    for _, r in edited.iterrows():
        st.session_state[state_key][r[id_column]] = bool(r["تحديد"])

    selected_ids = [row_id for row_id, checked in st.session_state[state_key].items() if checked]
    return selected_ids


def fuzzy_series_mask(series, keyword, threshold=0.6):
    """Approximate (typo-tolerant) fallback matching for client-side
    text filters. Used only when an exact `.str.contains` filter finds
    nothing, so exact-match behavior stays exactly as it was."""
    keyword = str(keyword or "").strip().lower()
    if not keyword:
        return series.apply(lambda _: False)

    def _match(value):
        value = str(value or "").strip().lower()
        if not value:
            return False
        if keyword in value or value in keyword:
            return True
        return SequenceMatcher(None, keyword, value).ratio() >= threshold

    return series.apply(_match)


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
        "current_page": "login",
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
            background: #F3F3F3;
            color: #120000;
        }
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {
            display: none !important;
        }
        .block-container {
            padding-top: 1.4rem;
            max-width: 1180px;
        }
        h1, h2, h3 {
            color: #120000;
            font-weight: 800 !important;
            letter-spacing: 0;
        }
        .hero, .panel {
            background: #DADADA;
            border: 1px solid #c5c5c5;
            border-radius: 8px;
            padding: 1.35rem;
            box-shadow: 0 14px 34px rgba(18, 0, 0, .08);
        }
        .hero {
            margin-bottom: 1rem;
        }
        .muted {
            color: #4a4a4a;
            font-size: .98rem;
        }
        div.stButton > button, div.stDownloadButton > button {
            border-radius: 8px;
            border: 1px solid #F90202;
            background: #F90202;
            color: white;
            min-height: 2.85rem;
            font-weight: 700;
            transition: transform .12s ease, box-shadow .12s ease;
        }
        div.stButton > button:hover, div.stDownloadButton > button:hover {
            border-color: #c40101;
            background: #c40101;
            color: white;
            transform: translateY(-1px);
            box-shadow: 0 10px 22px rgba(249, 2, 2, .25);
        }
        div.stButton > button[kind="secondary"] {
            background: #ffffff;
            color: #F90202;
        }
        [data-testid="stMetric"] {
            background: #DADADA;
            border: 1px solid #c5c5c5;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 8px 22px rgba(18, 0, 0, .06);
        }
        [data-testid="stDataFrame"] {
            border: 1px solid #c5c5c5;
            border-radius: 8px;
            overflow: hidden;
        }
        .top-nav {
            background: #DADADA;
            border: 1px solid #c5c5c5;
            border-radius: 8px;
            padding: .85rem 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 10px 26px rgba(18, 0, 0, .06);
        }
        /* نص أسود وواضح داخل جميع مربعات الإدخال والبحث */
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        div[data-baseweb="select"] *,
        div[data-baseweb="input"] input,
        .stDateInput input {
            color: #120000 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def logout():
    # مسح كامل للـ Session حتى لا يتبقى أي أثر من المستخدم السابق
    st.session_state.clear()
    init_session()
    st.session_state.current_page = "login"
    st.rerun()


def require_login(roles=None):
    init_session()
    if not st.session_state.get("logged_in"):
        st.warning("يرجى تسجيل الدخول أولاً.")
        st.session_state.current_page = "login"
        st.stop()
    if roles and st.session_state.get("role") not in roles:
        st.error("ليس لديك صلاحية للوصول لهذه الصفحة.")
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
        if st.button("🏠 الرئيسية", use_container_width=True):
            st.session_state.current_page = "home"
            st.rerun()
    with col3:
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
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
            "city": "المدينة",
            "notes": "ملاحظات",
            "execution_date": "تاريخ التنفيذ",
            "created_at": "تاريخ الإنشاء",
            "updated_at": "آخر تحديث",
        }
    )
    st.dataframe(display, hide_index=True, use_container_width=True)


def assigned_task_dataframe(df):
    """نفس شكل جدول task_dataframe تماماً، مع أعمدة إضافية خاصة بالإسناد
    (تاريخ الإسناد، وأسنِدت بواسطة)."""
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
            "city": "المدينة",
            "notes": "ملاحظات",
            "assigned_date": "تاريخ الإسناد",
            "assigned_by": "أسندت بواسطة",
            "created_at": "تاريخ الإنشاء",
            "updated_at": "آخر تحديث",
        }
    )
    st.dataframe(display, hide_index=True, use_container_width=True)


def date_selector(key_prefix, default=None):
    """حقول اليوم/الشهر/السنة بنفس أسلوب باقي التطبيق (أعمدة + مربعات رقمية).
    تُعيد كائن تاريخ (date) صحيحاً، أو None إذا كان التاريخ المدخل غير صالح."""
    today = default or datetime.date.today()
    col1, col2, col3 = st.columns(3)
    with col1:
        day = st.number_input("اليوم", min_value=1, max_value=31, value=today.day, step=1, key=f"{key_prefix}_day")
    with col2:
        month = st.number_input("الشهر", min_value=1, max_value=12, value=today.month, step=1, key=f"{key_prefix}_month")
    with col3:
        year = st.number_input("السنة", min_value=2020, max_value=2100, value=today.year, step=1, key=f"{key_prefix}_year")
    try:
        return datetime.date(int(year), int(month), int(day))
    except ValueError:
        return None
