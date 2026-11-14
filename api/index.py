import sys
import os
from pathlib import Path

# Set up python path to include the backend directory
BASE_DIR = Path(__file__).resolve().parent.parent
backend_dir = BASE_DIR / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Ensure SQLite is initialized in /tmp on Vercel serverless cold start
if os.getenv("VERCEL") or os.getenv("VERCEL_ENV"):
    try:
        from app.database.init_db import init_database
        init_database()
    except Exception as e:
        print(f"Vercel DB initialization note: {e}")

from app.main import app
