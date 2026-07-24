import datetime
import platform
import time
from io import BytesIO

import bcrypt
import pandas as pd
import psycopg2
import streamlit as st

from database.database import (
    CITIES,
    add_material,
    add_task,
    add_user,
    approve_import_review,
    assign_task,
    assigned_task_number_exists,
    bulk_add_tasks,
    bulk_approve_import_reviews,
    change_password,
    check_current_password,
    cleanup_cache,
    complete_assigned_task,
    create_import_review,
    create_tables,
    daily_report_exists,
    daily_report_display_source,
    daily_report_download_bytes,
    decrease_material,
    delete_daily_report,
    delete_material,
    delete_user,
    get_all_materials,
    get_all_users,
    get_assigned_task_by_number,
    get_audit_log,
    get_daily_report,
    get_database_info,
    get_error_log,
    get_import_logs,
    get_pending_import_reviews,
    get_query_stats,
    get_security_overview,
    get_system_counts,
    get_tasks_breakdown,
    increase_material,
    is_password_strong,
    log_action,
    log_error,
    login_user,
    material_exists,
    match_import_technician,
    normalize_import_task_status,
    normalize_import_task_type,
    resolve_column_mapping,
    save_daily_report,
    save_import_log,
    search_assigned_tasks,
    search_completed_tasks,
    search_tasks,
    task_exists,
    test_db_connection,
    update_material,
    update_task,
    delete_tasks,
    update_user,
)
from database.excel_importer import import_excel
from database.notifications import (
    list_notifications,
    mark_all_read,
    mark_read,
    notify_admins,
    notify_technician_by_name,
    notify_user,
    remove_all_notifications,
    remove_notification,
    show_toast,
)
from database.storage import ReportImageNotFoundError, StorageConfigurationError, StorageOperationError, validate_report_image
from config import SETTINGS
from logging_config import get_logger
from ui import TASK_STATUSES, TASK_TYPES, assigned_task_dataframe, confirm_delete_button, date_selector, fuzzy_series_mask, init_page, logout, page_header, require_login, selectable_table, task_dataframe, timed_spinner, top_nav


ROLE_LABELS = {"admin": "مدير", "technician": "فني"}
ROLE_VALUES = {label: value for value, label in ROLE_LABELS.items()}
UNITS = ["حبة", "متر", "بكرة", "كرتون", "رول", "كيس", "علبة", "أخرى"]
APP_VERSION = "2.1.0"
LOGGER = get_logger(__name__)


init_page("شركة الفكر الصاعد للمقاولات", "wide")


def go_to(page):
    st.session_state.current_page = page
    st.rerun()


def as_df(rows, columns=None):
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=columns or [])


def login_screen():
    st.session_state.current_page = "login"
    left, right = st.columns([1, 1.25], vertical_alignment="center")
    with left:
        st.image("images/logo.png", width=220)
        st.markdown(
            """
            <div class="hero">
                <h1>شركة الفكر الصاعد للمقاولات</h1>
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
            submitted = st.form_submit_button("🔑 تسجيل الدخول")
        if submitted:
            username = username.strip()
            password = password.strip()
            if not username or not password:
                st.warning("يرجى إدخال اسم المستخدم وكلمة المرور.")
            else:
                with timed_spinner("جاري تسجيل الدخول..."):
                    result = login_user(username, password)
                if result["ok"]:
                    user = result["user"]
                    st.session_state.logged_in = True
                    st.session_state.fullname = user["fullname"]
                    st.session_state.username = user["username"]
                    st.session_state.role = user["role"]
                    st.session_state.city = user.get("city") or ""
                    st.session_state.current_page = "home"
                    st.session_state.last_activity = time.time()
                    log_action(user["username"], "تسجيل دخول")
                    st.success("✅ تم تسجيل الدخول بنجاح")
                    st.rerun()
                elif result.get("locked"):
                    remaining = result.get("locked_until")
                    minutes_left = max(1, int(((remaining - datetime.datetime.now()).total_seconds()) // 60) + 1) if remaining else 15
                    st.error(f"🔒 تم قفل الحساب مؤقتاً بسبب محاولات دخول فاشلة متكررة. حاول مرة أخرى بعد {minutes_left} دقيقة تقريباً.")
                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة.")
        st.markdown("</div>", unsafe_allow_html=True)


def nav_card(label, page_key):
    if st.button(label, use_container_width=True):
        go_to(page_key)


def home_screen():
    require_login()
    page_header("🏠 الرئيسية", f"مرحباً {st.session_state.fullname}، اختر القسم المطلوب للانتقال مباشرة.")
    if st.session_state.role == "admin":
        cards = [
            ("📊 لوحة التحكم", "dashboard"),
            ("👔 لوحة المدير", "admin"),
            ("📑 صفحة التقارير", "reports"),
            ("📦 المستودع", "inventory"),
            ("👥 إدارة المستخدمين", "users"),
            ("🛠️ مركز المطور", "developer_center"),
            ("🔑 تغيير كلمة المرور", "change_password"),
        ]
    else:
        cards = [
            ("🛠️ صفحة الفني", "technician"),
            ("🔑 تغيير كلمة المرور", "change_password"),
        ]

    for row_start in range(0, len(cards), 3):
        cols = st.columns(3)
        for col, (label, page_key) in zip(cols, cards[row_start:row_start + 3]):
            with col:
                nav_card(label, page_key)

    st.divider()
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        logout()


def dashboard_page():
    require_login(["admin"])
    top_nav()
    page_header("📊 لوحة التحكم", "نظرة تنفيذية على المهام وأداء الفنيين.")
    with timed_spinner("جاري تحديث البيانات..."):
        df = as_df(search_tasks())
    if df.empty:
        st.info("لا توجد مهام حتى الآن.")
        return

    total = len(df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي المهام", total)
    c2.metric("مهام تقني", int((df["task_type"] == "تقني").sum()))
    c3.metric("مهام زيرا", int((df["task_type"] == "زيرا").sum()))
    c4.metric("أفضل فني", df["technician"].value_counts().idxmax() if total else "-")

    st.divider()
    status_counts = df["task_status"].value_counts()
    for col, status in zip(st.columns(len(TASK_STATUSES)), TASK_STATUSES):
        col.metric(status, int(status_counts.get(status, 0)))

    st.divider()
    with st.form("dashboard_filter_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            technician = st.selectbox("الفني", ["الكل"] + sorted(df["technician"].dropna().unique().tolist()))
        with col2:
            task_type = st.selectbox("نوع المهمة", ["الكل"] + TASK_TYPES)
        with col3:
            task_status = st.selectbox("حالة المهمة", ["الكل"] + TASK_STATUSES)
        keyword = st.text_input("بحث ذكي برقم المهمة أو الاشتراك أو نوع المهمة أو حالتها")
        search_submitted = st.form_submit_button("🔍 بحث")

    query_key = (keyword, technician, task_type, task_status)
    if search_submitted:
        with timed_spinner("جاري البحث عن المهمة..."):
            st.session_state["dashboard_filter_results"] = search_tasks(keyword, technician, task_type, task_status)
        st.session_state["dashboard_filter_query"] = query_key
    elif "dashboard_filter_query" not in st.session_state:
        st.session_state["dashboard_filter_results"] = df.to_dict("records")
        st.session_state["dashboard_filter_query"] = query_key

    filtered = as_df(st.session_state.get("dashboard_filter_results", []))

    st.subheader("📈 أداء الفنيين")
    st.bar_chart(df.groupby("technician").size().reset_index(name="عدد المهام").set_index("technician"))
    st.subheader("📋 المهام")
    task_dataframe(filtered)


def _import_review_tab(technicians_df):
    st.subheader("🔍 مراجعة الاستيراد")
    technicians_only = technicians_df[technicians_df["role"] == "technician"] if not technicians_df.empty else technicians_df
    technician_names = sorted(technicians_only["fullname"].tolist()) if not technicians_only.empty else []

    with st.form("import_review_filter_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            keyword = st.text_input("بحث", placeholder="اسم الفني، رقم المهمة...")
        with col2:
            refresh = st.form_submit_button("🔄 تحديث", use_container_width=True)

    if refresh or "import_review_loaded" not in st.session_state:
        st.session_state["import_review_rows"] = get_pending_import_reviews(keyword if refresh else st.session_state.get("import_review_keyword", ""))
        st.session_state["import_review_keyword"] = keyword if refresh else st.session_state.get("import_review_keyword", "")

    reviews = st.session_state.get("import_review_rows", get_pending_import_reviews())
    if not reviews:
        st.info("لا توجد مهام تحتاج مراجعة.")
        return

    display_rows = []
    for row in reviews:
        confidence = row.get("match_confidence")
        display_rows.append({
            "review_id": row["id"],
            "task_id": row["task_id"],
            "excel_technician_name": row["excel_technician_name"],
            "suggested_technician": row.get("suggested_technician") or "",
            "match_confidence": f"{confidence:.0%}" if confidence is not None else "—",
            "issue_reason": row.get("issue_reason") or "",
            "task_number": row.get("task_number") or "",
            "city": row.get("city") or "",
        })

    review_df = pd.DataFrame(display_rows)
    edited = st.data_editor(
        review_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "review_id": st.column_config.NumberColumn("المعرف", disabled=True),
            "excel_technician_name": st.column_config.TextColumn("اسم Excel", disabled=True),
            "suggested_technician": st.column_config.TextColumn("الفني المقترح"),
            "match_confidence": st.column_config.TextColumn("درجة التطابق", disabled=True),
            "issue_reason": st.column_config.TextColumn("سبب المشكلة", disabled=True),
            "task_number": st.column_config.TextColumn("رقم المهمة", disabled=True),
            "city": st.column_config.TextColumn("المدينة", disabled=True),
        },
        key="import_review_editor",
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        approve_all = st.button("✅ اعتماد جماعي (المقترح)", use_container_width=True)
    with col_b:
        selected_review = st.selectbox(
            "اختر للاعتماد",
            [f"#{r['review_id']} — {r['excel_technician_name']}" for r in display_rows],
            key="import_review_select",
        )
    with col_c:
        manual_tech = st.selectbox("فني بديل", technician_names or ["—"], key="import_review_manual_tech")

    c1, c2 = st.columns(2)
    with c1:
        approve_one = st.button("✅ اعتماد المحدد", use_container_width=True)
    with c2:
        approve_manual = st.button("✏️ اعتماد بالفني البديل", use_container_width=True)

    if approve_all:
        bulk_approve_import_reviews([r["review_id"] for r in display_rows], st.session_state.fullname)
        notify_admins("import_review", "مراجعة استيراد", f"تم اعتماد {len(display_rows)} مهمة جماعياً.")
        show_toast(f"✅ تم اعتماد {len(display_rows)} مهمة.", "✅")
        st.success("تم الاعتماد الجماعي.")
        st.rerun()

    if approve_one and selected_review:
        review_id = int(selected_review.split("—")[0].replace("#", "").strip())
        row = next((r for r in display_rows if r["review_id"] == review_id), None)
        if row and row.get("suggested_technician"):
            approve_import_review(review_id, row["suggested_technician"], st.session_state.fullname)
            show_toast("✅ تم اعتماد المهمة.", "✅")
            st.rerun()

    if approve_manual and selected_review and technician_names:
        review_id = int(selected_review.split("—")[0].replace("#", "").strip())
        approve_import_review(review_id, manual_tech, st.session_state.fullname)
        show_toast("✅ تم اعتماد المهمة بالفني البديل.", "✅")
        st.rerun()


def admin_page():
    require_login(["admin"])
    top_nav()
    page_header("📋 لوحة المدير", "إدارة المهام، البحث، الاستيراد، التعديل، والحذف.")
    with timed_spinner("جاري تحديث البيانات..."):
        df = as_df(search_tasks(), ["id", "technician", "task_number", "subscription_number", "task_type", "task_status"])
        technicians_df = as_df(get_all_users(), ["id", "username", "fullname", "role", "city"])

    tab_manage, tab_assign, tab_data, tab_transfer, tab_task_reports, tab_daily_tasks, tab_assigned_tasks, tab_import_review = st.tabs(
        ["📋 إدارة المهام", "📌 إسناد مهمة", "✏️ إدارة البيانات", "📥 الاستيراد والتصدير", "📷 تقارير المهام", "📅 المهام اليومية", "📋 المهام المسندة", "🔍 مراجعة الاستيراد"]
    )
    
    with tab_import_review:
        _import_review_tab(technicians_df)
    
    with tab_manage:
        total = len(df)
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي المهام", total)
        c2.metric("المزالة", int((df["task_status"] == "مزال").sum()) if total else 0)
        c3.metric("العوائق", int((df["task_status"] == "عائق").sum()) if total else 0)

        st.divider()
        with st.form("admin_manage_filter_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                keyword = st.text_input("بحث ذكي")
            with col2:
                status = st.selectbox("الحالة", ["الكل"] + TASK_STATUSES)
            with col3:
                task_type = st.selectbox("النوع", ["الكل"] + TASK_TYPES)
            manage_search_submitted = st.form_submit_button("🔍 بحث")

        manage_query_key = (keyword, task_type, status)
        if manage_search_submitted:
            with timed_spinner("جاري البحث عن المهمة..."):
                st.session_state["admin_manage_results"] = search_tasks(keyword, task_type=task_type, task_status=status)
            st.session_state["admin_manage_query"] = manage_query_key
        elif "admin_manage_query" not in st.session_state:
            st.session_state["admin_manage_results"] = df.to_dict("records")
            st.session_state["admin_manage_query"] = manage_query_key

        filtered = as_df(st.session_state.get("admin_manage_results", []))
        task_dataframe(filtered)
        st.caption(f"عدد النتائج: {len(filtered)}")

    with tab_assign:
        st.subheader("📌 إسناد المهمة")
        technicians_only = technicians_df[technicians_df["role"] == "technician"] if not technicians_df.empty else technicians_df
        technicians = sorted(technicians_only["fullname"].tolist()) if not technicians_only.empty else []
        technician_city_map = (
            {row["fullname"]: (row.get("city") or "") for _, row in technicians_only.iterrows()}
            if not technicians_only.empty else {}
        )

        if not technicians:
            st.info("لا يوجد فنيون مسجلون لإسناد المهام إليهم.")
        else:
            with st.form("assign_task_form", clear_on_submit=True):
                technician = st.selectbox("اختر الفني", technicians)
                task_number = st.text_input("رقم المهمة")
                subscription_number = st.text_input("رقم الاشتراك")
                assigned_date = date_selector("assign_task_date", label="تاريخ الإسناد")
                submitted = st.form_submit_button("📌 إسناد المهمة")

            if submitted:
                task_number = task_number.strip()
                subscription_number = subscription_number.strip()
                if not task_number or not subscription_number:
                    st.warning("يرجى إدخال رقم المهمة ورقم الاشتراك.")
                elif assigned_date is None:
                    st.error("تاريخ غير صحيح.")
                else:
                    with timed_spinner("💾 جاري حفظ المهمة..."):
                        exists = assigned_task_number_exists(task_number)
                        if not exists:
                            assign_task(
                                technician,
                                task_number,
                                subscription_number,
                                assigned_date=assigned_date,
                                city=technician_city_map.get(technician, ""),
                                assigned_by=st.session_state.fullname,
                            )
                            log_action(st.session_state.fullname, "إسناد مهمة", f"رقم المهمة: {task_number} → {technician}")
                    if exists:
                        st.error("❌ لا يمكن إضافة نفس رقم المهمة مرتين.")
                    else:
                        st.success("✅ تم حفظ المهمة بنجاح.")

    with tab_data:
        st.subheader("✏️ تعديل مهمة")
        st.info("تعديل المهام متقدم - يُرجى البحث والتعديل من تبويب إدارة المهام.")

    with tab_transfer:
        st.subheader("📥 الاستيراد والتصدير")
        st.info("استيراد وتصدير البيانات - متقدم في اللوحة الرئيسية.")

    with tab_task_reports:
        st.subheader("📷 تقارير المهام")
        st.info("عرض التقارير - متقدم في الصفحة المخصصة.")

    with tab_daily_tasks:
        st.subheader("📅 المهام اليومية")
        st.info("عرض المهام اليومية - متقدم في الصفحة المخصصة.")

    with tab_assigned_tasks:
        st.subheader("📋 المهام المسندة")
        st.info("عرض المهام المسندة - متقدم في الصفحة المخصصة.")


def route():
    if not st.session_state.get("logged_in"):
        login_screen()
        return

    pages = {
        "home": home_screen,
        "dashboard": dashboard_page,
        "admin": admin_page,
    }
    page = st.session_state.get("current_page", "home")
    handler = pages.get(page, home_screen)
    try:
        handler()
    except Exception as exc:
        LOGGER.exception("Unhandled page error in %s", handler.__name__)
        st.error("⚠️ حدث خطأ غير متوقع. تم تسجيل الخطأ تلقائياً.")


route()
