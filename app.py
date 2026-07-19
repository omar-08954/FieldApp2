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
    assign_task,
    assigned_task_number_exists,
    bulk_add_tasks,
    change_password,
    check_current_password,
    cleanup_cache,
    complete_assigned_task,
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
    search_assigned_tasks,
    search_completed_tasks,
    search_tasks,
    task_exists,
    test_db_connection,
    update_material,
    update_task,
    delete_tasks,
    update_user
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
        # أول ظهور للصفحة: نعرض كل المهام قبل أي بحث، دون تنفيذ استعلام إضافي
        st.session_state["dashboard_filter_results"] = df.to_dict("records")
        st.session_state["dashboard_filter_query"] = query_key

    filtered = as_df(st.session_state.get("dashboard_filter_results", []))

    st.subheader("📈 أداء الفنيين")
    st.bar_chart(df.groupby("technician").size().reset_index(name="عدد المهام").set_index("technician"))
    st.subheader("📋 المهام")
    task_dataframe(filtered)


def _technician_task_entry_tab():
    my_city = st.session_state.get("city") or ""
    if my_city:
        st.caption(f"المدينة المسجلة لحسابك: {my_city}")
    with st.form("task_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            task_number = st.text_input("رقم المهمة")
            task_type = st.selectbox("نوع المهمة", TASK_TYPES)
        with col2:
            subscription_number = st.text_input("رقم الاشتراك")
            task_status = st.selectbox("حالة المهمة", TASK_STATUSES)
        notes = st.text_area("ملاحظات (اختياري)", height=90)
        submitted = st.form_submit_button("💾 تسجيل المهمة")

    if submitted:
        task_number = task_number.strip()
        subscription_number = subscription_number.strip()
        if not task_number or not subscription_number:
            st.warning("يرجى إدخال رقم المهمة ورقم الاشتراك.")
        else:
            with timed_spinner("💾 جاري حفظ المهمة..."):
                # إذا كانت هذه المهمة موجودة ضمن المهام المسندة لنفس الفني،
                # تُعتبر منفذة تلقائياً وتُنقل من المهام المسندة إلى المهام المنفذة
                assigned_match = get_assigned_task_by_number(st.session_state.fullname, task_number)
                if assigned_match:
                    complete_assigned_task(
                        assigned_match["id"],
                        subscription_number=subscription_number,
                        task_type=task_type,
                        task_status=task_status,
                        notes=notes,
                        city=my_city,
                    )
                    exists = False
                    log_action(st.session_state.fullname, "تنفيذ مهمة مسندة", f"رقم المهمة: {task_number}")
                else:
                    exists = task_exists(task_number)
                    if not exists:
                        add_task(
                            st.session_state.fullname,
                            task_number,
                            subscription_number,
                            task_type,
                            task_status,
                            city=my_city,
                            notes=notes,
                        )
                        log_action(st.session_state.fullname, "إضافة مهمة", f"رقم المهمة: {task_number}")
            if exists:
                st.error("❌ لا يمكن إضافة نفس رقم المهمة مرتين.")
            else:
                st.success("✅ تم حفظ المهمة بنجاح.")


def technician_page():
    """صفحة الفني الوحيدة، بثلاث تبويبات فقط: المهام المسندة، المهام
    اليومية (تسجيل مهمة جديدة + عرض المهام المنفذة)، وإضافة تقرير."""
    require_login(["admin", "technician"])
    top_nav()
    page_header("🛠️ صفحة الفني", "المهام المسندة، المهام اليومية، وإضافة التقارير من مكان واحد.")

    tab_add, tab_assigned, tab_daily, tab_report = st.tabs(["➕ إضافة مهمة", "📋 المهام المسندة", "📅 المهام اليومية", "📷 إضافة تقرير"])

    with tab_assigned:
        _assigned_tasks_admin_view(st.session_state.fullname, "tech_assigned_tasks")

    with tab_add:
        st.subheader("➕ تسجيل مهمة جديدة")
        _technician_task_entry_tab()

    with tab_daily:
        st.subheader("✅ المهام المنفذة")
        _completed_tasks_view(
        st.session_state.fullname,
        "tech_daily_completed"
    )

    with tab_report:
        uploaded_report = st.file_uploader("📷 رفع صورة التقرير", type=["jpg", "jpeg", "png"], key="tech_report_uploader")
        if uploaded_report is not None:
            image_bytes = uploaded_report.getvalue()
            if uploaded_report.size > SETTINGS.max_upload_bytes:
                st.error("❌ حجم الصورة كبير جداً (الحد الأقصى 5 ميجابايت).")
            elif not validate_report_image(image_bytes, uploaded_report.type or ""):
                st.error("Invalid report image. Upload a valid JPEG or PNG file.")
            else:
                report_date = date_selector("tech_report_date", label="تاريخ التقرير")
                if report_date is not None and daily_report_exists(st.session_state.fullname, report_date):
                    st.info("⚠️ يوجد تقرير محفوظ مسبقاً لهذا التاريخ، وسيتم استبداله عند الحفظ.")

                if st.button("💾 حفظ التقرير", key="tech_report_save_btn", use_container_width=True):
                    if report_date is None:
                        st.error("تاريخ غير صحيح.")
                    else:
                        with timed_spinner("💾 جاري حفظ المهمة..."):
                            save_daily_report(
                                st.session_state.fullname,
                                report_date,
                                image_bytes,
                                uploaded_report.type or "image/jpeg",
                            )
                            log_action(st.session_state.fullname, "رفع تقرير", f"التاريخ: {report_date}")
                        st.success("✅ تم حفظ المهمة بنجاح.")
                        st.rerun()


def select_task_from_search(state_prefix, title):
    with st.form(f"{state_prefix}_search_form"):
        keyword = st.text_input(title, key=f"{state_prefix}_keyword")
        search_clicked = st.form_submit_button("🔍 البحث")
    if search_clicked:
        if not keyword.strip():
            st.warning("يرجى إدخال قيمة للبحث.")
        else:
            with timed_spinner("جاري البحث عن المهمة..."):
                st.session_state[f"{state_prefix}_results"] = search_tasks(keyword)
                st.session_state.pop(f"{state_prefix}_selected_id", None)
            if st.session_state[f"{state_prefix}_results"]:
                st.success("✅ تم العثور على المهمة")
            else:
                st.error("لم يتم العثور على مهمة مطابقة.")

    results = st.session_state.get(f"{state_prefix}_results", [])
    if not results:
        return None

    df = as_df(results)
    if len(df) > 1:
        st.info("تم العثور على أكثر من سجل. اختر السجل المطلوب من القائمة.")
        task_dataframe(df)
        options = {
            f"{row['task_number']} - {row['subscription_number']} - {row['task_type']} - {row['task_status']}": row
            for _, row in df.iterrows()
        }
        selected_label = st.selectbox("اختر المهمة", list(options.keys()), key=f"{state_prefix}_select")
        return options[selected_label]

    return df.iloc[0].to_dict()


def _assign_task_view(technicians_df):
    """نموذج إسناد المهمة داخل لوحة المدير، دون أي قسم بحث مكرر."""
    technicians_only = technicians_df[technicians_df["role"] == "technician"] if not technicians_df.empty else technicians_df
    technicians = sorted(technicians_only["fullname"].tolist()) if not technicians_only.empty else []
    technician_city_map = (
        {row["fullname"]: (row.get("city") or "") for _, row in technicians_only.iterrows()}
        if not technicians_only.empty else {}
    )

    if not technicians:
        st.info("لا يوجد فنيون مسجلون لإسناد المهام إليهم.")
        return

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


def _assigned_tasks_admin_view(technician_filter, key_prefix):
    """نفس أسلوب _completed_tasks_view تماماً، لكن لعرض المهام المسندة (لم
    تُنفَّذ بعد) لفني معيّن في تاريخ محدد. تُستخدم من تبويب المهام المسندة
    داخل لوحة المدير."""
    view_date = date_selector(f"{key_prefix}_date", label="تاريخ الإسناد")
    if st.button("👁️ عرض", key=f"{key_prefix}_btn", use_container_width=True):
        if view_date is None:
            st.error("تاريخ غير صحيح.")
        else:
            with timed_spinner("جاري تحديث البيانات..."):
                st.session_state[f"{key_prefix}_results"] = search_assigned_tasks(technician_filter, view_date)
            st.session_state[f"{key_prefix}_query"] = (technician_filter, view_date)

    query = st.session_state.get(f"{key_prefix}_query")
    results = st.session_state.get(f"{key_prefix}_results", []) if query == (technician_filter, view_date) else []
    assigned_task_dataframe(as_df(results))
    _export_results_button(results, "المهام_المسندة.xlsx", f"{key_prefix}_export")


def _daily_report_view(technician, key_prefix):
    """نفس أسلوب _completed_tasks_view تماماً (اختيار تاريخ + زر عرض +
    تخزين النتيجة في session_state)، لكن لعرض تقرير يوم واحد لفني محدد.
    تعتمد على get_daily_report المخزَّنة مؤقتاً بنفس إعدادات باقي المشروع."""
    report_date = date_selector(f"{key_prefix}_date", label="تاريخ التقرير")
    if st.button("👁️ عرض التقرير", key=f"{key_prefix}_btn", use_container_width=True):
        if report_date is None:
            st.error("تاريخ غير صحيح.")
        else:
            with timed_spinner("جاري تحديث البيانات..."):
                st.session_state[f"{key_prefix}_result"] = get_daily_report(technician, report_date)
            st.session_state[f"{key_prefix}_query"] = (technician, report_date)

    query = st.session_state.get(f"{key_prefix}_query")
    if query == (technician, report_date):
        result = st.session_state.get(f"{key_prefix}_result")
        if result:
            display_source = daily_report_display_source(result)
            if display_source:
                st.image(display_source, use_container_width=True)
            else:
                st.error("الصورة غير موجودة في هذا التقرير.")

            download_bytes = None
            if display_source:
                try:
                    download_bytes = daily_report_download_bytes(result)
                except ReportImageNotFoundError:
                    st.error("تعذر حفظ الصورة لأن الملف غير موجود في Supabase Storage.")
                except (StorageConfigurationError, StorageOperationError):
                    LOGGER.exception("Could not download report image.")
                    st.error("تعذر جلب الصورة الأصلية من التخزين. حاول مرة أخرى لاحقاً.")

            col_save, col_delete = st.columns(2)
            with col_save:
                if download_bytes:
                    extension = ".png" if result.get("image_mime") == "image/png" else ".jpg"
                    st.download_button(
                        "💾 حفظ الصورة",
                        data=download_bytes,
                        file_name=f"تقرير_{technician}_{report_date}{extension}",
                        mime=result.get("image_mime") or "image/jpeg",
                        key=f"{key_prefix}_download",
                        use_container_width=True,
                    )
                else:
                    st.button("💾 حفظ الصورة", key=f"{key_prefix}_download_unavailable", disabled=True, use_container_width=True)
            with col_delete:
                if st.button("🗑 حذف الصورة", key=f"{key_prefix}_delete", use_container_width=True):
                    try:
                        with timed_spinner("جاري حذف الصورة..."):
                            deletion = delete_daily_report(result["id"], result.get("image_url"))
                            log_action(st.session_state.fullname, "حذف تقرير", f"الفني: {technician}، التاريخ: {report_date}")
                    except (StorageConfigurationError, StorageOperationError):
                        LOGGER.exception("Could not delete report image.")
                        st.error("فشل حذف الصورة من Supabase Storage، ولم يُحذف مرجعها من قاعدة البيانات.")
                    except Exception:
                        LOGGER.exception("Could not delete daily report.")
                        st.error("تعذر حذف الصورة أو مرجعها من قاعدة البيانات. حاول مرة أخرى.")
                    else:
                        st.session_state.pop(f"{key_prefix}_result", None)
                        st.session_state.pop(f"{key_prefix}_query", None)
                        if deletion["database_was_missing"]:
                            st.warning("لم يعد مرجع التقرير موجوداً في قاعدة البيانات؛ تم تحديث الواجهة.")
                        elif deletion["storage_was_missing"]:
                            st.warning("لم تكن الصورة موجودة في Storage؛ تم تنظيف مرجع التقرير من قاعدة البيانات.")
                        else:
                            st.success("✅ تم حذف الصورة من Storage وقاعدة البيانات.")
                        st.rerun()
        else:
            st.info("لا يوجد تقرير لهذا الفني في هذا التاريخ.")


def _export_results_button(rows, filename, key):
    """زر تحميل Excel لنتائج ظاهرة حالياً على الشاشة فقط. لا يظهر إطلاقاً
    إن لم توجد نتائج، بنفس أسلوب زر تصدير Excel المستخدم في لوحة المدير."""
    if not rows:
        return
    export_df = as_df(rows).drop(columns=["id"], errors="ignore")
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False)
    st.download_button(
        "📥 تحميل تقرير Excel",
        data=output.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=key,
        use_container_width=True,
    )


def _completed_tasks_view(technician_filter, key_prefix):
    """منطق موحّد لعرض المهام المنفذة حسب اسم الفني + اليوم/الشهر/السنة، بالاعتماد
    الكامل على execution_date. يُستخدم من صفحة المهام اليومية (الفني) ومن تبويب
    المهام اليومية داخل لوحة المدير، حتى يبقى السلوك متطابقاً في المكانين."""
    completed_date = date_selector(f"{key_prefix}_date", label="تاريخ التنفيذ")
    if st.button("👁️ عرض", key=f"{key_prefix}_btn", use_container_width=True):
        if completed_date is None:
            st.error("تاريخ غير صحيح.")
        else:
            with timed_spinner("جاري تحديث البيانات..."):
                st.session_state[f"{key_prefix}_results"] = search_completed_tasks(technician_filter, completed_date)
            st.session_state[f"{key_prefix}_query"] = (technician_filter, completed_date)

    query = st.session_state.get(f"{key_prefix}_query")
    results = st.session_state.get(f"{key_prefix}_results", []) if query == (technician_filter, completed_date) else []
    task_dataframe(as_df(results))
    _export_results_button(results, "المهام_المنفذة.xlsx", f"{key_prefix}_export")


def admin_page():
    require_login(["admin"])
    top_nav()
    page_header("📋 لوحة المدير", "إدارة المهام، البحث، الاستيراد، التعديل، والحذف.")
    with timed_spinner("جاري تحديث البيانات..."):
        df = as_df(search_tasks(), ["id", "technician", "task_number", "subscription_number", "task_type", "task_status"])
        technicians_df = as_df(get_all_users(), ["id", "username", "fullname", "role", "city"])

    tab_manage, tab_assign, tab_data, tab_transfer, tab_task_reports, tab_daily_tasks, tab_assigned_tasks = st.tabs(
        ["📋 إدارة المهام", "📌 إسناد مهمة", "✏️ إدارة البيانات", "📥 الاستيراد والتصدير", "📷 تقارير المهام", "📅 المهام اليومية", "📋 المهام المسندة"]
    )
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
        _assign_task_view(technicians_df)

    with tab_data:
        st.subheader("✏️ تعديل مهمة")
        task = select_task_from_search("edit_task", "بحث ذكي للتعديل")
        if task:
            with st.form("edit_form"):
                new_number = st.text_input("رقم المهمة", value=task["task_number"])
                new_subscription = st.text_input("رقم الاشتراك", value=task["subscription_number"])
                new_type = st.selectbox("نوع المهمة", TASK_TYPES, index=TASK_TYPES.index(task["task_type"]) if task["task_type"] in TASK_TYPES else 0)
                new_status = st.selectbox("حالة المهمة", TASK_STATUSES, index=TASK_STATUSES.index(task["task_status"]) if task["task_status"] in TASK_STATUSES else 0)
                current_city = task.get("city") if task.get("city") in CITIES else (CITIES[0] if CITIES else None)
                new_city = st.selectbox("المدينة", CITIES, index=CITIES.index(current_city) if current_city in CITIES else 0)
                new_notes = st.text_area("ملاحظات", value=task.get("notes") or "", height=90)
                save = st.form_submit_button("💾 حفظ التعديلات")
            if save:
                with timed_spinner("جاري حفظ التعديلات..."):
                    duplicate = task_exists(new_number, exclude_id=task["id"])
                    if not duplicate:
                        update_task(task["id"], new_number, new_subscription, new_type, new_status, city=new_city, notes=new_notes)
                        log_action(st.session_state.fullname, "تعديل مهمة", f"رقم المهمة: {new_number}")
                if duplicate:
                    st.error("رقم المهمة مستخدم في مهمة أخرى.")
                else:
                    st.success("✅ تم حفظ التعديلات بنجاح.")
                    st.session_state.pop("edit_task_results", None)
                    st.rerun()

        st.divider()
        st.subheader("🗑 حذف مهام")
        with timed_spinner("جاري تحديث البيانات..."):
            delete_df = as_df(search_tasks(), ["id", "technician", "task_number", "subscription_number", "task_type", "task_status", "city"])
        selected_ids = selectable_table(
            delete_df,
            "id",
            {
                "technician": "الفني",
                "task_number": "رقم المهمة",
                "subscription_number": "رقم الاشتراك",
                "task_type": "نوع المهمة",
                "task_status": "حالة المهمة",
                "city": "المدينة",
            },
            key_prefix="delete_tasks",
        )
        if confirm_delete_button("delete_tasks", selected_ids, "🗑 حذف المهام المحددة", "مهمة محددة"):
            with timed_spinner("جاري حذف المهمة..."):
                delete_tasks(selected_ids)
            log_action(st.session_state.fullname, "حذف مهام", f"عدد: {len(selected_ids)}")
            st.success(f"✅ تم حذف {len(selected_ids)} مهمة بنجاح.")
            st.rerun()

    with tab_transfer:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📥 استيراد Excel")
            uploaded = st.file_uploader("اختر ملف Excel", type=["xlsx"])
            if uploaded:
                if uploaded.size > 10 * 1024 * 1024:
                    st.error("❌ حجم الملف كبير جداً (الحد الأقصى 10 ميجابايت).")
                    uploaded = None
            if uploaded:
                incoming = pd.read_excel(uploaded)
                if len(incoming) > 20000:
                    st.error(f"❌ الملف يحتوي على {len(incoming)} صف، والحد الأقصى المسموح به لكل استيراد هو 20,000 صف. يرجى تقسيم الملف.")
                    incoming = incoming.iloc[0:0]
                # مطابقة أسماء الأعمدة تلقائياً (بالاسم أو بمحتوى العمود) حتى لو اختلفت عن الأسماء المتوقعة
                column_map = resolve_column_mapping(incoming.columns, incoming)
                if column_map:
                    incoming = incoming.rename(columns=column_map)
                columns = [column for column in ["الفني", "رقم المهمة", "رقم الاشتراك", "نوع المهمة", "حالة المهمة"] if column in incoming.columns]
                st.dataframe(incoming[columns].head(20), hide_index=True, use_container_width=True)
                with st.form("import_tasks_form"):
                    confirm_import = st.form_submit_button("بدء الاستيراد", use_container_width=True)
                if confirm_import:
                    added = duplicated = skipped_ambiguous = 0
                    import_warnings = []
                    with timed_spinner("جاري استيراد البيانات..."):
                        # استخدام البيانات المجلوبة بالفعل بدل تكرار الاستعلام عن كل رقم مهمة
                        existing_numbers = set(df["task_number"].astype(str)) if not df.empty else set()
                        technicians_df = as_df(get_all_users(), ["id", "username", "fullname", "role", "city", "created_at"])
                        if not technicians_df.empty:
                            technicians_only = technicians_df[technicians_df["role"] == "technician"]
                            technician_names = technicians_only["fullname"].tolist()
                            technician_city_map = {
                                row["fullname"]: (row.get("city") or "") for _, row in technicians_only.iterrows()
                            }
                        else:
                            technician_names, technician_city_map = [], {}

                        rows_to_insert = []
                        today = datetime.date.today()
                        for row_index, row in incoming.iterrows():
                            number = str(row.get("رقم المهمة", "")).strip()
                            if not number or number in existing_numbers:
                                duplicated += 1
                                continue
                            raw_technician = str(row.get("الفني", "")).strip() or "غير محدد"
                            # مطابقة ذكية لاسم الفني: تطابق الاسم الأول، ثم الاسم
                            # الثاني عند التعارض. إذا تعذّر الفصل يُسجَّل تحذير
                            # ويُتجاوز هذا السطر فقط دون إيقاف الاستيراد بالكامل.
                            resolved_technician, ambiguity_warning = match_import_technician(raw_technician, technician_names)
                            if ambiguity_warning:
                                import_warnings.append(f"صف {row_index + 2}: {ambiguity_warning}")
                                skipped_ambiguous += 1
                                continue
                            # إذا تم التعرف على الفني، تُستخدم مدينته من قاعدة البيانات دائماً
                            # (حتى لو كانت فارغة) وليس من ملف Excel
                            if resolved_technician in technician_city_map:
                                resolved_city = technician_city_map[resolved_technician]
                            else:
                                resolved_city = str(row.get("المدينة", "")).strip()
                            # نوع/حالة المهمة: القيمة الفارغة أو غير المعروفة تُستبدل
                            # تلقائياً بقيمة افتراضية ولا تُعتبر خطأ يوقف الاستيراد
                            resolved_type = normalize_import_task_type(row.get("نوع المهمة", ""))
                            resolved_status = normalize_import_task_status(row.get("حالة المهمة", ""))
                            rows_to_insert.append((
                                resolved_technician,
                                number,
                                str(row.get("رقم الاشتراك", "")).strip(),
                                resolved_type,
                                resolved_status,
                                resolved_city,
                                str(row.get("الملاحظات", "")).strip(),
                                today,
                            ))
                            existing_numbers.add(number)
                            added += 1
                        # إدراج جماعي بدل استعلام لكل صف على حدة (أسرع بكثير للملفات الكبيرة)
                        bulk_add_tasks(rows_to_insert)
                        if added:
                            log_action(
                                st.session_state.fullname,
                                "استيراد مهام",
                                f"عدد: {added}, مكرر: {duplicated}, متجاوَز (اسم فني غامض): {skipped_ambiguous}",
                            )
                    summary = f"✅ تمت إضافة {added} مهمة، وتجاهل {duplicated} مهمة مكررة."
                    if skipped_ambiguous:
                        summary += f" تم تجاوز {skipped_ambiguous} صف بسبب تعذر تحديد اسم الفني بدقة."
                    st.success(summary)
                    if import_warnings:
                        with st.expander(f"⚠️ سجل تحذيرات الاستيراد ({len(import_warnings)})", expanded=True):
                            for warning in import_warnings:
                                st.warning(warning)
                    st.session_state["last_import_warnings"] = import_warnings
                    if not import_warnings:
                        st.rerun()
        with col2:
            st.subheader("📤 تصدير Excel")
            with st.form("export_tasks_form"):
                export_type = st.selectbox("نوع المهمة", ["الكل"] + TASK_TYPES, key="export_task_type")
                export_status = st.selectbox("حالة المهمة", ["الكل"] + TASK_STATUSES, key="export_task_status")
                export_build_submitted = st.form_submit_button("⚙️ تجهيز ملف Excel")

            if export_build_submitted:
                with timed_spinner("جاري تصدير البيانات..."):
                    export_df = df
                    if export_type != "الكل":
                        export_df = export_df[export_df["task_type"] == export_type]
                    if export_status != "الكل":
                        export_df = export_df[export_df["task_status"] == export_status]
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:
                        export_df.drop(columns=["id"], errors="ignore").to_excel(writer, index=False)
                    st.session_state["export_tasks_bytes"] = output.getvalue()

            if st.session_state.get("export_tasks_bytes"):
                st.download_button(
                    "تحميل ملف Excel",
                    data=st.session_state["export_tasks_bytes"],
                    file_name="tasks.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

    with tab_task_reports:
        technicians = (
            sorted(technicians_df[technicians_df["role"] == "technician"]["fullname"].tolist())
            if not technicians_df.empty else []
        )
        if not technicians:
            st.info("لا يوجد فنيون مسجلون.")
        else:
            technician = st.selectbox("اسم الفني", technicians, key="admin_report_tech")
            _daily_report_view(technician, "admin_report")

    with tab_daily_tasks:
        technicians_daily = (
            sorted(technicians_df[technicians_df["role"] == "technician"]["fullname"].tolist())
            if not technicians_df.empty else []
        )
        if not technicians_daily:
            st.info("لا يوجد فنيون مسجلون.")
        else:
            technician_daily = st.selectbox("الفني", technicians_daily, key="admin_daily_tasks_tech")
            _completed_tasks_view(technician_daily, "admin_daily_tasks")

    with tab_assigned_tasks:
        technicians_assigned = (
            sorted(technicians_df[technicians_df["role"] == "technician"]["fullname"].tolist())
            if not technicians_df.empty else []
        )
        if not technicians_assigned:
            st.info("لا يوجد فنيون مسجلون.")
        else:
            technician_assigned = st.selectbox("الفني", technicians_assigned, key="admin_assigned_tasks_tech")
            _assigned_tasks_admin_view(technician_assigned, "admin_assigned_tasks")


def _city_report_tab(city):
    with timed_spinner("جاري إنشاء التقرير..."):
        df = as_df(search_tasks(city=city))
    if df.empty:
        st.info("لا توجد بيانات لهذه المدينة.")
        return

    with st.form(f"report_filter_form_{city}"):
        col1, col2 = st.columns(2)
        with col1:
            task_type = st.selectbox("نوع المهمة", ["الكل"] + TASK_TYPES, key=f"report_type_{city}")
        with col2:
            task_status = st.selectbox("حالة المهمة", ["الكل"] + TASK_STATUSES, key=f"report_status_{city}")
        keyword = st.text_input(
            "بحث ذكي برقم المهمة أو الاشتراك أو نوع المهمة أو حالتها أو اسم الفني",
            key=f"report_keyword_{city}",
        )
        report_search_submitted = st.form_submit_button("🔍 بحث")

    report_query_key = (city, keyword, task_type, task_status)
    if report_search_submitted:
        with timed_spinner("جاري إنشاء التقرير..."):
            # city يُمرر دائماً لضمان عدم اختلاط بيانات المدينتين
            st.session_state[f"report_results_{city}"] = search_tasks(keyword, task_type=task_type, task_status=task_status, city=city)
        st.session_state[f"report_query_{city}"] = report_query_key
    elif f"report_query_{city}" not in st.session_state:
        st.session_state[f"report_results_{city}"] = df.to_dict("records")
        st.session_state[f"report_query_{city}"] = report_query_key

    filtered = as_df(st.session_state.get(f"report_results_{city}", []))

    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي النتائج", len(filtered))
    c2.metric("مهام تقني", int((filtered["task_type"] == "تقني").sum()) if not filtered.empty else 0)
    c3.metric("مهام زيرا", int((filtered["task_type"] == "زيرا").sum()) if not filtered.empty else 0)
    task_dataframe(filtered)
    with timed_spinner("جاري تحميل التقارير..."):
        csv = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        f"📥 تحميل تقرير {city}", csv, f"tasks_report_{city}.csv", "text/csv",
        use_container_width=True, key=f"report_download_{city}",
    )


def reports_page():
    require_login(["admin"])
    top_nav()
    page_header("📑 التقارير", "تقارير المهام حسب المدينة والنوع والحالة مع إمكانية التصدير.")

    tab_jeddah, tab_makkah = st.tabs(["📍 تقارير جدة", "📍 تقارير مكة"])
    with tab_jeddah:
        _city_report_tab("جدة")
    with tab_makkah:
        _city_report_tab("مكة")


def users_page():
    require_login(["admin"])
    top_nav()
    page_header("👥 إدارة المستخدمين", "إدارة المستخدمين والصلاحيات من مكان واحد.")

    with timed_spinner("جاري تحديث البيانات..."):
        users_df = as_df(get_all_users(), ["id", "username", "fullname", "role", "city", "created_at"])
    tab_view, tab_add, tab_edit, tab_delete = st.tabs(["👥 عرض المستخدمين", "➕ إضافة مستخدم", "✏️ تعديل مستخدم", "🗑️ حذف مستخدم"])

    with tab_view:
        with st.form("users_search_form"):
            search = st.text_input("بحث بالاسم أو اسم المستخدم")
            users_search_submitted = st.form_submit_button("🔍 بحث")

        if users_search_submitted:
            st.session_state["users_search_query"] = search
        search = st.session_state.get("users_search_query", "")

        filtered = users_df.copy()
        if search.strip() and not filtered.empty:
            exact_mask = (
                filtered["fullname"].astype(str).str.contains(search, case=False, na=False)
                | filtered["username"].astype(str).str.contains(search, case=False, na=False)
            )
            if exact_mask.any():
                filtered = filtered[exact_mask]
            else:
                # لا يوجد تطابق حرفي: جرّب بحثاً ذكياً (تقريبياً)
                fuzzy_mask = (
                    fuzzy_series_mask(filtered["fullname"].astype(str), search)
                    | fuzzy_series_mask(filtered["username"].astype(str), search)
                )
                filtered = filtered[fuzzy_mask]
        users_table(filtered)
        st.caption(f"عدد المستخدمين: {len(filtered)}")

    with tab_add:
        with st.form("add_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                fullname = st.text_input("الاسم الكامل")
                username = st.text_input("اسم المستخدم")
            with col2:
                password = st.text_input("كلمة المرور", type="password")
                confirm_password = st.text_input("تأكيد كلمة المرور", type="password")
            role_label = st.selectbox("نوع المستخدم", ["مدير", "فني"])
            city = st.selectbox("المدينة", CITIES)
            add_submitted = st.form_submit_button("➕ إضافة المستخدم")
        if add_submitted:
            is_strong, strength_message = is_password_strong(password.strip())
            if not fullname.strip() or not username.strip() or not password.strip() or not confirm_password.strip():
                st.warning("يرجى تعبئة جميع الحقول.")
            elif password.strip() != confirm_password.strip():
                st.error("كلمة المرور وتأكيدها غير متطابقين.")
            elif not is_strong:
                st.error(f"❌ {strength_message}")
            elif username_exists(users_df, username):
                st.error("اسم المستخدم مستخدم بالفعل")
            else:
                try:
                    with timed_spinner("جاري إضافة المستخدم..."):
                        add_user(username, password, fullname, ROLE_VALUES[role_label], city)
                    log_action(st.session_state.username, "إضافة مستخدم", f"المستخدم: {username}")
                    st.success("✅ تم إضافة المستخدم بنجاح")
                    st.rerun()
                except Exception as exc:
                    st.error("اسم المستخدم مستخدم بالفعل" if "duplicate" in str(exc).lower() or "unique" in str(exc).lower() else f"تعذر إضافة المستخدم: {exc}")

    with tab_edit:
        options = user_options(users_df)
        if not options:
            st.info("لا يوجد مستخدمون للتعديل.")
        else:
            selected_label = st.selectbox("اختر المستخدم", list(options.keys()), key="edit_user_select")
            selected_user = options[selected_label]
            with st.form("edit_user_form"):
                fullname = st.text_input("الاسم الكامل", value=selected_user["fullname"])
                password = st.text_input("كلمة المرور الجديدة (اتركها فارغة بدون تغيير)", type="password")
                role_current = ROLE_LABELS.get(selected_user["role"], selected_user["role"])
                role_label = st.selectbox("نوع المستخدم", ["مدير", "فني"], index=["مدير", "فني"].index(role_current) if role_current in ["مدير", "فني"] else 0)
                current_city = selected_user.get("city") if selected_user.get("city") in CITIES else CITIES[0]
                city = st.selectbox("المدينة", CITIES, index=CITIES.index(current_city))
                save_submitted = st.form_submit_button("💾 حفظ التعديلات")
            if save_submitted:
                is_strong, strength_message = is_password_strong(password.strip()) if password.strip() else (True, "")
                if not fullname.strip():
                    st.warning("يرجى إدخال الاسم الكامل.")
                elif password.strip() and not is_strong:
                    st.error(f"❌ {strength_message}")
                else:
                    with timed_spinner("جاري حفظ التعديلات..."):
                        update_user(selected_user["id"], fullname, password, ROLE_VALUES[role_label], city=city)
                    log_action(st.session_state.username, "تعديل مستخدم", f"المستخدم: {selected_user['username']}")
                    st.success("✅ تم حفظ التعديلات بنجاح")
                    st.rerun()

    with tab_delete:
        if users_df.empty:
            st.info("لا يوجد مستخدمون للحذف.")
        else:
            display_df = users_df.copy()
            display_df["نوع المستخدم"] = display_df["role"].map(ROLE_LABELS).fillna(display_df["role"])
            selected_ids = selectable_table(
                display_df,
                "id",
                {
                    "fullname": "الاسم الكامل",
                    "username": "اسم المستخدم",
                    "نوع المستخدم": "نوع المستخدم",
                    "city": "المدينة",
                },
                key_prefix="delete_users",
            )
            if confirm_delete_button("delete_users", selected_ids, "🗑️ حذف المستخدمين المحددين", "مستخدم محدد"):
                admins_count = int((users_df["role"] == "admin").sum()) if not users_df.empty else 0
                deleted = 0
                blocked = []
                with timed_spinner("جاري حذف مستخدم..."):
                    for user_id in selected_ids:
                        row = users_df[users_df["id"].astype(int) == int(user_id)].iloc[0]
                        if row["username"] == st.session_state.username:
                            blocked.append(f"{row['fullname']} (لا يمكن حذف المستخدم الذي قام بتسجيل الدخول حالياً)")
                            continue
                        if row["role"] == "admin" and admins_count <= 1:
                            blocked.append(f"{row['fullname']} (لا يمكن حذف آخر مدير في النظام)")
                            continue
                        delete_user(row["id"])
                        deleted += 1
                        log_action(st.session_state.username, "حذف مستخدم", f"المستخدم: {row['username']}")
                        if row["role"] == "admin":
                            admins_count -= 1
                if deleted:
                    st.success(f"✅ تم حذف {deleted} مستخدم بنجاح")
                for message in blocked:
                    st.error(message)
                if deleted:
                    st.rerun()


def username_exists(df, username, exclude_id=None):
    if df.empty:
        return False
    matches = df[df["username"].astype(str).str.lower() == username.strip().lower()]
    if exclude_id is not None:
        matches = matches[matches["id"].astype(int) != int(exclude_id)]
    return not matches.empty


def users_table(df):
    if df.empty:
        st.info("لا يوجد مستخدمون حالياً.")
        return
    display = df.copy()
    display["نوع المستخدم"] = display["role"].map(ROLE_LABELS).fillna(display["role"])
    visible_columns = ["fullname", "username", "نوع المستخدم"]
    if "city" in display.columns:
        visible_columns.append("city")
    if "created_at" in display.columns:
        visible_columns.append("created_at")
    st.dataframe(
        display[visible_columns].rename(
            columns={
                "fullname": "الاسم الكامل",
                "username": "اسم المستخدم",
                "city": "المدينة",
                "created_at": "تاريخ الإنشاء",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )


def user_options(df):
    if df.empty:
        return {}
    return {f"{row['fullname']} ({row['username']})": row for _, row in df.sort_values("fullname").iterrows()}


def inventory_page():
    require_login(["admin"])
    top_nav()
    page_header("📦 المستودع", "إدارة المواد والكميات والتنبيهات المخزنية.")
    with timed_spinner("جاري تحديث البيانات..."):
        df = as_df(get_all_materials(), ["id", "name", "quantity", "unit", "notes"])

    total_materials = len(df)
    c1, c2, c3 = st.columns(3)
    c1.metric("عدد المواد", total_materials)
    c2.metric("إجمالي الكمية", int(df["quantity"].sum()) if total_materials else 0)
    c3.metric("منخفضة المخزون", int((df["quantity"] <= 10).sum()) if total_materials else 0)

    tab_add, tab_list, tab_manage = st.tabs(["➕ إضافة مادة", "📋 المواد", "⚙️ إدارة مادة"])
    with tab_add:
        with st.form("add_material_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("اسم المادة")
                quantity = st.number_input("الكمية", min_value=1, step=1)
            with col2:
                unit = st.selectbox("الوحدة", UNITS)
                notes = st.text_area("الملاحظات", height=100)
            submitted = st.form_submit_button("➕ إضافة المادة")
        if submitted:
            if not name.strip():
                st.warning("يرجى إدخال اسم المادة.")
            else:
                with timed_spinner("جاري إضافة مادة للمستودع..."):
                    exists = material_exists(name)
                    if not exists:
                        add_material(name, quantity, unit, notes)
                        log_action(st.session_state.username, "إضافة مادة", f"المادة: {name}")
                if exists:
                    st.error("هذه المادة موجودة بالفعل.")
                else:
                    st.success("✅ تم إضافة المادة بنجاح.")
                    st.rerun()

    with tab_list:
        with st.form("materials_search_form"):
            search = st.text_input("بحث باسم المادة أو الوحدة أو الملاحظات")
            materials_search_submitted = st.form_submit_button("🔍 بحث")

        if materials_search_submitted:
            st.session_state["materials_search_query"] = search
        search = st.session_state.get("materials_search_query", "")

        filtered = df.copy()
        if search:
            exact_mask = (
                filtered["name"].astype(str).str.contains(search, case=False, na=False)
                | filtered["unit"].astype(str).str.contains(search, case=False, na=False)
                | filtered["notes"].astype(str).str.contains(search, case=False, na=False)
            )
            if exact_mask.any():
                filtered = filtered[exact_mask]
            else:
                # لا يوجد تطابق حرفي: جرّب بحثاً ذكياً (تقريبياً)
                fuzzy_mask = (
                    fuzzy_series_mask(filtered["name"].astype(str), search)
                    | fuzzy_series_mask(filtered["unit"].astype(str), search)
                    | fuzzy_series_mask(filtered["notes"].astype(str), search)
                )
                filtered = filtered[fuzzy_mask]
        display = filtered.rename(columns={"name": "اسم المادة", "quantity": "الكمية", "unit": "الوحدة", "notes": "الملاحظات", "created_at": "تاريخ الإضافة", "updated_at": "آخر تحديث"}).drop(columns=["id"], errors="ignore")
        st.dataframe(display, hide_index=True, use_container_width=True)
        st.caption(f"عدد النتائج: {len(filtered)}")

    with tab_manage:
        if df.empty:
            st.info("لا توجد مواد داخل المستودع.")
            return
        selected_name = st.selectbox("اختر المادة", sorted(df["name"].astype(str).tolist()))
        material = df[df["name"] == selected_name].iloc[0]
        st.success(f"الكمية الحالية: {material['quantity']} {material['unit']}")
        if int(material["quantity"]) <= 10:
            st.warning("هذه المادة منخفضة المخزون.")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("✏️ تعديل المادة")
            edit_name = st.text_input("اسم المادة", value=material["name"])
            current_unit = material["unit"] if material["unit"] in UNITS else "أخرى"
            edit_unit = st.selectbox("الوحدة", UNITS, index=UNITS.index(current_unit))
            edit_notes = st.text_area("الملاحظات", value=material["notes"] or "", height=120)
            if st.button("💾 حفظ التعديلات", use_container_width=True):
                with timed_spinner("جاري تعديل مادة..."):
                    exists = material_exists(edit_name, exclude_id=material["id"])
                    if not exists:
                        update_material(material["id"], edit_name, edit_unit, edit_notes)
                        log_action(st.session_state.username, "تعديل مادة", f"المادة: {edit_name}")
                if exists:
                    st.error("اسم المادة مستخدم بالفعل.")
                else:
                    st.success("✅ تم تعديل المادة بنجاح.")
                    st.rerun()

        with col2:
            st.subheader("📦 إدارة الكمية")
            increase_qty = st.number_input("إضافة كمية", min_value=1, step=1, key="increase_qty")
            if st.button("➕ إضافة للمخزون", use_container_width=True):
                with timed_spinner("جاري إضافة مادة للمستودع..."):
                    increase_material(material["id"], increase_qty)
                log_action(st.session_state.username, "زيادة كمية", f"المادة: {material['name']}, الكمية: {increase_qty}")
                st.success("✅ تمت إضافة الكمية بنجاح.")
                st.rerun()

            decrease_qty = st.number_input("خصم كمية", min_value=1, step=1, key="decrease_qty")
            if st.button("➖ خصم من المخزون", use_container_width=True):
                with timed_spinner("جاري تحديث البيانات..."):
                    success = decrease_material(material["id"], decrease_qty)
                if success:
                    log_action(st.session_state.username, "خصم كمية", f"المادة: {material['name']}, الكمية: {decrease_qty}")
                    st.success("✅ تم خصم الكمية بنجاح.")
                    st.rerun()
                else:
                    st.error("الكمية المطلوبة أكبر من الكمية الموجودة.")

        st.divider()
        st.subheader("🗑 حذف مواد")
        # إعادة استخدام df المجلوبة أعلى الصفحة بدل استعلام get_all_materials() مكرر
        delete_df = df
        selected_ids = selectable_table(
            delete_df,
            "id",
            {
                "name": "اسم المادة",
                "quantity": "الكمية",
                "unit": "الوحدة",
                "notes": "الملاحظات",
            },
            key_prefix="delete_materials",
        )
        if confirm_delete_button("delete_materials", selected_ids, "🗑 حذف المواد المحددة", "مادة محددة"):
            with timed_spinner("جاري حذف مادة..."):
                for material_id in selected_ids:
                    delete_material(int(material_id))
            log_action(st.session_state.username, "حذف مواد", f"عدد: {len(selected_ids)}")
            st.success(f"✅ تم حذف {len(selected_ids)} مادة بنجاح.")
            st.rerun()


def change_password_page():
    require_login(["admin", "technician"])
    top_nav()
    page_header("🔑 تغيير كلمة المرور", f"المستخدم الحالي: {st.session_state.fullname}")
    with st.form("change_password_form"):
        current_password = st.text_input("كلمة المرور الحالية", type="password")
        new_password = st.text_input("كلمة المرور الجديدة", type="password")
        confirm_password = st.text_input("تأكيد كلمة المرور الجديدة", type="password")
        submitted = st.form_submit_button("💾 حفظ")

    if submitted:
        if not current_password.strip() or not new_password.strip() or not confirm_password.strip():
            st.warning("يرجى تعبئة جميع الحقول.")
        elif new_password.strip() != confirm_password.strip():
            st.error("كلمتا المرور غير متطابقتين.")
        else:
            is_strong, strength_message = is_password_strong(new_password.strip())
            if not is_strong:
                st.error(f"❌ {strength_message}")
            else:
                with timed_spinner("جاري حفظ التعديلات..."):
                    valid = check_current_password(st.session_state.username, current_password.strip())
                    if valid:
                        change_password(st.session_state.username, new_password.strip())
                if valid:
                    log_action(st.session_state.username, "تغيير كلمة المرور")
                    st.success("✅ تم تغيير كلمة المرور بنجاح.")
                else:
                    st.error("كلمة المرور الحالية غير صحيحة.")


def _metric_cards(items):
    """صف بطاقات إحصائية موحّد الشكل، يُعاد استخدامه أعلى كل تبويب بمركز
    المطور بدل تكرار st.columns/st.metric في كل تبويب على حدة."""
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def _run_diagnostics():
    """اختبارات ذاتية خفيفة وحقيقية (وليست شكلية): تختبر فعلياً الاتصال
    بقاعدة البيانات، وكتابة/قراءة ملف Excel بالمكتبات الفعلية المستخدمة في
    التطبيق، وجاهزية جدول التقارير. لا تُنفَّذ إلا عند الضغط على الزر."""
    results = []

    db_result = test_db_connection()
    results.append(("اختبار الاتصال بقاعدة البيانات وسرعتها", db_result["connected"], f"{db_result['response_ms']} ms" if db_result["connected"] else db_result["error"]))

    try:
        reports_count = get_system_counts()["reports"]
        results.append(("اختبار جاهزية جدول التقارير (رفع الصور)", True, f"{reports_count} تقرير محفوظ حالياً"))
    except Exception as exc:
        results.append(("اختبار جاهزية جدول التقارير (رفع الصور)", False, str(exc)))

    try:
        sample_df = pd.DataFrame({"عمود": [1, 2, 3]})
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            sample_df.to_excel(writer, index=False)
        results.append(("اختبار التصدير (Excel/openpyxl)", True, f"{len(output.getvalue())} bytes"))
    except Exception as exc:
        results.append(("اختبار التصدير (Excel/openpyxl)", False, str(exc)))

    try:
        output.seek(0)
        read_back = pd.read_excel(output)
        results.append(("اختبار الاستيراد (قراءة Excel)", len(read_back) == 3, f"{len(read_back)} صف"))
    except Exception as exc:
        results.append(("اختبار الاستيراد (قراءة Excel)", False, str(exc)))

    return results


def developer_center_page():
    require_login(["admin"])
    top_nav()
    page_header("🛠️ مركز المطور", "أدوات تقنية للمدير فقط: حالة النظام، الأداء، الأمان، والصيانة.")

    (
        tab_status, tab_users, tab_tasks, tab_inventory, tab_audit,
        tab_errors, tab_maintenance, tab_performance, tab_settings, tab_assistant,
    ) = st.tabs([
        "📊 لوحة الحالة", "👥 المستخدمون", "📋 المهام", "📦 المستودع", "📜 سجل العمليات",
        "⚠️ سجل الأخطاء", "🧹 الصيانة", "📈 الأداء", "⚙️ إعدادات المطور", "🤖 مساعد المطور",
    ])

    with tab_status:
        db_result = test_db_connection()
        db_info = get_database_info()
        _metric_cards([
            ("حالة قاعدة البيانات", "🟢 متصلة" if db_result["connected"] else "🔴 غير متصلة"),
            ("زمن الاستجابة", f"{db_result['response_ms']} ms"),
            ("إصدار التطبيق", APP_VERSION),
        ])
        _metric_cards([
            ("إصدار PostgreSQL", db_info["version"]),
            ("حجم قاعدة البيانات", db_info["size"]),
            ("اتصالات نشطة الآن", db_info["active_connections"] if db_info["active_connections"] is not None else "غير متاح"),
        ])
        if not db_result["connected"]:
            st.error(f"تعذّر الاتصال بقاعدة البيانات: {db_result['error']}")

    with tab_users:
        counts = get_system_counts()
        security = get_security_overview()

        _metric_cards([
            ("إجمالي المستخدمين", counts["users"]),
            ("المستخدمون المتصلون", len(security.get("online_now", []))),
            ("الحسابات المقفلة", len(security.get("locked", []))),
        ])

        st.divider()

        st.subheader("🟢 المستخدمون المتصلون حالياً")
        online = pd.DataFrame(security.get("online_now", []))
        if online.empty:
            st.info("لا يوجد مستخدمون متصلون حالياً.")
        else:
            st.dataframe(online, hide_index=True, use_container_width=True)

        st.subheader("🕒 آخر عمليات تسجيل الدخول")
        recent = pd.DataFrame(security.get("recent_logins", []))
        if recent.empty:
            st.info("لا توجد عمليات تسجيل دخول.")
        else:
            st.dataframe(recent, hide_index=True, use_container_width=True)

    with tab_tasks:
        counts = get_system_counts()
        breakdown = get_tasks_breakdown()
        _metric_cards([
            ("عدد المهام المنفذة", counts["tasks"]),
            ("عدد المهام المسندة", counts["assigned_tasks"]),
            ("عدد التقارير", counts["reports"]),
        ])
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption("حسب المدينة")
            st.dataframe(as_df(breakdown["by_city"]), hide_index=True, use_container_width=True)
        with col2:
            st.caption("حسب الحالة")
            st.dataframe(as_df(breakdown["by_status"]), hide_index=True, use_container_width=True)
        with col3:
            st.caption("حسب النوع")
            st.dataframe(as_df(breakdown["by_type"]), hide_index=True, use_container_width=True)

    with tab_inventory:
        counts = get_system_counts()
        with timed_spinner("جاري تحديث البيانات..."):
            materials_df = as_df(get_all_materials(), ["id", "name", "quantity", "unit", "notes"])
        _metric_cards([
            ("عدد المواد", counts["materials"]),
            ("مواد منخفضة المخزون", counts["low_stock_materials"]),
        ])
        low_stock = materials_df[materials_df["quantity"] <= 5] if not materials_df.empty else materials_df
        st.caption("المواد منخفضة المخزون (5 وحدات أو أقل)")
        st.dataframe(low_stock.rename(columns={"name": "اسم المادة", "quantity": "الكمية", "unit": "الوحدة"}), hide_index=True, use_container_width=True)
        inventory_log = as_df(get_audit_log(300))
        if not inventory_log.empty:
            inventory_log = inventory_log[inventory_log["action"].isin(["إضافة مادة", "تعديل مادة", "زيادة كمية", "خصم كمية"])]
        st.caption("آخر عمليات المستودع (إضافة / تعديل / زيادة / خصم)")
        st.dataframe(inventory_log.head(30), hide_index=True, use_container_width=True)

    with tab_audit:
        with timed_spinner("جاري تحديث البيانات..."):
            audit_df = as_df(get_audit_log(500))
        with st.form("audit_filter_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                search = st.text_input("بحث في السجل", key="audit_search")
            with col2:
                user_filter = st.selectbox("تصفية حسب المستخدم", ["الكل"] + (sorted(audit_df["username"].dropna().unique().tolist()) if not audit_df.empty else []), key="audit_user_filter")
            with col3:
                action_filter = st.selectbox("تصفية حسب نوع العملية", ["الكل"] + (sorted(audit_df["action"].dropna().unique().tolist()) if not audit_df.empty else []), key="audit_action_filter")
            date_filter = st.date_input("تصفية حسب التاريخ (اختياري)", value=None, key="audit_date_filter")
            audit_filter_submitted = st.form_submit_button("🔍 تصفية")

        if audit_filter_submitted:
            st.session_state["audit_filter_params"] = (search, user_filter, action_filter, date_filter)
        search, user_filter, action_filter, date_filter = st.session_state.get(
            "audit_filter_params", ("", "الكل", "الكل", None)
        )

        filtered = audit_df.copy()
        if not filtered.empty:
            if search.strip():
                mask = (
                    filtered["username"].astype(str).str.contains(search, case=False, na=False)
                    | filtered["action"].astype(str).str.contains(search, case=False, na=False)
                    | filtered["details"].astype(str).str.contains(search, case=False, na=False)
                )
                filtered = filtered[mask]
            if user_filter != "الكل":
                filtered = filtered[filtered["username"] == user_filter]
            if action_filter != "الكل":
                filtered = filtered[filtered["action"] == action_filter]
            if date_filter:
                filtered = filtered[pd.to_datetime(filtered["created_at"]).dt.date == date_filter]
        st.dataframe(filtered, hide_index=True, use_container_width=True)
        _export_results_button(filtered.to_dict("records"), "سجل_العمليات.xlsx", "audit_log_export")

    with tab_errors:
        with timed_spinner("جاري تحديث البيانات..."):
            errors_df = as_df(get_error_log(200))
        _metric_cards([("عدد الأخطاء المسجَّلة", len(errors_df))])
        st.dataframe(errors_df, hide_index=True, use_container_width=True)
        if errors_df.empty:
            st.info("لا توجد أخطاء مسجَّلة حتى الآن.")

    with tab_maintenance:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🧹 تنظيف Cache", use_container_width=True):
                cleanup_cache()
                log_action(st.session_state.username, "تنظيف Cache")
                st.success("✅ تم تنظيف الكاش بنجاح.")
        with col2:
            if st.button("🏗️ إعادة إنشاء الجداول", use_container_width=True):
                with timed_spinner("جاري إعادة إنشاء الجداول..."):
                    create_tables()
                log_action(st.session_state.username, "إعادة إنشاء الجداول")
                st.success("✅ تم التأكد من الجداول والفهارس (Migration آمن، لا حذف بيانات).")
        with col3:
            if st.button("🔌 اختبار الاتصال بقاعدة البيانات", use_container_width=True):
                result = test_db_connection()
                if result["connected"]:
                    st.success(f"✅ الاتصال يعمل ({result['response_ms']} ms).")
                else:
                    st.error(f"❌ فشل الاتصال: {result['error']}")

        st.divider()
        if st.button("🧪 اختبار جميع الخدمات", use_container_width=True):
            with timed_spinner("جاري تشغيل الاختبارات..."):
                diagnostics = _run_diagnostics()
            for name, ok, detail in diagnostics:
                (st.success if ok else st.error)(f"{'✅' if ok else '❌'} {name}: {detail}")

    with tab_performance:
        stats = get_query_stats()
        _metric_cards([
            ("عدد الاستعلامات (منذ بدء التشغيل)", stats["count"]),
            ("متوسط زمن الاستجابة", f"{stats['avg_ms']:.1f} ms"),
        ])
        st.caption("أبطأ 10 استعلامات (منذ بدء تشغيل هذه الجلسة)")
        slow_df = pd.DataFrame(stats["slowest"], columns=["الزمن (ms)", "الاستعلام"]) if stats["slowest"] else pd.DataFrame(columns=["الزمن (ms)", "الاستعلام"])
        st.dataframe(slow_df, hide_index=True, use_container_width=True)

        st.caption("استخدام Cache في المشروع (@st.cache_data لكل عمليات القراءة، ttl=20 ثانية)")
        st.write("المستخدمون، المهام، المهام المسندة، المهام المنفذة، التقارير، إحصاءات مركز المطور — جميعها مخزَّنة مؤقتاً ويُمسح الكاش المرتبط مباشرة بعد أي عملية كتابة.")

        suggestions = []
        if stats["avg_ms"] > 200:
            suggestions.append("متوسط زمن الاستعلامات مرتفع نسبياً — راجع الفهارس على الأعمدة الأكثر استخداماً في البحث.")
        if stats["count"] > 0 and not stats["slowest"]:
            suggestions.append("لا توجد استعلامات بطيئة ملحوظة حتى الآن — الأداء جيد.")
        if not suggestions:
            suggestions.append("لا توجد ملاحظات أداء حرجة حالياً بناءً على البيانات المتاحة في هذه الجلسة.")
        st.caption("اقتراحات تحسين الأداء")
        for suggestion in suggestions:
            st.write(f"• {suggestion}")

    with tab_settings:
        _metric_cards([
            ("إصدار Python", platform.python_version()),
            ("إصدار Streamlit", st.__version__),
            ("إصدار PostgreSQL", get_database_info()["version"]),
        ])
        st.caption("إصدارات المكتبات الأساسية")
        st.dataframe(
            pd.DataFrame([
                {"المكتبة": "pandas", "الإصدار": pd.__version__},
                {"المكتبة": "psycopg2", "الإصدار": psycopg2.__version__},
                {"المكتبة": "bcrypt", "الإصدار": getattr(bcrypt, "__version__", "غير متاح")},
            ]),
            hide_index=True, use_container_width=True,
        )
        st.caption("معلومات الخادم")
        st.write(f"النظام: {platform.platform()}")
        st.checkbox(
            "تفعيل وضع التشخيص (يعرض تفاصيل تقنية إضافية عند حدوث أخطاء)",
            key="developer_diagnostic_mode",
            value=st.session_state.get("developer_diagnostic_mode", False),
        )

    with tab_assistant:
        st.caption("مساعد يجيب عن حالة النظام اعتماداً على بيانات حقيقية من قاعدة البيانات وسجلات التشغيل (بدون أي بيانات وهمية).")
        questions = {
            "لماذا التطبيق بطيء؟": lambda: _assistant_answer_slowness(),
            "هل توجد أخطاء؟": lambda: _assistant_answer_errors(),
            "هل قاعدة البيانات تعمل؟": lambda: _assistant_answer_db(),
            "كم عدد المهام؟": lambda: _assistant_answer_task_counts(),
            "ما أبطأ الاستعلامات؟": lambda: _assistant_answer_slow_queries(),
            "هل يوجد مستخدمون متصلون؟": lambda: _assistant_answer_online_users(),
            "هل توجد محاولات دخول فاشلة؟": lambda: _assistant_answer_failed_logins(),
            "ما الذي يحتاج إلى تحسين؟": lambda: _assistant_answer_improvements(),
        }
        cols = st.columns(2)
        for index, (question, handler) in enumerate(questions.items()):
            if cols[index % 2].button(question, use_container_width=True, key=f"assistant_q_{index}"):
                st.session_state["developer_assistant_answer"] = handler()
        answer = st.session_state.get("developer_assistant_answer")
        if answer:
            st.info(answer)


def _assistant_answer_db():
    result = test_db_connection()
    if result["connected"]:
        return f"✅ قاعدة البيانات تعمل بشكل طبيعي، وزمن الاستجابة الحالي {result['response_ms']} ms."
    return f"🔴 قاعدة البيانات غير متصلة حالياً. الخطأ: {result['error']}"


def _assistant_answer_task_counts():
    counts = get_system_counts()
    return f"عدد المهام المنفذة: {counts['tasks']}، المهام المسندة: {counts['assigned_tasks']}، التقارير: {counts['reports']}."


def _assistant_answer_slow_queries():
    stats = get_query_stats()
    if not stats["slowest"]:
        return "لا توجد بيانات كافية بعد عن استعلامات بطيئة في هذه الجلسة."
    top_ms, top_query = stats["slowest"][0]
    return f"أبطأ استعلام سُجّل في هذه الجلسة استغرق {top_ms:.1f} ms: {top_query}"


def _assistant_answer_slowness():
    stats = get_query_stats()
    db = test_db_connection()
    if not db["connected"]:
        return "🔴 التطبيق بطيء على الأرجح بسبب فقدان الاتصال بقاعدة البيانات."
    if stats["avg_ms"] > 200:
        return f"متوسط زمن الاستعلامات مرتفع ({stats['avg_ms']:.1f} ms) — راجع تبويب 📈 الأداء لمعرفة أبطأ الاستعلامات."
    return "لا توجد مؤشرات بطء واضحة حالياً بناءً على بيانات هذه الجلسة؛ زمن الاستجابة وسرعة الاستعلامات طبيعيان."


def _assistant_answer_errors():
    errors = get_error_log(50)
    if not errors:
        return "✅ لا توجد أخطاء مسجَّلة حديثاً."
    return f"⚠️ يوجد {len(errors)} خطأ مسجَّل مؤخراً. راجع تبويب ⚠️ سجل الأخطاء للتفاصيل."


def _assistant_answer_online_users():
    online = get_security_overview()["online_now"]
    if not online:
        return "لا يوجد مستخدمون متصلون حالياً (بناءً على تسجيل دخول خلال آخر 15 دقيقة)."
    names = "، ".join(row["fullname"] for row in online)
    return f"يوجد {len(online)} مستخدم متصل تقريباً الآن: {names}."


def _assistant_answer_failed_logins():
    failed = get_security_overview()["failed_attempts"]
    locked = get_security_overview()["locked"]
    if not failed and not locked:
        return "✅ لا توجد محاولات دخول فاشلة حالياً، ولا حسابات مقفلة."
    parts = []
    if failed:
        parts.append(f"{len(failed)} حساباً عليه محاولات فاشلة غير مكتملة القفل")
    if locked:
        parts.append(f"{len(locked)} حساباً مقفلاً حالياً")
    return "⚠️ " + " و".join(parts) + "."


def _assistant_answer_improvements():
    suggestions = []
    stats = get_query_stats()
    if stats["avg_ms"] > 200:
        suggestions.append("مراجعة الفهارس على الأعمدة الأكثر استخداماً في البحث")
    errors = get_error_log(50)
    if errors:
        suggestions.append("مراجعة سجل الأخطاء الأخير")
    locked = get_security_overview()["locked"]
    if locked:
        suggestions.append("مراجعة الحسابات المقفلة حالياً")
    if not suggestions:
        return "لا توجد ملاحظات تحسين حرجة حالياً — النظام يعمل ضمن المعدل الطبيعي."
    return "يُقترح: " + "، ".join(suggestions) + "."


def route():
    if not st.session_state.get("logged_in"):
        login_screen()
        return

    pages = {
        "home": home_screen,
        "dashboard": dashboard_page,
        "admin": admin_page,
        "technician": technician_page,
        "assign_tasks": admin_page,
        "reports": reports_page,
        "inventory": inventory_page,
        "users": users_page,
        "developer_center": developer_center_page,
        "change_password": change_password_page,
    }
    page = st.session_state.get("current_page", "home")
    handler = pages.get(page, home_screen)
    try:
        handler()
    except Exception as exc:
        LOGGER.exception("Unhandled page error in %s", handler.__name__)
        log_error(type(exc).__name__, "app.py", handler.__name__, str(exc))
        st.error("⚠️ حدث خطأ غير متوقع أثناء تحميل هذه الصفحة. تم تسجيل الخطأ تلقائياً.")
        if st.session_state.get("developer_diagnostic_mode") and st.session_state.get("role") == "admin":
            st.exception(exc)


route()
