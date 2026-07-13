import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import create_tables

create_tables()

print("✅ Database initialized successfully.")