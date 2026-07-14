import sys
from pathlib import Path

# إضافة مجلد المشروع إلى Python Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database.database import create_tables

create_tables()

print("✅ Database initialized successfully.")