import time

import pandas as pd
import streamlit as st

from database.database import (
    add_material,
    decrease_material,
    delete_material,
    get_all_materials,
    increase_material,
    material_exists,
    update_material,
)
from ui import init_page, page_header, require_login, top_nav


UNITS = ["حبة", "متر", "بكرة", "كرتون", "رول", "كيس", "علبة", "أخرى"]


init_page("المستودع")
require_login(["admin"])
top_nav()
page_header("📦 المستودع", "إدارة المواد والكميات والتنبيهات المخزنية.")

materials = get_all_materials()
df = pd.DataFrame(materials)
if df.empty:
    df = pd.DataFrame(columns=["id", "name", "quantity", "unit", "notes"])

total_materials = len(df)
total_quantity = int(df["quantity"].sum()) if total_materials else 0
low_stock = int((df["quantity"] <= 10).sum()) if total_materials else 0
c1, c2, c3 = st.columns(3)
c1.metric("عدد المواد", total_materials)
c2.metric("إجمالي الكمية", total_quantity)
c3.metric("منخفضة المخزون", low_stock)

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
        submitted = st.form_submit_button("➕ إضافة المادة", use_container_width=True)
    if submitted:
        name = name.strip()
        if not name:
            st.warning("يرجى إدخال اسم المادة.")
        elif material_exists(name):
            st.error("هذه المادة موجودة بالفعل.")
        else:
            with st.spinner("جاري إضافة المادة..."):
                add_material(name, quantity, unit, notes)
                time.sleep(0.4)
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
    display = filtered.rename(
        columns={
            "name": "اسم المادة",
            "quantity": "الكمية",
            "unit": "الوحدة",
            "notes": "الملاحظات",
            "created_at": "تاريخ الإضافة",
            "updated_at": "آخر تحديث",
        }
    ).drop(columns=["id"], errors="ignore")
    st.dataframe(display, hide_index=True, use_container_width=True)
    st.caption(f"عدد النتائج: {len(filtered)}")

with tab_manage:
    if df.empty:
        st.info("لا توجد مواد داخل المستودع.")
    else:
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
                if material_exists(edit_name, exclude_id=material["id"]):
                    st.error("اسم المادة مستخدم بالفعل.")
                else:
                    update_material(material["id"], edit_name, edit_unit, edit_notes)
                    st.success("✅ تم تعديل المادة بنجاح.")
                    st.rerun()

        with col2:
            st.subheader("📦 إدارة الكمية")
            increase_qty = st.number_input("إضافة كمية", min_value=1, step=1, key="increase_qty")
            if st.button("➕ إضافة للمخزون", use_container_width=True):
                increase_material(material["id"], increase_qty)
                st.success("✅ تمت إضافة الكمية بنجاح.")
                st.rerun()

            decrease_qty = st.number_input("خصم كمية", min_value=1, step=1, key="decrease_qty")
            if st.button("➖ خصم من المخزون", use_container_width=True):
                if decrease_material(material["id"], decrease_qty):
                    st.success("✅ تم خصم الكمية بنجاح.")
                    st.rerun()
                else:
                    st.error("الكمية المطلوبة أكبر من الكمية الموجودة.")

        st.divider()
        st.subheader("🗑 حذف المادة")
        st.warning("هل أنت متأكد من حذف المادة؟")
        confirm = st.checkbox("نعم، أؤكد حذف المادة نهائياً")
        if st.button("🗑 حذف المادة", disabled=not confirm, use_container_width=True):
            delete_material(material["id"])
            st.success("✅ تم حذف المادة بنجاح.")
            st.rerun()
