import datetime
import time
from contextlib import contextmanager

import streamlit as st
from difflib import SequenceMatcher

from config import SETTINGS


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
        /* إخفاء عناصر Streamlit الظاهرة للمستخدم (بالإضافة إلى toolbarMode="minimal"
           الرسمي في .streamlit/config.toml). هذه المحددات (#MainMenu/footer/header)
           مستقرة منذ سنوات طويلة في Streamlit، لكن لا يوجد لها مفتاح رسمي مخصص في
           config.toml حتى الآن، لذا استُخدم CSS كحل معروف وموثّق لهذه النقطة تحديداً. */
        #MainMenu, footer, header [data-testid="stToolbar"] {
            visibility: hidden !important;
            height: 0 !important;
        }
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
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
        div[data-testid="stForm"] {
            background: #ffffff;
            border: 1px solid #c5c5c5;
            border-radius: 8px;
            padding: 1.1rem 1.2rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: .35rem;
            border-bottom: 1px solid #c5c5c5;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            padding: .55rem 1rem;
            font-weight: 700;
        }
        .stTabs [aria-selected="true"] {
            color: #F90202 !important;
        }
        div[data-testid="stMetricValue"] {
            color: #F90202;
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
    username = st.session_state.get("username")
    if username:
        try:
            from database.database import log_action
            log_action(username, "تسجيل خروج")
        except Exception:
            pass
    st.session_state.clear()
    init_session()
    st.session_state.current_page = "login"
    st.rerun()


SESSION_TIMEOUT_SECONDS = SETTINGS.session_timeout_seconds


def require_login(roles=None):
    init_session()
    if not st.session_state.get("logged_in"):
        st.warning("يرجى تسجيل الدخول أولاً.")
        st.session_state.current_page = "login"
        st.stop()

    last_activity = st.session_state.get("last_activity")
    now = time.time()
    if last_activity and (now - last_activity) > SESSION_TIMEOUT_SECONDS:
        st.session_state.clear()
        init_session()
        st.session_state.current_page = "login"
        st.warning("⏱️ تم تسجيل خروجك تلقائياً بسبب عدم النشاط لمدة 30 دقيقة.")
        st.stop()
    st.session_state.last_activity = now

    if roles and st.session_state.get("role") not in roles:
        st.error("ليس لديك صلاحية للوصول لهذه الصفحة.")
        st.stop()


def top_nav():
    from database.notifications import (
        get_badge_count,
        list_notifications,
        mark_all_read,
        mark_read,
        notifications_enabled,
        remove_all_notifications,
        remove_notification,
        set_notifications_enabled,
        show_toast,
    )

    # تحديث دوري خفيف لعدد الإشعارات غير المقروءة دون الحاجة لإعادة تحميل الصفحة
    # يدوياً. الاعتماد على مكتبة streamlit-autorefresh اختياري تماماً: أي فشل في
    # استيرادها أو تشغيلها لا يوقف التطبيق، فقط يعطّل التحديث التلقائي.
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=20000, key="notifications_autorefresh")
    except Exception:
        pass

    badge = get_badge_count()
    previous_badge = st.session_state.get("_last_seen_badge_count", badge)
    is_new_arrival = badge > previous_badge
    st.session_state["_last_seen_badge_count"] = badge
    if is_new_arrival:
        show_toast("🔔 وصل إشعار جديد.", "🔔")
        st.session_state["_notif_pulse_until"] = time.time() + 2.5

    pulse_active = time.time() < st.session_state.get("_notif_pulse_until", 0)

    st.markdown(
        f"""
        <style>
        .st-key-notif_bell_wrap button {{
            position: relative;
            border-radius: 10px !important;
            transition: transform .15s ease, box-shadow .15s ease, background .15s ease;
        }}
        .st-key-notif_bell_wrap button:hover {{
            transform: translateY(-2px) scale(1.03);
            box-shadow: 0 10px 22px rgba(249, 2, 2, .3);
        }}
        {"" if not badge else f'''
        .st-key-notif_bell_wrap button::after {{
            content: "{badge if badge < 100 else '99+'}";
            position: absolute;
            top: -6px;
            right: -6px;
            min-width: 18px;
            height: 18px;
            padding: 0 4px;
            border-radius: 999px;
            background: #F90202;
            color: #fff;
            font-size: 11px;
            font-weight: 800;
            line-height: 18px;
            text-align: center;
            box-shadow: 0 0 0 2px #DADADA;
        }}
        '''}
        {"" if not pulse_active else '''
        @keyframes notifPulse {
            0% { box-shadow: 0 0 0 0 rgba(249, 2, 2, .55); }
            70% { box-shadow: 0 0 0 10px rgba(249, 2, 2, 0); }
            100% { box-shadow: 0 0 0 0 rgba(249, 2, 2, 0); }
        }
        .st-key-notif_bell_wrap button {
            animation: notifPulse 1.1s ease-out 2;
        }
        '''}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="top-nav">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([2, 1.2, 1, 1])
    with col1:
        st.markdown(
            f"**{st.session_state.get('fullname', '')}**  \n"
            f"<span class='muted'>الصلاحية: {st.session_state.get('role', '')}</span>",
            unsafe_allow_html=True,
        )
    with col2:
        enabled = notifications_enabled()
        new_enabled = st.toggle("تشغيل الإشعارات", value=enabled, key="notifications_toggle")
        if new_enabled != enabled:
            set_notifications_enabled(new_enabled)
            st.rerun()
    with col3:
        with st.container(key="notif_bell_wrap"):
            bell_label = f"🔔 ({badge})" if badge else "🔔"
            with st.popover(bell_label, use_container_width=True, help="الإشعارات"):
                _render_notifications_popover(list_notifications, mark_read, mark_all_read, remove_notification, remove_all_notifications)
    with col4:
        c_home, c_logout = st.columns(2)
        with c_home:
            if st.button("🏠", use_container_width=True, help="الرئيسية"):
                st.session_state.current_page = "home"
                st.rerun()
        with c_logout:
            if st.button("🚪", use_container_width=True, help="تسجيل الخروج"):
                logout()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_notifications_popover(list_notifications, mark_read, mark_all_read, remove_notification, remove_all_notifications):
    """محتوى نافذة الإشعارات: تُفتح داخل نفس الصفحة (Popover) دون أي انتقال أو
    تحميل صفحة جديدة. يحتوي على بحث فوري، فلترة حسب النوع وحالة القراءة،
    ترتيب حسب الأحدث (افتراضي من قاعدة البيانات)، تحديد كمقروء/الكل، وحذف
    واحد/الكل."""
    from database.notifications import EVENT_LABELS

    st.markdown("#### 🔔 مركز الإشعارات")
    search_col, status_col, type_col = st.columns([2, 1, 1])
    with search_col:
        keyword = st.text_input("بحث داخل الإشعارات", key="notif_popover_search", label_visibility="collapsed", placeholder="🔎 بحث...")
    with status_col:
        status_filter = st.selectbox(
            "حالة القراءة", ["الكل", "غير مقروءة", "مقروءة"],
            key="notif_popover_status_filter", label_visibility="collapsed",
        )
    with type_col:
        type_options = ["كل الأنواع"] + list(EVENT_LABELS.values())
        type_filter = st.selectbox("نوع الإشعار", type_options, key="notif_popover_type_filter", label_visibility="collapsed")

    items = list_notifications(keyword=keyword)
    if status_filter == "غير مقروءة":
        items = [n for n in items if not n.get("is_read")]
    elif status_filter == "مقروءة":
        items = [n for n in items if n.get("is_read")]
    if type_filter != "كل الأنواع":
        items = [n for n in items if EVENT_LABELS.get(n.get("event_type"), n.get("event_type")) == type_filter]

    b1, b2 = st.columns(2)
    with b1:
        if st.button("✅ تحديد الكل كمقروء", use_container_width=True, key="notif_popover_mark_all"):
            mark_all_read()
            st.rerun()
    with b2:
        if st.button("🗑️ حذف الكل", use_container_width=True, key="notif_popover_delete_all"):
            remove_all_notifications()
            st.rerun()

    if not items:
        st.info("لا توجد إشعارات.")
        return

    for item in items[:50]:
        unread = not item.get("is_read")
        dot = "🟢" if unread else "⚪"
        event_label = EVENT_LABELS.get(item.get("event_type"), item.get("event_type") or "")
        with st.container(border=True):
            top = st.columns([5, 1, 1])
            with top[0]:
                title = item.get("title", "")
                st.markdown(f"**{dot} {title}**  \n<span class='muted'>🏷️ {event_label}</span>", unsafe_allow_html=True)
                meta = str(item.get("created_at", ""))
                actor = item.get("actor")
                if actor:
                    meta += f" · بواسطة {actor}"
                st.caption(meta)
                st.write(item.get("message", ""))
            with top[1]:
                if unread and st.button("✅", key=f"notif_popover_read_{item['id']}", help="تحديد كمقروء"):
                    mark_read(item["id"])
                    st.rerun()
            with top[2]:
                if st.button("🗑️", key=f"notif_popover_del_{item['id']}", help="حذف"):
                    remove_notification(item["id"])
                    st.rerun()


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


def date_selector(key_prefix, default=None, label="التاريخ"):
    """مكوّن تقويم موحّد مطابق لمكوّن سجل العمليات في مركز المطور."""
    return st.date_input(
        label,
        value=default or datetime.date.today(),
        key=f"{key_prefix}_date_picker",
    )
