"""Render one Streamlit route in an isolated process for smoke testing."""

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


if len(sys.argv) != 3:
    raise SystemExit("usage: run_page_smoke.py PAGE ROLE")

page, role = sys.argv[1:]
harness = Path(__file__).with_name("app_smoke_harness.py")
app = AppTest.from_file(str(harness), default_timeout=20)
app.session_state["logged_in"] = True
app.session_state["username"] = "smoke"
app.session_state["fullname"] = "مستخدم الاختبار"
app.session_state["role"] = role
app.session_state["city"] = "جدة"
app.session_state["current_page"] = page
app.run()

if list(app.exception):
    raise AssertionError(f"Runtime error while rendering {page}: {list(app.exception)}")

if page == "admin":
    labels = [tab.label for tab in app.tabs]
    for expected in ("📌 إسناد مهمة", "📅 المهام اليومية", "📋 المهام المسندة"):
        if expected not in labels:
            raise AssertionError(f"Manager tab is missing: {expected}; tabs={labels}")

if page == "technician" and not any("صفحة الفني" in title.value for title in app.title):
    raise AssertionError("Technician page title was not rendered")

print(f"SMOKE_OK page={page} role={role}")
