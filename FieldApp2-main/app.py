from io import BytesIO

import pandas as pd
import streamlit as st

from database.database import (
    add_material,
    add_task,
    add_user,
    change_password,
    check_current_password,
    create_tables,
    decrease_material,
    delete_material,
    delete_task,
    delete_user,
    get_all_materials,
    get_all_users,
    increase_material,
    login_user,
    material_exists,
    search_tasks,
    task_exists,
    update_material,
    update_task,
    update_user,
)
from ui import TASK_STATUSES, TASK_TYPES, init_page, logout, page_header, require_login, task_dataframe, top_nav


ROLE_LABELS = {"admin": "مدير", "technician": "فني"}
ROLE_VALUES = {label: value for value, label in ROLE_LABELS.items()}
UNITS = ["حبة", "متر", "بكرة", "كرتون", "رول", "كيس", "علبة", "أخرى"]


init_page("شركة الفكر الصاعد للمقاولات", "wide")
create_tables()


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
            submitted = st.form_submit_button("🔑 تسجيل الدخول", width="stretch")
        if submitted:
            username = username.strip()
            password = password.strip()
            if not username or not password:
                st.warning("يرجى إدخال اسم المستخدم وكلمة المرور.")
            else:
                with st.spinner("جاري تسجيل الدخول..."):
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
    if st.button(label, width="stretch"):
        go_to(page_key)


def home_screen():
    require_login()
    page_header("🏠 الرئيسية", f"مرحباً {st.session_state.fullname}، اختر القسم المطلوب للانتقال مباشرة.")
    if st.session_state.role == "admin":
        cards = [
            ("📊 لوحة التحكم", "dashboard"),
            ("📋 لوحة المدير", "admin"),
            ("👷 الفنيين", "technician"),
            ("📊 التقارير", "reports"),
            ("📦 المستودع", "inventory"),
            ("👥 المستخدمون", "users"),
            ("🔒 تغيير كلمة المرور", "change_password"),
        ]
    else:
        cards = [("👷 صفحة الفني", "technician"), ("🔒 تغيير كلمة المرور", "change_password")]

    for row_start in range(0, len(cards), 3):
        cols = st.columns(3)
        for col, (label, page_key) in zip(cols, cards[row_start:row_start + 3]):
            with col:
                nav_card(label, page_key)

    st.divider()
    if st.button("🚪 تسجيل الخروج", width="stretch"):
        logout()


def dashboard_page():
    require_login(["admin"])
    top_nav()
    page_header("📊 لوحة التحكم", "نظرة تنفيذية على المهام وأداء الفنيين.")
    with st.spinner("جاري تحديث البيانات..."):
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

    with st.spinner("جاري البحث عن المهمة..."):
        filtered = as_df(search_tasks(keyword, technician, task_type, task_status))

    st.subheader("📈 أداء الفنيين")
    st.bar_chart(df.groupby("technician").size().reset_index(name="عدد المهام").set_index("technician"))
    st.subheader("📋 المهام")
    task_dataframe(filtered)


def technician_page():
    require_login(["admin", "technician"])
    top_nav()
    page_header("👷 صفحة الفني", "تسجيل المهام اليومية بسرعة وبدون تكرار رقم المهمة.")
    with st.form("task_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            task_number = st.text_input("رقم المهمة")
            task_type = st.selectbox("نوع المهمة", TASK_TYPES)
        with col2:
            subscription_number = st.text_input("رقم الاشتراك")
            task_status = st.selectbox("حالة المهمة", TASK_STATUSES)
        submitted = st.form_submit_button("💾 تسجيل المهمة", width="stretch")

    if submitted:
        task_number = task_number.strip()
        subscription_number = subscription_number.strip()
        if not task_number or not subscription_number:
            st.warning("يرجى إدخال رقم المهمة ورقم الاشتراك.")
            return
        with st.spinner("جاري تسجيل المهمة..."):
            exists = task_exists(task_number)
            if not exists:
                add_task(st.session_state.fullname, task_number, subscription_number, task_type, task_status)
        if exists:
            st.error("❌ لا يمكن إضافة نفس رقم المهمة مرتين.")
        else:
            st.success("✅ تم تسجيل المهمة بنجاح")


def select_task_from_search(state_prefix, title):
    keyword = st.text_input(title, key=f"{state_prefix}_keyword")
    if st.button("🔍 البحث", key=f"{state_prefix}_search_btn", width="stretch"):
        if not keyword.strip():
            st.warning("يرجى إدخال قيمة للبحث.")
        else:
            with st.spinner("جاري البحث عن المهمة..."):
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


def admin_page():
    require_login(["admin"])
    top_nav()
    page_header("📋 لوحة المدير", "إدارة المهام، البحث، الاستيراد، التعديل، والحذف.")
    with st.spinner("جاري تحديث البيانات..."):
        df = as_df(search_tasks(), ["id", "technician", "task_number", "subscription_number", "task_type", "task_status"])

    tab_manage, tab_data, tab_transfer = st.tabs(["📋 إدارة المهام", "✏️ إدارة البيانات", "📥 الاستيراد والتصدير"])
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
        with st.spinner("جاري البحث عن المهمة..."):
            filtered = as_df(search_tasks(keyword, task_type=task_type, task_status=status))
        task_dataframe(filtered)
        st.caption(f"عدد النتائج: {len(filtered)}")

    with tab_data:
        edit_col, delete_col = st.columns(2)
        with edit_col:
            st.subheader("✏️ تعديل مهمة")
            task = select_task_from_search("edit_task", "بحث ذكي للتعديل")
            if task:
                with st.form("edit_form"):
                    new_number = st.text_input("رقم المهمة", value=task["task_number"])
                    new_subscription = st.text_input("رقم الاشتراك", value=task["subscription_number"])
                    new_type = st.selectbox("نوع المهمة", TASK_TYPES, index=TASK_TYPES.index(task["task_type"]) if task["task_type"] in TASK_TYPES else 0)
                    new_status = st.selectbox("حالة المهمة", TASK_STATUSES, index=TASK_STATUSES.index(task["task_status"]) if task["task_status"] in TASK_STATUSES else 0)
                    save = st.form_submit_button("💾 حفظ التعديلات", width="stretch")
                if save:
                    with st.spinner("جاري حفظ التعديلات..."):
                        duplicate = task_exists(new_number, exclude_id=task["id"])
                        if not duplicate:
                            update_task(task["id"], new_number, new_subscription, new_type, new_status)
                    if duplicate:
                        st.error("رقم المهمة مستخدم في مهمة أخرى.")
                    else:
                        st.success("✅ تم حفظ التعديلات بنجاح.")
                        st.session_state.pop("edit_task_results", None)
                        st.rerun()

        with delete_col:
            st.subheader("🗑 حذف مهمة")
            task = select_task_from_search("delete_task", "بحث ذكي للحذف")
            if task:
                task_dataframe(as_df([task]))
                st.warning("هل أنت متأكد من حذف المهمة؟")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("نعم، حذف", width="stretch"):
                        with st.spinner("جاري حذف المهمة..."):
                            delete_task(task["id"])
                        st.success("✅ تم حذف المهمة بنجاح.")
                        st.session_state.pop("delete_task_results", None)
                        st.rerun()
                with col2:
                    if st.button("إلغاء", width="stretch"):
                        st.session_state.pop("delete_task_results", None)
                        st.rerun()

    with tab_transfer:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📥 استيراد Excel")
            uploaded = st.file_uploader("اختر ملف Excel", type=["xlsx"])
            if uploaded:
                incoming = pd.read_excel(uploaded)
                columns = [column for column in ["الفني", "رقم المهمة", "رقم الاشتراك", "نوع المهمة", "حالة المهمة"] if column in incoming.columns]
                st.dataframe(incoming[columns].head(20), hide_index=True, width="stretch")
                if st.button("بدء الاستيراد", width="stretch"):
                    added = duplicated = 0
                    with st.spinner("جاري استيراد البيانات..."):
                        for _, row in incoming.iterrows():
                            number = str(row.get("رقم المهمة", "")).strip()
                            if not number or task_exists(number):
                                duplicated += 1
                                continue
                            add_task(
                                str(row.get("الفني", "")).strip() or "غير محدد",
                                number,
                                str(row.get("رقم الاشتراك", "")).strip(),
                                str(row.get("نوع المهمة", "تقني")).strip(),
                                str(row.get("حالة المهمة", "عائق")).strip(),
                            )
                            added += 1
                    st.success(f"✅ تمت إضافة {added} مهمة، وتجاهل {duplicated} مهمة مكررة.")
                    st.rerun()
        with col2:
            st.subheader("📤 تصدير Excel")
            with st.spinner("جاري تصدير البيانات..."):
                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df.drop(columns=["id"], errors="ignore").to_excel(writer, index=False)
            st.download_button(
                "تحميل ملف Excel",
                data=output.getvalue(),
                file_name="tasks.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )


def reports_page():
    require_login(["admin"])
    top_nav()
    page_header("📑 التقارير", "تقارير المهام حسب النوع والحالة مع إمكانية التصدير.")
    with st.spinner("جاري إنشاء التقرير..."):
        df = as_df(search_tasks())
    if df.empty:
        st.info("لا توجد بيانات.")
        return

    col1, col2 = st.columns(2)
    with col1:
        task_type = st.selectbox("نوع المهمة", ["الكل"] + TASK_TYPES)
    with col2:
        task_status = st.selectbox("حالة المهمة", ["الكل"] + TASK_STATUSES)
    keyword = st.text_input("بحث ذكي برقم المهمة أو الاشتراك أو نوع المهمة أو حالتها")
    with st.spinner("جاري إنشاء التقرير..."):
        filtered = as_df(search_tasks(keyword, task_type=task_type, task_status=task_status))

    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي النتائج", len(filtered))
    c2.metric("مهام تقني", int((filtered["task_type"] == "تقني").sum()) if not filtered.empty else 0)
    c3.metric("مهام زيرا", int((filtered["task_type"] == "زيرا").sum()) if not filtered.empty else 0)
    task_dataframe(filtered)
    with st.spinner("جاري تحميل التقارير..."):
        csv = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 تحميل التقرير", csv, "tasks_report.csv", "text/csv", width="stretch")


def users_page():
    require_login(["admin"])
    top_nav()
    page_header("👥 إدارة المستخدمين", "إدارة المستخدمين والصلاحيات من مكان واحد.")

    with st.spinner("جاري تحديث البيانات..."):
        users_df = as_df(get_all_users(), ["id", "username", "fullname", "role", "city", "created_at"])
    tab_view, tab_add, tab_edit, tab_delete = st.tabs(["👥 عرض المستخدمين", "➕ إضافة مستخدم", "✏️ تعديل مستخدم", "🗑️ حذف مستخدم"])

    with tab_view:
        search = st.text_input("بحث بالاسم أو اسم المستخدم")
        filtered = users_df.copy()
        if search.strip() and not filtered.empty:
            filtered = filtered[
                filtered["fullname"].astype(str).str.contains(search, case=False, na=False)
                | filtered["username"].astype(str).str.contains(search, case=False, na=False)
            ]
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
            add_submitted = st.form_submit_button("➕ إضافة المستخدم", width="stretch")
        if add_submitted:
            if not fullname.strip() or not username.strip() or not password.strip() or not confirm_password.strip():
                st.warning("يرجى تعبئة جميع الحقول.")
            elif password.strip() != confirm_password.strip():
                st.error("كلمة المرور وتأكيدها غير متطابقين.")
            elif username_exists(users_df, username):
                st.error("اسم المستخدم مستخدم بالفعل")
            else:
                try:
                    with st.spinner("جاري إضافة المستخدم..."):
                        add_user(username, password, fullname, ROLE_VALUES[role_label], "")
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
                save_submitted = st.form_submit_button("💾 حفظ التعديلات", width="stretch")
            if save_submitted:
                if not fullname.strip():
                    st.warning("يرجى إدخال الاسم الكامل.")
                else:
                    with st.spinner("جاري حفظ التعديلات..."):
                        update_user(selected_user["id"], fullname, password, ROLE_VALUES[role_label])
                    st.success("✅ تم حفظ التعديلات بنجاح")
                    st.rerun()

    with tab_delete:
        options = user_options(users_df)
        if not options:
            st.info("لا يوجد مستخدمون للحذف.")
        else:
            selected_label = st.selectbox("اختر المستخدم", list(options.keys()), key="delete_user_select")
            selected_user = options[selected_label]
            admins_count = int((users_df["role"] == "admin").sum()) if not users_df.empty else 0
            st.info(f"الاسم الكامل: {selected_user['fullname']}\n\nاسم المستخدم: {selected_user['username']}\n\nنوع المستخدم: {ROLE_LABELS.get(selected_user['role'], selected_user['role'])}")
            st.warning("تأكيد واضح: سيتم حذف هذا المستخدم نهائياً من قاعدة البيانات.")
            confirm_delete = st.checkbox("نعم، أؤكد حذف المستخدم", key="confirm_delete_user")
            if st.button("🗑️ حذف المستخدم", width="stretch", disabled=not confirm_delete):
                if selected_user["username"] == st.session_state.username:
                    st.error("لا يمكن حذف المستخدم الذي قام بتسجيل الدخول حالياً.")
                elif selected_user["role"] == "admin" and admins_count <= 1:
                    st.error("لا يمكن حذف آخر مدير في النظام.")
                else:
                    with st.spinner("جاري حذف مستخدم..."):
                        delete_user(selected_user["id"])
                    st.success("✅ تم حذف المستخدم بنجاح")
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
    if "created_at" in display.columns:
        visible_columns.append("created_at")
    st.dataframe(
        display[visible_columns].rename(
            columns={"fullname": "الاسم الكامل", "username": "اسم المستخدم", "created_at": "تاريخ الإنشاء"}
        ),
        hide_index=True,
        width="stretch",
    )


def user_options(df):
    if df.empty:
        return {}
    return {f"{row['fullname']} ({row['username']})": row for _, row in df.sort_values("fullname").iterrows()}


def inventory_page():
    require_login(["admin"])
    top_nav()
    page_header("📦 المستودع", "إدارة المواد والكميات والتنبيهات المخزنية.")
    with st.spinner("جاري تحديث البيانات..."):
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
            submitted = st.form_submit_button("➕ إضافة المادة", width="stretch")
        if submitted:
            if not name.strip():
                st.warning("يرجى إدخال اسم المادة.")
            else:
                with st.spinner("جاري إضافة مادة للمستودع..."):
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
            filtered = filtered[
                filtered["name"].astype(str).str.contains(search, case=False, na=False)
                | filtered["unit"].astype(str).str.contains(search, case=False, na=False)
                | filtered["notes"].astype(str).str.contains(search, case=False, na=False)
            ]
        display = filtered.rename(columns={"name": "اسم المادة", "quantity": "الكمية", "unit": "الوحدة", "notes": "الملاحظات", "created_at": "تاريخ الإضافة", "updated_at": "آخر تحديث"}).drop(columns=["id"], errors="ignore")
        st.dataframe(display, hide_index=True, width="stretch")
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
            if st.button("💾 حفظ التعديلات", width="stretch"):
                with st.spinner("جاري تعديل مادة..."):
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
            if st.button("➕ إضافة للمخزون", width="stretch"):
                with st.spinner("جاري إضافة مادة للمستودع..."):
                    increase_material(material["id"], increase_qty)
                st.success("✅ تمت إضافة الكمية بنجاح.")
                st.rerun()

            decrease_qty = st.number_input("خصم كمية", min_value=1, step=1, key="decrease_qty")
            if st.button("➖ خصم من المخزون", width="stretch"):
                with st.spinner("جاري تحديث البيانات..."):
                    success = decrease_material(material["id"], decrease_qty)
                if success:
                    st.success("✅ تم خصم الكمية بنجاح.")
                    st.rerun()
                else:
                    st.error("الكمية المطلوبة أكبر من الكمية الموجودة.")

        st.divider()
        st.subheader("🗑 حذف المادة")
        st.warning("هل أنت متأكد من حذف المادة؟")
        confirm = st.checkbox("نعم، أؤكد حذف المادة نهائياً")
        if st.button("🗑 حذف المادة", disabled=not confirm, width="stretch"):
            with st.spinner("جاري حذف مادة..."):
                delete_material(material["id"])
            st.success("✅ تم حذف المادة بنجاح.")
            st.rerun()


def change_password_page():
    require_login(["admin", "technician"])
    top_nav()
    page_header("🔒 تغيير كلمة المرور", f"المستخدم الحالي: {st.session_state.fullname}")
    with st.form("change_password_form"):
        current_password = st.text_input("كلمة المرور الحالية", type="password")
        new_password = st.text_input("كلمة المرور الجديدة", type="password")
        confirm_password = st.text_input("تأكيد كلمة المرور الجديدة", type="password")
        submitted = st.form_submit_button("💾 حفظ", width="stretch")

    if submitted:
        if not current_password.strip() or not new_password.strip() or not confirm_password.strip():
            st.warning("يرجى تعبئة جميع الحقول.")
        elif new_password.strip() != confirm_password.strip():
            st.error("كلمتا المرور غير متطابقتين.")
        elif len(new_password.strip()) < 4:
            st.error("يجب أن تكون كلمة المرور 4 أحرف على الأقل.")
        else:
            with st.spinner("جاري حفظ التعديلات..."):
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
        "reports": reports_page,
        "inventory": inventory_page,
        "users": users_page,
        "change_password": change_password_page,
    }
    page = st.session_state.get("current_page", "home")
    pages.get(page, home_screen)()


route()
