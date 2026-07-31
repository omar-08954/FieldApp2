import sys
from pathlib import Path

# إضافة مجلد المشروع إلى Python Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database.database import create_tables

def main() -> None:
    print("⏳ Initializing legacy database schema...", flush=True)
    try:
        create_tables()
    except Exception as exc:
        print(f"❌ Database initialization failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise
    print("✅ Database initialized successfully.", flush=True)


if __name__ == "__main__":
    main()
