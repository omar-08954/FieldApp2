"""خدمة الإشعارات — إرسال، عرض Toast، وإدارة التفضيلات."""

from __future__ import annotations

import streamlit as st

from database.database import (
    create_notification,
    delete_all_notifications,
    delete_notification,
    get_unread_notification_count,
    get_user_notifications,
    get_user_notification_setting,
    mark_all_notifications_read,
    mark_notification_read,
    set_user_notification_setting,
)
from logging_config import get_logger

LOGGER = get_logger(__name__)

EVENT_LABELS = {
    "task_add": "إضافة مهمة",
    "task_update": "تعديل مهمة",
    "task_delete": "حذف مهمة",
    "task_assign": "إسناد مهمة",
    "task_status": "تغيير حالة",
    "import_start": "بدء استيراد",
    "import_success": "نجاح استيراد",
    "import_fail": "فشل استيراد",
    "import_review": "مهام تحتاج مراجعة",
    "user_add": "مستخدم جديد",
    "technician_add": "فني جديد",
    "password_reset": "إعادة كلمة مرور",
    "system": "عملية نظام",
}


def notifications_enabled(username: str | None = None) -> bool:
    user = username or st.session_state.get("username") or ""
    if not user:
        return False
    return get_user_notification_setting(user)


def set_notifications_enabled(enabled: bool, username: str | None = None) -> None:
    user = username or st.session_state.get("username") or ""
    if user:
        set_user_notification_setting(user, enabled)


def show_toast(message: str, icon: str = "ℹ️") -> None:
    if notifications_enabled():
        try:
            st.toast(message, icon=icon)
        except Exception as exc:
            LOGGER.warning("Toast failed: %s", exc)


def notify_user(
    username: str,
    event_type: str,
    title: str,
    message: str,
    *,
    show_toast_now: bool = False,
    toast_icon: str = "ℹ️",
) -> None:
    if not username:
        return
    if not get_user_notification_setting(username):
        return
    try:
        create_notification(username, event_type, title, message)
    except Exception as exc:
        LOGGER.warning("Notification create failed: %s", exc)
        return
    if show_toast_now and username == st.session_state.get("username"):
        show_toast(message, toast_icon)


def notify_admins(event_type: str, title: str, message: str, *, toast_icon: str = "ℹ️") -> None:
    from database.database import get_all_users

    for user in get_all_users():
        if user.get("role") == "admin":
            notify_user(user["username"], event_type, title, message, toast_icon=toast_icon)


def notify_technician_by_name(
    fullname: str,
    event_type: str,
    title: str,
    message: str,
    *,
    toast_icon: str = "ℹ️",
) -> None:
    from database.database import get_all_users

    for user in get_all_users():
        if user.get("role") == "technician" and user.get("fullname") == fullname:
            notify_user(user["username"], event_type, title, message, toast_icon=toast_icon)


def get_badge_count(username: str | None = None) -> int:
    user = username or st.session_state.get("username") or ""
    if not user or not notifications_enabled(user):
        return 0
    try:
        return get_unread_notification_count(user)
    except Exception:
        return 0


def list_notifications(username: str | None = None, *, unread_only: bool = False, keyword: str = ""):
    user = username or st.session_state.get("username") or ""
    return get_user_notifications(user, unread_only=unread_only, keyword=keyword)


def mark_read(notification_id: int) -> None:
    mark_notification_read(notification_id)


def mark_all_read(username: str | None = None) -> None:
    user = username or st.session_state.get("username") or ""
    mark_all_notifications_read(user)


def remove_notification(notification_id: int) -> None:
    delete_notification(notification_id)


def remove_all_notifications(username: str | None = None) -> None:
    user = username or st.session_state.get("username") or ""
    delete_all_notifications(user)
