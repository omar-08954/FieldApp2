from io import BytesIO

import pandas as pd
import streamlit as st

from database.database import (
    CITIES,
    add_material,
    add_task,
    add_user,
    assign_task,
    assigned_task_number_exists,
    change_password,
    check_current_password,
    complete_assigned_task,
    decrease_material,
    delete_assigned_task,
    delete_material,
    delete_task,
    delete_user,
    get_all_materials,
    get_all_users,
    get_assigned_task_by_number,
    get_daily_report,
    increase_material,
    login_user,
    material_exists,
    resolve_column_mapping,
    resolve_known_technician,
    save_daily_report,
    search_assigned_tasks,
    search_completed_tasks,
    search_tasks,
    task_exists,
    update_material,
    update_task,
    delete_tasks,
    update_user
)
from ui import TASK_STATUSES, TASK_TYPES, assigned_task_dataframe, confirm_delete_button, date_selector, fuzzy_series_mask, init_page, logout, page_header, require_login, selectable_table, task_dataframe, timed_spinner, top_nav


ROLE_LABELS = {"admin": "مدير", "technician": "فني"}
ROLE_VALUES = {label: value for value, label in ROLE_LABELS.items()}
UNITS = ["حبة", "متر", "بكرة", "كرتون", "رول", "كيس", "علبة", "أخرى"]


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
                    user = login_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.fullname = user["fullname"]
                    st.session_state.username = user["username"]
                    st.session_state.role = user["role"]
                    st.session_state.city = user.get("city") or ""
                    st.session_state.current_page = "home"
                    st.success("✅ تم تسجيل الدخول بنجاح")
                    st.rerun()
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
            ("🛠️ صفحة الفني", "technician"),
            ("📌 إسناد المهام", "assign_tasks"),
            ("📋 المهام المسندة", "assigned_tasks"),
            ("📑 صفحة التقارير", "reports"),
            ("📦 المستودع", "inventory"),
            ("👥 إدارة المستخدمين", "users"),
            ("🔑 تغيير كلمة المرور", "change_password"),
        ]
    else:
        cards = [
            ("🛠️ صفحة الفني", "technician"),
            ("📋 المهام المسندة", "assigned_tasks"),
            ("📅 المهام اليومية", "daily_tasks"),
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
    col1, col2, col3 = st.columns(3)
    with col1:
        technician = st.selectbox("الفني", ["الكل"] + sorted(df["technician"].dropna().unique().tolist()))
    with col2:
        task_type = st.selectbox("نوع المهمة", ["الكل"] + TASK_TYPES)
    with col3:
        task_status = st.selectbox("حالة المهمة", ["الكل"] + TASK_STATUSES)
    keyword = st.text_input("بحث ذكي برقم المهمة أو الاشتراك أو نوع المهمة أو حالتها")

    with timed_spinner("جاري البحث عن المهمة..."):
        filtered = as_df(search_tasks(keyword, technician, task_type, task_status))

    st.subheader("📈 أداء الفنيين")
    st.bar_chart(df.groupby("technician").size().reset_index(name="عدد المهام").set_index("technician"))
    st.subheader("📋 المهام")
    task_dataframe(filtered)


def technician_page():
    require_login(["admin", "technician"])
    top_nav()
    page_header("🛠️ صفحة الفني", "تسجيل المهام اليومية بسرعة وبدون تكرار رقم المهمة.")

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
            if exists:
                st.error("❌ لا يمكن إضافة نفس رقم المهمة مرتين.")
            else:
                st.success("✅ تم حفظ المهمة بنجاح.")


def select_task_from_search(state_prefix, title):
    keyword = st.text_input(title, key=f"{state_prefix}_keyword")
    if st.button("🔍 البحث", key=f"{state_prefix}_search_btn", use_container_width=True):
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


def _technician_names():
    with timed_spinner("جاري تحديث البيانات..."):
        technicians_df = as_df(get_all_users(), ["id", "username", "fullname", "role", "city"])
    if technicians_df.empty:
        return []
    return sorted(technicians_df[technicians_df["role"] == "technician"]["fullname"].tolist())


def assign_tasks_page():
    require_login(["admin"])
    top_nav()
    page_header("📌 إسناد المهام", "إسناد مهام جديدة للفنيين لتنفيذها.")

    with timed_spinner("جاري تحديث البيانات..."):
        technicians_df = as_df(get_all_users(), ["id", "username", "fullname", "role", "city"])
    technicians_only = technicians_df[technicians_df["role"] == "technician"] if not technicians_df.empty else technicians_df
    technicians = sorted(technicians_only["fullname"].tolist()) if not technicians_only.empty else []
    # قراءة مدينة كل فني من جدول المستخدمين لتحديدها تلقائياً عند الإسناد
    technician_city_map = (
        {row["fullname"]: (row.get("city") or "") for _, row in technicians_only.iterrows()}
        if not technicians_only.empty else {}
    )

    tab_add, tab_search = st.tabs(["📌 إسناد مهمة", "🔍 بحث في المهام المسندة"])

    with tab_add:
        if not technicians:
            st.info("لا يوجد فنيون مسجلون لإسناد المهام إليهم.")
        else:
            with st.form("assign_task_form", clear_on_submit=True):
                technician = st.selectbox("اختر الفني", technicians)
                task_number = st.text_input("رقم المهمة")
                subscription_number = st.text_input("رقم الاشتراك")
                submitted = st.form_submit_button("📌 إسناد المهمة")

            if submitted:
                task_number = task_number.strip()
                subscription_number = subscription_number.strip()
                if not task_number or not subscription_number:
                    st.warning("يرجى إدخال رقم المهمة ورقم الاشتراك.")
                else:
                    with timed_spinner("💾 جاري حفظ المهمة..."):
                        exists = assigned_task_number_exists(task_number)
                        if not exists:
                            # المدينة تُحدَّد تلقائياً من مدينة الفني المسجلة في جدول المستخدمين
                            assign_task(
                                technician,
                                task_number,
                                subscription_number,
                                city=technician_city_map.get(technician, ""),
                                assigned_by=st.session_state.fullname,
                            )
                    if exists:
                        st.error("❌ لا يمكن إضافة نفس رقم المهمة مرتين.")
                    else:
                        st.success("✅ تم حفظ المهمة بنجاح.")

    with tab_search:
        technician_filter = st.selectbox("الفني", ["الكل"] + technicians, key="assign_search_tech")
        search_date = date_selector("assign_search_date")
        if st.button("👁️ عرض", key="assign_search_btn", use_container_width=True):
            if search_date is None:
                st.error("تاريخ غير صحيح.")
            else:
                with timed_spinner("جاري البحث عن المهمة..."):
                    st.session_state["assign_search_results"] = search_assigned_tasks(technician_filter, search_date)

        results = st.session_state.get("assign_search_results", [])
        assigned_task_dataframe(as_df(results))


def assigned_tasks_page():
    require_login(["admin", "technician"])
    top_nav()
    page_header("📋 المهام المسندة", "عرض المهام المسندة حسب التاريخ.")

    is_admin = st.session_state.role == "admin"
    if is_admin:
        technicians = _technician_names()
        technician_filter = st.selectbox("الفني", ["الكل"] + technicians, key="assigned_view_tech")
    else:
        technician_filter = st.session_state.fullname

    view_date = date_selector("assigned_view_date")
    if st.button("👁️ عرض", key="assigned_view_btn", use_container_width=True):
        if view_date is None:
            st.error("تاريخ غير صحيح.")
        else:
            with timed_spinner("جاري تحديث البيانات..."):
                st.session_state["assigned_view_results"] = search_assigned_tasks(technician_filter, view_date)

    results = st.session_state.get("assigned_view_results", [])
    assigned_task_dataframe(as_df(results))

    if is_admin and results:
        st.divider()
        st.subheader("🗑 حذف مهام مسندة")
        delete_df = as_df(results)
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
            key_prefix="delete_assigned_tasks",
        )
        if confirm_delete_button("delete_assigned_tasks", selected_ids, "🗑 حذف المهام المسندة المحددة", "مهمة مسندة محددة"):
            with timed_spinner("جاري حذف المهمة..."):
                for assigned_id in selected_ids:
                    delete_assigned_task(assigned_id)
            st.success(f"✅ تم حذف {len(selected_ids)} مهمة بنجاح.")
            st.session_state.pop("assigned_view_results", None)
            st.rerun()


def _completed_tasks_view(technician_filter, key_prefix):
    """عرض المهام المنفذة حسب الفني والتاريخ."""

    completed_date = date_selector(f"{key_prefix}_date")

    if st.button("👁️ عرض", key=f"{key_prefix}_btn", use_container_width=True):
        if completed_date is None:
            st.error("تاريخ غير صحيح.")
        else:
            with timed_spinner("جاري تحديث البيانات..."):
                st.session_state[f"{key_prefix}_results"] = search_completed_tasks(
                    technician_filter,
                    completed_date,
                )

    results = st.session_state.get(f"{key_prefix}_results", [])

    st.write("اسم الفني:", technician_filter)
    st.write("التاريخ المختار:", completed_date)
    st.write("عدد النتائج:", len(results))

    task_dataframe(as_df(results))


def daily_tasks_page():
    require_login(["technician"])
    top_nav()
    page_header("📅 المهام اليومية", "عرض المهام المنفذة يومياً ورفع تقرير المهمة.")

    tab_completed, tab_report = st.tabs(["✅ المهام المنفذة", "📷 إضافة تقرير"])

    with tab_completed:
        _completed_tasks_view(st.session_state.fullname, "daily_completed")

    with tab_report:
        report_date = date_selector("daily_report_date")
        if st.button("👁️ عرض", key="daily_report_view_btn", use_container_width=True):
            if report_date is None:
                st.error("تاريخ غير صحيح.")
            else:
                with timed_spinner("جاري تحديث البيانات..."):
                    existing = get_daily_report(st.session_state.fullname, report_date)
                st.session_state["daily_report_selected_date"] = report_date
                st.session_state["daily_report_existing"] = existing

        selected_date = st.session_state.get("daily_report_selected_date")
        if selected_date:
            existing = st.session_state.get("daily_report_existing")
            if existing:
                st.success("✅ يوجد تقرير محفوظ لهذا التاريخ. يمكنك استبداله برفع صورة جديدة.")
                st.image(bytes(existing["image_data"]), use_container_width=True)
            else:
                st.info("لا يوجد تقرير لهذا التاريخ بعد.")

            uploaded_report = st.file_uploader("📷 إضافة تقرير", type=["jpg", "jpeg", "png"], key="daily_report_uploader")
            if uploaded_report is not None and st.button("💾 حفظ التقرير", key="daily_report_save_btn", use_container_width=True):
                with timed_spinner("💾 جاري حفظ المهمة..."):
                    save_daily_report(
                        st.session_state.fullname,
                        selected_date,
                        uploaded_report.getvalue(),
                        uploaded_report.type or "image/jpeg",
                    )
                st.success("✅ تم حفظ المهمة بنجاح.")
                st.session_state.pop("daily_report_existing", None)
                st.rerun()


def admin_page():
    require_login(["admin"])
    top_nav()
    page_header("📋 لوحة المدير", "إدارة المهام، البحث، الاستيراد، التعديل، والحذف.")
    with timed_spinner("جاري تحديث البيانات..."):
        df = as_df(search_tasks(), ["id", "technician", "task_number", "subscription_number", "task_type", "task_status"])

    tab_manage, tab_data, tab_transfer, tab_task_reports, tab_daily_tasks = st.tabs(
        ["📋 إدارة المهام", "✏️ إدارة البيانات", "📥 الاستيراد والتصدير", "📷 تقارير المهام", "📅 المهام اليومية"]
    )
    with tab_manage:
        total = len(df)
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي المهام", total)
        c2.metric("المزالة", int((df["task_status"] == "مزال").sum()) if total else 0)
        c3.metric("العوائق", int((df["task_status"] == "عائق").sum()) if total else 0)

        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            keyword = st.text_input("بحث ذكي")
        with col2:
            status = st.selectbox("الحالة", ["الكل"] + TASK_STATUSES)
        with col3:
            task_type = st.selectbox("النوع", ["الكل"] + TASK_TYPES)
        with timed_spinner("جاري البحث عن المهمة..."):
            filtered = as_df(search_tasks(keyword, task_type=task_type, task_status=status))
        task_dataframe(filtered)
        st.caption(f"عدد النتائج: {len(filtered)}")

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
            st.success(f"✅ تم حذف {len(selected_ids)} مهمة بنجاح.")
            st.rerun()

    with tab_transfer:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📥 استيراد Excel")
            uploaded = st.file_uploader("اختر ملف Excel", type=["xlsx"])
            if uploaded:
                incoming = pd.read_excel(uploaded)
                # مطابقة أسماء الأعمدة تلقائياً (بالاسم أو بمحتوى العمود) حتى لو اختلفت عن الأسماء المتوقعة
                column_map = resolve_column_mapping(incoming.columns, incoming)
                if column_map:
                    incoming = incoming.rename(columns=column_map)
                columns = [column for column in ["الفني", "رقم المهمة", "رقم الاشتراك", "نوع المهمة", "حالة المهمة"] if column in incoming.columns]
                st.dataframe(incoming[columns].head(20), hide_index=True, use_container_width=True)
                if st.button("بدء الاستيراد", use_container_width=True):
                    added = duplicated = 0
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

                        for _, row in incoming.iterrows():
                            number = str(row.get("رقم المهمة", "")).strip()
                            if not number or number in existing_numbers:
                                duplicated += 1
                                continue
                            raw_technician = str(row.get("الفني", "")).strip() or "غير محدد"
                            # مطابقة تقريبية (Fuzzy) لاسم الفني مع الفنيين الموجودين بالفعل
                            resolved_technician = resolve_known_technician(raw_technician, technician_names)
                            # إذا تم التعرف على الفني، تُستخدم مدينته من قاعدة البيانات دائماً
                            # (حتى لو كانت فارغة) وليس من ملف Excel
                            if resolved_technician in technician_city_map:
                                resolved_city = technician_city_map[resolved_technician]
                            else:
                                resolved_city = str(row.get("المدينة", "")).strip()
                            add_task(
                                resolved_technician,
                                number,
                                str(row.get("رقم الاشتراك", "")).strip(),
                                str(row.get("نوع المهمة", "تقني")).strip(),
                                str(row.get("حالة المهمة", "عائق")).strip(),
                                city=resolved_city,
                                notes=str(row.get("الملاحظات", "")).strip(),
                            )
                            existing_numbers.add(number)
                            added += 1
                    st.success(f"✅ تمت إضافة {added} مهمة، وتجاهل {duplicated} مهمة مكررة.")
                    st.rerun()
        with col2:
            st.subheader("📤 تصدير Excel")
            export_type = st.selectbox("نوع المهمة", ["الكل"] + TASK_TYPES, key="export_task_type")
            export_status = st.selectbox("حالة المهمة", ["الكل"] + TASK_STATUSES, key="export_task_status")
            with timed_spinner("جاري تصدير البيانات..."):
                export_df = df
                if export_type != "الكل":
                    export_df = export_df[export_df["task_type"] == export_type]
                if export_status != "الكل":
                    export_df = export_df[export_df["task_status"] == export_status]
                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    export_df.drop(columns=["id"], errors="ignore").to_excel(writer, index=False)
            st.download_button(
                "تحميل ملف Excel",
                data=output.getvalue(),
                file_name="tasks.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    with tab_task_reports:
        with timed_spinner("جاري تحديث البيانات..."):
            technicians_df = as_df(get_all_users(), ["id", "username", "fullname", "role", "city"])
        technicians = (
            sorted(technicians_df[technicians_df["role"] == "technician"]["fullname"].tolist())
            if not technicians_df.empty else []
        )
        if not technicians:
            st.info("لا يوجد فنيون مسجلون.")
        else:
            technician = st.selectbox("اسم الفني", technicians, key="admin_report_tech")
            report_date = date_selector("admin_report_date")
            if st.button("👁️ عرض التقرير", key="admin_report_view_btn", use_container_width=True):
                if report_date is None:
                    st.error("تاريخ غير صحيح.")
                else:
                    with timed_spinner("جاري تحديث البيانات..."):
                        st.session_state["admin_report_result"] = get_daily_report(technician, report_date)
                    st.session_state["admin_report_query"] = (technician, report_date)

            query = st.session_state.get("admin_report_query")
            if query == (technician, report_date):
                result = st.session_state.get("admin_report_result")
                if result:
                    st.image(bytes(result["image_data"]), use_container_width=True)
                else:
                    st.info("لا يوجد تقرير لهذا الفني في هذا التاريخ.")

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


def _city_report_tab(city):
    with timed_spinner("جاري إنشاء التقرير..."):
        df = as_df(search_tasks(city=city))
    if df.empty:
        st.info("لا توجد بيانات لهذه المدينة.")
        return

    col1, col2 = st.columns(2)
    with col1:
        task_type = st.selectbox("نوع المهمة", ["الكل"] + TASK_TYPES, key=f"report_type_{city}")
    with col2:
        task_status = st.selectbox("حالة المهمة", ["الكل"] + TASK_STATUSES, key=f"report_status_{city}")
    keyword = st.text_input(
        "بحث ذكي برقم المهمة أو الاشتراك أو نوع المهمة أو حالتها أو اسم الفني",
        key=f"report_keyword_{city}",
    )
    with timed_spinner("جاري إنشاء التقرير..."):
        # city يُمرر دائماً لضمان عدم اختلاط بيانات المدينتين
        filtered = as_df(search_tasks(keyword, task_type=task_type, task_status=task_status, city=city))

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
        search = st.text_input("بحث بالاسم أو اسم المستخدم")
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
            if not fullname.strip() or not username.strip() or not password.strip() or not confirm_password.strip():
                st.warning("يرجى تعبئة جميع الحقول.")
            elif password.strip() != confirm_password.strip():
                st.error("كلمة المرور وتأكيدها غير متطابقين.")
            elif username_exists(users_df, username):
                st.error("اسم المستخدم مستخدم بالفعل")
            else:
                try:
                    with timed_spinner("جاري إضافة المستخدم..."):
                        add_user(username, password, fullname, ROLE_VALUES[role_label], city)
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
                if not fullname.strip():
                    st.warning("يرجى إدخال الاسم الكامل.")
                else:
                    with timed_spinner("جاري حفظ التعديلات..."):
                        update_user(selected_user["id"], fullname, password, ROLE_VALUES[role_label], city=city)
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
                if exists:
                    st.error("هذه المادة موجودة بالفعل.")
                else:
                    st.success("✅ تم إضافة المادة بنجاح.")
                    st.rerun()

    with tab_list:
        search = st.text_input("بحث باسم المادة أو الوحدة أو الملاحظات")
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
                st.success("✅ تمت إضافة الكمية بنجاح.")
                st.rerun()

            decrease_qty = st.number_input("خصم كمية", min_value=1, step=1, key="decrease_qty")
            if st.button("➖ خصم من المخزون", use_container_width=True):
                with timed_spinner("جاري تحديث البيانات..."):
                    success = decrease_material(material["id"], decrease_qty)
                if success:
                    st.success("✅ تم خصم الكمية بنجاح.")
                    st.rerun()
                else:
                    st.error("الكمية المطلوبة أكبر من الكمية الموجودة.")

        st.divider()
        st.subheader("🗑 حذف مواد")
        with timed_spinner("جاري تحديث البيانات..."):
            delete_df = as_df(get_all_materials(), ["id", "name", "quantity", "unit", "notes"])
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
        elif len(new_password.strip()) < 4:
            st.error("يجب أن تكون كلمة المرور 4 أحرف على الأقل.")
        else:
            with timed_spinner("جاري حفظ التعديلات..."):
                valid = check_current_password(st.session_state.username, current_password.strip())
                if valid:
                    change_password(st.session_state.username, new_password.strip())
            if valid:
                st.success("✅ تم تغيير كلمة المرور بنجاح.")
            else:
                st.error("كلمة المرور الحالية غير صحيحة.")


def route():
    if not st.session_state.get("logged_in"):
        login_screen()
        return

    pages = {
        "home": home_screen,
        "dashboard": dashboard_page,
        "admin": admin_page,
        "technician": technician_page,
        "assign_tasks": assign_tasks_page,
        "assigned_tasks": assigned_tasks_page,
        "daily_tasks": daily_tasks_page,
        "reports": reports_page,
        "inventory": inventory_page,
        "users": users_page,
        "change_password": change_password_page,
    }
    page = st.session_state.get("current_page", "home")
    pages.get(page, home_screen)()


route()
