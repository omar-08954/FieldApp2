import streamlit as st
import pandas as pd
import time

from database.database import (
    get_all_materials,
    add_material,
    material_exists,
    update_material,
    increase_material,
    decrease_material,
    delete_material
)

# ======================================
# التحقق من تسجيل الدخول
# ======================================

if not st.session_state.get("logged_in", False):
    st.warning("يرجى تسجيل الدخول أولاً")
    st.stop()

# ======================================
# صلاحيات المدير فقط
# ======================================

if st.session_state.get("role") != "admin":
    st.error("ليس لديك صلاحية للوصول لهذه الصفحة.")
    st.stop()

# ======================================
# عنوان الصفحة
# ======================================

st.title("📦 المستودع")

st.caption(
    "إدارة مواد شركة الفكر الصاعد للمقاولات"
)

# ======================================
# جلب المواد
# ======================================

materials = get_all_materials()

if materials:
    df = pd.DataFrame(materials)
else:
    df = pd.DataFrame(
        columns=[
            "id",
            "name",
            "quantity",
            "unit",
            "notes"
        ]
    )

# ======================================
# الإحصائيات
# ======================================

total_materials = len(df)

if len(df):

    total_quantity = int(
        df["quantity"].sum()
    )

    low_stock = len(
        df[df["quantity"] <= 10]
    )

else:

    total_quantity = 0
    low_stock = 0

card1, card2, card3 = st.columns(3)

card1.metric(
    "📦 عدد المواد",
    total_materials
)

card2.metric(
    "📊 إجمالي الكمية",
    total_quantity
)

card3.metric(
    "⚠️ أوشكت على النفاد",
    low_stock
)

st.divider()

# ======================================
# التبويبات
# ======================================

tab_add, tab_list, tab_manage = st.tabs(
    [
        "➕ إضافة مادة",
        "📋 المواد",
        "⚙️ إدارة مادة"
    ]
)

# ======================================
# تبويب إضافة مادة
# ======================================

with tab_add:

    st.subheader("➕ إضافة مادة جديدة")

    with st.form(
        "add_material_form",
        clear_on_submit=True
    ):

        material_name = st.text_input(
            "اسم المادة"
        )

        quantity = st.number_input(
            "الكمية",
            min_value=1,
            step=1
        )

        unit = st.selectbox(
            "الوحدة",
            [
                "حبة",
                "متر",
                "بكرة",
                "كرتون",
                "رول",
                "كيس",
                "أخرى"
            ]
        )

        notes = st.text_area(
            "الملاحظات (اختياري)",
            height=80
        )

        add_btn = st.form_submit_button(
            "➕ إضافة المادة",
            width="stretch"
        )

    if add_btn:

        material_name = material_name.strip()

        if material_name == "":

            st.warning(
                "⚠️ يرجى إدخال اسم المادة."
            )

        elif material_exists(material_name):

            st.error(
                "❌ هذه المادة موجودة بالفعل."
            )

        else:

            with st.spinner(
                "⏳ جاري إضافة المادة..."
            ):

                add_material(
                    material_name,
                    quantity,
                    unit,
                    notes
                )

                time.sleep(1)

            success = st.success(
                "✅ تم إضافة المادة بنجاح."
            )

            time.sleep(3)

            success.empty()

            st.rerun()

    
# ======================================
# تبويب المواد
# ======================================

with tab_list:

    st.subheader("📋 المواد الموجودة")

    search = st.text_input(
        "🔍 ابحث باسم المادة أو الوحدة أو الملاحظات"
    )

    search_btn = st.button(
        "🔍 بحث",
        width="stretch"
    )

    filtered_df = df.copy()

    if search_btn:

        keyword = search.strip().lower()

        if keyword:

            filtered_df = filtered_df[
                filtered_df.apply(
                    lambda row:
                    keyword in str(row["name"]).lower()
                    or keyword in str(row["unit"]).lower()
                    or keyword in str(row["notes"]).lower(),
                    axis=1
                )
            ]

        msg = st.success(
            "✅ تم البحث بنجاح."
        )

        time.sleep(3)

        msg.empty()

    if len(filtered_df):

        display_df = filtered_df.copy()

        display_df = display_df.rename(
            columns={
                "name": "اسم المادة",
                "quantity": "الكمية",
                "unit": "الوحدة",
                "notes": "الملاحظات"
            }
        )

        if "id" in display_df.columns:

            display_df = display_df.drop(
                columns=["id"]
            )

    # ======================================
    # تلوين الكمية
    # ======================================
    
    def color_quantity(value):
    
        try:
            value = int(value)
    
        except:
            return ""
    
        if value <= 10:
    
            return (
                "background-color:#ffd6d6;"
                "color:black;"
                "font-weight:bold;"
            )
    
        elif value <= 20:
    
            return (
                "background-color:#fff4c2;"
                "color:black;"
                "font-weight:bold;"
            )
    
        else:
    
            return (
                "background-color:#d9ffd9;"
                "color:black;"
                "font-weight:bold;"
            )
    
    
    styled_df = display_df.style.map(
        color_quantity,
        subset=["الكمية"]
    )
    
    st.dataframe(
        styled_df,
        hide_index=True,
        width="stretch"
    )

st.dataframe(

    styled_df,

    hide_index=True,

    width="stretch"

)

st.dataframe(

    styled_df,

    hide_index=True,

    width="stretch"

)

st.dataframe(

    styled_df,

    hide_index=True,

    width="stretch"

)
        st.dataframe(
            styled_df,
            width="stretch",
            hide_index=True
        )

        st.caption(
            f"📦 عدد النتائج : {len(filtered_df)}"
        )

    else:

        st.warning(
            "لا توجد مواد مطابقة للبحث."
        )

    st.divider()

    st.info(
        """
🟢 أخضر = مخزون جيد

🟡 أصفر = مخزون متوسط

🔴 أحمر = مخزون منخفض ويحتاج إعادة طلب
"""
    )

# ======================================
# تبويب إدارة مادة
# ======================================

with tab_manage:

    st.subheader("⚙️ إدارة مادة")

    if df.empty:

        st.info("لا توجد مواد داخل المستودع.")

    else:

        material_names = sorted(
            df["name"].astype(str).tolist()
        )

        selected_name = st.selectbox(
            "اختر المادة",
            material_names
        )

        material = df[
            df["name"] == selected_name
        ].iloc[0]

        st.success(
            f"📦 الكمية الحالية : {material['quantity']} {material['unit']}"
        )

        if material["quantity"] <= 10:

            st.warning(
                "⚠️ هذه المادة قاربت على النفاد."
            )

        st.divider()

        col1, col2 = st.columns(2)

        # ======================================
        # تعديل المادة
        # ======================================

        with col1:

            st.subheader("✏️ تعديل المادة")

            with st.form(
                "edit_material_form"
            ):

                edit_name = st.text_input(
                    "اسم المادة",
                    value=material["name"]
                )

                units = [
                    "حبة",
                    "متر",
                    "بكرة",
                    "كرتون",
                    "رول",
                    "كيس",
                    "أخرى"
                ]

                current_unit = (
                    material["unit"]
                    if material["unit"] in units
                    else "أخرى"
                )

                edit_unit = st.selectbox(
                    "الوحدة",
                    units,
                    index=units.index(current_unit)
                )

                edit_notes = st.text_area(
                    "الملاحظات",
                    value=material["notes"] or "",
                    height=80
                )

                save_btn = st.form_submit_button(
                    "💾 حفظ التعديلات",
                    width="stretch"
                )

            if save_btn:

                new_name = edit_name.strip()

                if new_name == "":

                    st.warning(
                        "⚠️ أدخل اسم المادة."
                    )

                elif (
                    new_name.lower()
                    != material["name"].lower()
                    and
                    material_exists(new_name)
                ):

                    st.error(
                        "❌ اسم المادة موجود بالفعل."
                    )

                else:

                    with st.spinner(
                        "⏳ جاري حفظ التعديلات..."
                    ):

                        update_material(
                            material["id"],
                            new_name,
                            edit_unit,
                            edit_notes
                        )

                        time.sleep(1)

                    msg = st.success(
                        "✅ تم تعديل المادة بنجاح."
                    )

                    time.sleep(3)

                    msg.empty()

                    st.rerun()

        # ======================================
        # إدارة الكمية
        # ======================================

        with col2:

            st.subheader("📦 إدارة الكمية")

            with st.form("increase_form"):

                increase_qty = st.number_input(
                    "إضافة كمية",
                    min_value=1,
                    step=1
                )

                increase_btn = st.form_submit_button(
                    "➕ إضافة للمخزون",
                    width="stretch"
                )

            if increase_btn:

                with st.spinner(
                    "⏳ جاري إضافة الكمية..."
                ):

                    increase_material(
                        material["id"],
                        increase_qty
                    )

                    time.sleep(1)

                msg = st.success(
                    "✅ تمت إضافة الكمية بنجاح."
                )

                time.sleep(3)

                msg.empty()

                st.rerun()

            st.divider()

            with st.form("decrease_form"):

                decrease_qty = st.number_input(
                    "خصم كمية",
                    min_value=1,
                    step=1
                )

                decrease_btn = st.form_submit_button(
                    "➖ خصم من المخزون",
                    width="stretch"
                )

            if decrease_btn:

                with st.spinner(
                    "⏳ جاري خصم الكمية..."
                ):

                    success = decrease_material(
                        material["id"],
                        decrease_qty
                    )

                    time.sleep(1)

                if success:

                    remaining = int(material["quantity"]) - int(decrease_qty)

                    if remaining <= 0:

                        st.warning(
                            "⚠️ نفدت هذه المادة من المستودع."
                        )

                    msg = st.success(
                        "✅ تم خصم الكمية بنجاح."
                    )

                    time.sleep(3)

                    msg.empty()

                    st.rerun()

                else:

                    st.error(
                        "❌ الكمية المطلوبة أكبر من الكمية الموجودة."
                    )

        st.divider()

        # ======================================
        # حذف المادة
        # ======================================

        st.subheader("🗑 حذف المادة")

        confirm_delete = st.checkbox(
            "أؤكد حذف المادة نهائياً"
        )

        if st.button(
            "🗑 حذف المادة",
            width="stretch",
            disabled=not confirm_delete
        ):

            with st.spinner(
                "⏳ جاري حذف المادة..."
            ):

                delete_material(
                    material["id"]
                )

                time.sleep(1)

            msg = st.success(
                "✅ تم حذف المادة بنجاح."
            )

            time.sleep(3)

            msg.empty()

            st.rerun()

# ======================================
# تسجيل الخروج
# ======================================

st.divider()

if st.button(
    "🚪 تسجيل الخروج والعودة للرئيسية",
    width="stretch"
):

    st.session_state.logged_in = False
    st.session_state.fullname = ""
    st.session_state.username = ""
    st.session_state.role = ""

    st.switch_page("app.py")
    
