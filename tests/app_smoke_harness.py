"""Streamlit smoke harness: isolates UI rendering from production services."""

import sys
import types
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


fake_db = types.ModuleType("database.database")
fake_db.CITIES = ["جدة", "مكة"]


def _rows(*_args, **_kwargs):
    return []


def _none(*_args, **_kwargs):
    return None


def _false(*_args, **_kwargs):
    return False


def _true(*_args, **_kwargs):
    return True


for name in (
    "add_material add_task add_user assign_task bulk_add_tasks change_password cleanup_cache "
    "complete_assigned_task create_tables decrease_material delete_daily_report delete_material "
    "delete_tasks delete_user increase_material log_action log_error save_daily_report update_material "
    "update_task update_user"
).split():
    setattr(fake_db, name, _none)

for name in (
    "assigned_task_number_exists check_current_password daily_report_exists is_password_strong "
    "material_exists task_exists"
).split():
    setattr(fake_db, name, _false)

for name in (
    "get_all_materials get_audit_log get_error_log search_assigned_tasks search_completed_tasks search_tasks"
).split():
    setattr(fake_db, name, _rows)

fake_db.get_all_users = lambda *_args, **_kwargs: [
    {"id": 1, "username": "admin", "fullname": "مدير الاختبار", "role": "admin", "city": "جدة"},
    {"id": 2, "username": "tech", "fullname": "فني الاختبار", "role": "technician", "city": "جدة"},
]
fake_db.get_assigned_task_by_number = _none
fake_db.get_daily_report = _none
fake_db.daily_report_display_source = _none
fake_db.daily_report_download_bytes = _none
fake_db.login_user = _none
fake_db.resolve_column_mapping = lambda *_args, **_kwargs: {}
fake_db.resolve_known_technician = lambda value, *_args, **_kwargs: value
fake_db.get_query_stats = lambda: {"avg_ms": 0, "slowest": []}
fake_db.get_system_counts = lambda: {"tasks": 0, "assigned_tasks": 0, "reports": 0}
fake_db.get_tasks_breakdown = lambda: []
fake_db.get_security_overview = lambda: {"online_now": [], "failed_attempts": [], "locked": []}
fake_db.get_database_info = lambda: {}
fake_db.test_db_connection = lambda: {"connected": True, "response_ms": 1, "error": None}

sys.modules["database.database"] = fake_db
sys.modules.pop("app", None)

st.session_state.setdefault("logged_in", True)
st.session_state.setdefault("username", "smoke")
st.session_state.setdefault("fullname", "مستخدم الاختبار")
st.session_state.setdefault("role", "admin")
st.session_state.setdefault("city", "جدة")
st.session_state.setdefault("current_page", "admin")

import app  # noqa: E402,F401  # route() renders the selected page
